"""Web frontend for Beasty Bar with multiplayer rooms.

Run with `python webapp/server.py [port]` and open http://localhost:8000.
Create a room, share the invite link with friends; empty seats are filled
with AI players. Decks: classic, new_beasts (expansion), mixed.
Uses only the standard library.
"""
import copy
import json
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from logic import GameRunner  # noqa: E402
from safari.cards.base import ANIMALS  # noqa: E402
from safari.cards.first_game_deck import Chameleon  # noqa: E402
from safari.cards.new_beasts_deck import Penguin, Vulture  # noqa: E402
from safari.players.strategies import Max, Player  # noqa: E402
from safari.stacks.shuffle import init  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent / "static"
AI_DELAY = 0.8          # seconds between AI moves
ROOM_TTL = 24 * 3600    # drop rooms idle for a day


class GameError(Exception):
    pass


def card_json(card):
    return {
        "animal": int(card.value),
        "name": card.__class__.__name__,
        "player": card.player,
    }


class Room:
    def __init__(self, total, humans, deck, host_name):
        if not 2 <= total <= 4:
            raise GameError("Beasty Bar is played by 2-4 players")
        if not 1 <= humans <= total:
            raise GameError("number of humans must be between 1 and the player count")
        self.id = secrets.token_urlsafe(4)
        self.deck = deck
        self.seats = []
        strategies = {}
        for i in range(total):
            if i < humans:
                self.seats.append({"name": None, "token": None, "is_ai": False})
                strategies[i] = Player
            else:
                self.seats.append({"name": f"AI {i + 1}", "token": None, "is_ai": True})
                strategies[i] = Max
        self.runner = GameRunner(init(strategies=strategies, deck=deck))
        self.state.scoring = 'count' if deck == 'classic' else 'points'
        self.log = []
        self.version = 0
        self.last_touch = time.time()
        self.last_ai_move = 0.0
        self.claim_seat(host_name)

    # ---- seats ----

    @property
    def state(self):
        return self.runner.game_state

    @property
    def started(self):
        return all(s["token"] or s["is_ai"] for s in self.seats)

    def claim_seat(self, name):
        # an open human seat first; otherwise take over an AI seat, so an
        # invite link always works even if the host left the default of
        # one human player
        free = next((i for i, s in enumerate(self.seats)
                     if not s["is_ai"] and s["token"] is None), None)
        if free is None and not self.state.finished:
            free = next((i for i, s in enumerate(self.seats) if s["is_ai"]), None)
        if free is None:
            raise GameError("this game is already full")
        seat = self.seats[free]
        seat["is_ai"] = False
        seat["token"] = secrets.token_urlsafe(9)
        seat["name"] = (name or "").strip()[:20] or f"Player {free + 1}"
        self.bump()
        return free, seat["token"]

    def seat_of(self, token):
        for i, seat in enumerate(self.seats):
            if token and seat["token"] == token:
                return i
        return None

    def bump(self):
        self.version += 1
        self.last_touch = time.time()

    # ---- game flow ----

    def _apply_turn(self, card):
        gs = self.state
        player = gs.current_player
        bar_before = len(gs.cards_in_bar)
        trash_before = len(gs.cards_in_thrash)

        self.runner.update_game_state(card)

        entry = {
            "player": player,
            "played": card_json(card),
            "as": getattr(card, "taken_form_of", None),
            "to_bar": [card_json(c) for c in gs.cards_in_bar[bar_before:]],
            "to_trash": [card_json(c) for c in gs.cards_in_thrash[trash_before:]],
            "gate_opened": gs.last_queue_evaluation is not None,
        }
        self.log.append(entry)
        self.bump()

    def _skip_finished(self):
        gs = self.state
        for _ in range(gs.n_players):
            if gs.finished:
                return
            p = gs.current_player
            if gs.table[p]["hand"]:
                return
            gs.mark_player_finished(p)
            self.runner.check_game_end()
            gs.increment_turn()
            gs.next_player()
            self.bump()

    def tick(self):
        """Advance one AI turn if it's an AI's move and the delay passed.
        Called lazily whenever a client polls."""
        if not self.started or self.state.finished:
            return
        self._skip_finished()
        gs = self.state
        if gs.finished:
            return
        p = gs.current_player
        if not self.seats[p]["is_ai"]:
            return
        now = time.time()
        if now - self.last_ai_move < AI_DELAY:
            return
        self.last_ai_move = now
        card = gs.table[p]["strategy"].strategy(gs.table[p]["hand"])
        self._set_ai_defaults(card, gs.table[p]["hand"])
        self._apply_turn(card)
        self._skip_finished()

    def _set_ai_defaults(self, card, hand):
        if isinstance(card, Penguin):
            others = [c for c in hand if c is not card]
            if others:
                card.imitate_class = max(others, key=lambda c: int(c.value)).__class__

    def play_human(self, token, animal_value, params):
        seat, gs, card = self._validate_play(token, animal_value)
        self._attach_params(card, params or {}, gs.get_player_hand(seat), gs)
        self._apply_turn(card)
        self._skip_finished()

    def preview(self, token, animal_value, params):
        """Dry-run a play on a copy of the game state, so the client can
        SHOW the outcome (new line, who flies out, who gets in) before the
        player commits."""
        seat, _, _ = self._validate_play(token, animal_value)
        gs = copy.deepcopy(self.state)
        hand = gs.get_player_hand(seat)
        card = next(c for c in hand if int(c.value) == int(animal_value))
        self._attach_params(card, params or {}, hand, gs)
        bar_before = len(gs.cards_in_bar)
        trash_before = len(gs.cards_in_thrash)

        gs.update_queue(card)
        gate_opened = len(gs.queue) == 5
        if gate_opened:
            gs.cards_in_bar.extend(gs.queue[:2])
            gs.cards_in_thrash.append(gs.queue[-1])
            gs.queue = gs.queue[2:4]
            new_queue, burned = gs.queue.burn_bats()
            gs.queue = new_queue
            gs.cards_in_thrash.extend(burned)

        return {
            "queue": [card_json(c) for c in gs.queue],
            "to_bar": [card_json(c) for c in gs.cards_in_bar[bar_before:]],
            "to_trash": [card_json(c) for c in gs.cards_in_thrash[trash_before:]],
            "gate_opened": gate_opened,
        }

    def _validate_play(self, token, animal_value):
        if not self.started:
            raise GameError("the game has not started yet")
        seat = self.seat_of(token)
        if seat is None:
            raise GameError("you are not seated in this game")
        self._skip_finished()
        gs = self.state
        if gs.finished:
            raise GameError("the game is over")
        if gs.current_player != seat:
            raise GameError("it is not your turn")
        card = next((c for c in gs.get_player_hand(seat)
                     if int(c.value) == int(animal_value)), None)
        if card is None:
            raise GameError("that card is not in your hand")
        return seat, gs, card

    def _attach_params(self, card, params, hand, gs):
        queue_len = len(gs.queue)
        if isinstance(card, Chameleon) and "imitate" in params:
            chosen = int(params["imitate"])
            if chosen not in [int(c.value) for c in gs.queue]:
                raise GameError("you can only imitate a species in the queue")
            card.imitate = chosen
        if isinstance(card, Penguin) and "imitate_value" in params:
            chosen = next((c for c in hand
                           if c is not card and int(c.value) == int(params["imitate_value"])), None)
            if chosen is None:
                raise GameError("you can only imitate another animal from your hand")
            card.imitate_class = chosen.__class__
        if isinstance(card, Vulture):
            revive = params.get("revive") or {}
            card.revive_params = self._revive_params(revive, hand, gs)
        if "jump" in params:
            card.jump = int(params["jump"])
        if "parity" in params:
            if params["parity"] not in ("even", "odd"):
                raise GameError("parity must be 'even' or 'odd'")
            card.parity = params["parity"]
        if "target_index" in params:
            idx = int(params["target_index"])
            if not 0 <= idx < queue_len:
                raise GameError("invalid target")
            card.target_index = idx

    def _revive_params(self, revive, hand, gs):
        out = {}
        if "target_index" in revive:
            idx = int(revive["target_index"])
            if not 0 <= idx < len(gs.queue):
                raise GameError("invalid revive target")
            out["target_index"] = idx
        if "jump" in revive:
            out["jump"] = int(revive["jump"])
        if revive.get("parity") in ("even", "odd"):
            out["parity"] = revive["parity"]
        if "imitate_value" in revive:
            chosen = next((c for c in hand if int(c.value) == int(revive["imitate_value"])), None)
            if chosen is not None:
                out["imitate_class"] = chosen.__class__
        if "imitate" in revive:
            out["imitate"] = int(revive["imitate"])
        return out

    # ---- serialization ----

    def serialize(self, token):
        gs = self.state
        seat = self.seat_of(token)
        players = []
        for i, s in enumerate(self.seats):
            info = gs.table[i]
            score = sum((c.point_value if gs.scoring == 'points' else 1)
                        for c in gs.cards_in_bar if c.player == i)
            players.append({
                "id": i,
                "name": s["name"] or "(open seat)",
                "is_ai": s["is_ai"],
                "claimed": s["is_ai"] or s["token"] is not None,
                "hand_count": len(info["hand"]),
                "deck_count": len(info["deck"]),
                "in_bar": sum(1 for c in gs.cards_in_bar if c.player == i),
                "score": score,
                "finished": info["finished"],
            })
        data = {
            "room": self.id,
            "deck": self.deck,
            "scoring": gs.scoring,
            "started": self.started,
            "version": self.version,
            "you": seat,
            "players": players,
            "queue": [card_json(c) for c in gs.queue],
            "bar_count": len(gs.cards_in_bar),
            "trash_count": len(gs.cards_in_thrash),
            "trash_top": card_json(gs.cards_in_thrash[-1]) if gs.cards_in_thrash else None,
            "current_player": gs.current_player,
            "finished": gs.finished,
            "log": self.log[-50:],
            "log_total": len(self.log),
            "hand": [card_json(c) for c in gs.table[seat]["hand"]] if seat is not None else [],
        }
        if gs.finished:
            gs.update_results()
            data["results"] = {str(p): n for p, n in gs.results.items()}
            data["winners"] = gs.get_winners()
        return data


