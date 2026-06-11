"""Web frontend for Beasty Bar.

Run with `python webapp/server.py` and open http://localhost:8000.
Player 0 is the human, the remaining seats are AI (Max strategy).
Uses only the standard library.
"""
import json
import threading
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from logic import GameRunner  # noqa: E402
from safari.cards.base import ANIMALS  # noqa: E402
from safari.players.strategies import Max, Player  # noqa: E402
from safari.stacks.shuffle import init  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent / "static"
HUMAN = 0


def card_json(card):
    return {
        "animal": int(card.value),
        "name": card.__class__.__name__,
        "player": card.player,
    }


class WebGame:
    def __init__(self, n_players=4):
        if not 2 <= n_players <= 4:
            raise ValueError("Beasty Bar is played by 2-4 players")
        strategies = {HUMAN: Player}
        strategies.update({i: Max for i in range(1, n_players)})
        self.runner = GameRunner(init(strategies=strategies))
        self.log = []
        self.last_turn = None

    @property
    def state(self):
        return self.runner.game_state

    def serialize(self):
        gs = self.state
        players = []
        for p in gs.players:
            info = gs.table[p]
            players.append({
                "id": p,
                "is_human": p == HUMAN,
                "hand_count": len(info["hand"]),
                "deck_count": len(info["deck"]),
                "in_bar": sum(1 for c in gs.cards_in_bar if c.player == p),
                "finished": info["finished"],
            })
        data = {
            "queue": [card_json(c) for c in gs.queue],
            "hand": [card_json(c) for c in gs.table[HUMAN]["hand"]],
            "bar": [card_json(c) for c in gs.cards_in_bar],
            "trash": [card_json(c) for c in gs.cards_in_thrash],
            "players": players,
            "current_player": gs.current_player,
            "turn": gs.turn_number,
            "finished": gs.finished,
            "log": self.log[-40:],
            "last_turn": self.last_turn,
        }
        if gs.finished:
            gs.update_results()
            data["results"] = {str(p): n for p, n in gs.results.items()}
            data["winners"] = gs.get_winners()
        return data

    def _apply_turn(self, card):
        gs = self.state
        player = gs.current_player
        bar_before = len(gs.cards_in_bar)
        trash_before = len(gs.cards_in_thrash)

        self.runner.update_game_state(card)

        to_bar = gs.cards_in_bar[bar_before:]
        to_trash = gs.cards_in_thrash[trash_before:]
        entry = {
            "player": player,
            "played": card_json(card),
            "as": getattr(card, "taken_form_of", None),
            "to_bar": [card_json(c) for c in to_bar],
            "to_trash": [card_json(c) for c in to_trash],
            "gate_opened": gs.last_queue_evaluation is not None,
        }
        self.log.append(entry)
        self.last_turn = entry

    def _skip_finished(self):
        """Advance past players that have no cards left."""
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

    def play_human(self, animal_value, params):
        gs = self.state
        self._skip_finished()
        if gs.finished:
            raise GameError("the game is over")
        if gs.current_player != HUMAN:
            raise GameError("it is not your turn")
        hand = gs.get_player_hand(HUMAN)
        card = next((c for c in hand if int(c.value) == animal_value), None)
        if card is None:
            raise GameError("that card is not in your hand")
        self._attach_params(card, params or {})
        self._apply_turn(card)
        self._skip_finished()

    def _attach_params(self, card, params):
        if "imitate" in params and int(card.value) == ANIMALS.CHAMELEON:
            try:
                card.imitate = ANIMALS(int(params["imitate"]))
            except ValueError:
                raise GameError("unknown species to imitate")
            if card.imitate not in [c.value for c in self.state.queue]:
                raise GameError("you can only imitate a species in the queue")
        if "jump" in params:
            card.jump = int(params["jump"])
        if "target_index" in params:
            idx = int(params["target_index"])
            if not 0 <= idx < len(self.state.queue):
                raise GameError("invalid parrot target")
            card.target_index = idx

    def step_ai(self):
        gs = self.state
        self._skip_finished()
        if gs.finished or gs.current_player == HUMAN:
            return
        p = gs.current_player
        card = gs.table[p]["strategy"].strategy(gs.table[p]["hand"])
        self._apply_turn(card)
        self._skip_finished()


class GameError(Exception):
    pass


GAME = WebGame()
LOCK = threading.Lock()

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the console quiet

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
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

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            with LOCK:
                self._send_json(GAME.serialize())
        elif path == "/":
            self._send_file("index.html")
        else:
            self._send_file(path.lstrip("/"))

    def do_POST(self):
        global GAME
        path = self.path.split("?")[0]
        try:
            body = self._read_body()
            with LOCK:
                if path == "/api/new":
                    GAME = WebGame(int(body.get("players", 4)))
                elif path == "/api/play":
                    GAME.play_human(int(body["card"]), body.get("params"))
                elif path == "/api/step":
                    GAME.step_ai()
                else:
                    self.send_error(404)
                    return
                self._send_json(GAME.serialize())
        except (GameError, ValueError, KeyError) as exc:
            self._send_json({"error": str(exc)}, status=400)


def main(port=8000):
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Beasty Bar running on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8000)