ROOMS = {}
LOCK = threading.Lock()


def get_room(room_id):
    room = ROOMS.get(room_id)
    if room is None:
        raise GameError("this game no longer exists — the host can start a new one")
    return room


def prune_rooms():
    now = time.time()
    for rid in [r for r, room in ROOMS.items() if now - room.last_touch > ROOM_TTL]:
        del ROOMS[rid]


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".webmanifest": "application/manifest+json",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    # ---- plumbing ----

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path):
        try:
            resolved = (STATIC_DIR / path).resolve()
            resolved.relative_to(STATIC_DIR)  # forbid path traversal
            body = resolved.read_bytes()
        except (OSError, ValueError):
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type",
                         CONTENT_TYPES.get(resolved.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length) or b"{}")

    def _query(self):
        if "?" not in self.path:
            return {}
        out = {}
        for pair in self.path.split("?", 1)[1].split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
                out[k] = v
        return out

    # ---- routes ----

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            q = self._query()
            try:
                with LOCK:
                    room = get_room(q.get("room", ""))
                    room.tick()
                    self._send_json(room.serialize(q.get("token")))
            except GameError as exc:
                self._send_json({"error": str(exc)}, status=404)
            except Exception as exc:  # never kill the connection on a bug
                self._send_json({"error": f"server error: {exc}"}, status=500)
        elif path == "/":
            self._send_file("index.html")
        else:
            self._send_file(path.lstrip("/"))

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            body = self._read_body()
            with LOCK:
                if path == "/api/room":
                    prune_rooms()
                    room = Room(
                        total=int(body.get("players", 4)),
                        humans=int(body.get("humans", 1)),
                        deck=body.get("deck", "classic"),
                        host_name=body.get("name", ""),
                    )
                    ROOMS[room.id] = room
                    seat, token = 0, room.seats[0]["token"]
                    self._send_json({"room": room.id, "seat": seat, "token": token})
                elif path == "/api/join":
                    room = get_room(body.get("room", ""))
                    seat, token = room.claim_seat(body.get("name", ""))
                    self._send_json({"room": room.id, "seat": seat, "token": token})
                elif path == "/api/play":
                    room = get_room(body.get("room", ""))
                    room.play_human(body.get("token"), body["card"], body.get("params"))
                    self._send_json(room.serialize(body.get("token")))
                elif path == "/api/preview":
                    room = get_room(body.get("room", ""))
                    self._send_json(room.preview(body.get("token"), body["card"], body.get("params")))
                else:
                    self.send_error(404)
        except (GameError, ValueError, KeyError) as exc:
            self._send_json({"error": str(exc)}, status=400)
        except Exception as exc:  # never kill the connection on a bug
            self._send_json({"error": f"server error: {exc}"}, status=500)


def main(port=8000):
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Beasty Bar running on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    import os
    default_port = int(os.environ.get("PORT", 8000))  # Cloud Run sets $PORT
    main(int(sys.argv[1]) if len(sys.argv) > 1 else default_port)
