import importlib.util
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "webapp_server", Path(__file__).resolve().parents[2] / "webapp" / "server.py")
server = importlib.util.module_from_spec(_spec)
sys.modules["webapp_server"] = server
_spec.loader.exec_module(server)


def make_room(total=4, local=None, ai=0, deck='classic', difficulty='medium'):
    # deterministic seating for tests; fairness is covered separately
    return server.Room(total=total, local_names=local or ["Host"], ai=ai,
                       deck=deck, difficulty=difficulty, fair_start=False)


def test_invite_works_when_only_ai_seats_remain():
    """Regression: a friend opening the invite link of a host+AI game used
    to get 'room already full' — now they take over an AI seat."""
    room = make_room(total=4, local=["Host"], ai=3)
    assert room.started  # solo + AI games start immediately
    token, seats = room.claim_seats(["Friend"])
    assert seats == [1]
    assert room.seats[1]["is_ai"] is False
    assert room.seats[1]["name"] == "Friend"
    assert room.started


def test_hotseat_two_seats_one_token():
    room = make_room(total=4, local=["Anna", "Ben"], ai=2)
    assert room.seats_of(room.host_token) == [0, 1]
    assert room.seats[0]["name"] == "Anna"
    assert room.seats[1]["name"] == "Ben"
    assert room.started
    # the same token may play either of its seats, but only on its turn
    gs = room.state
    assert gs.current_player == 0
    card = gs.table[0]["hand"][0]
    room.play_human(room.host_token, int(card.value), {})
    assert gs.current_player == 1
    card = gs.table[1]["hand"][0]
    room.play_human(room.host_token, int(card.value), {})
    assert gs.current_player == 2


def test_two_devices_two_players_each():
    room = make_room(total=4, local=["A1", "A2"], ai=0)
    assert not room.started  # two open seats remain
    token_b, seats_b = room.claim_seats(["B1", "B2"])
    assert seats_b == [2, 3]
    assert room.started
    view = room.serialize(token_b)
    assert view["you_seats"] == [2, 3]
    assert set(view["hands"].keys()) == {"2", "3"}
    assert all(len(h) == 4 for h in view["hands"].values())
    # device A cannot play device B's seat
    gs = room.state
    while gs.current_player in (0, 1):
        card = gs.table[gs.current_player]["hand"][0]
        room.play_human(room.host_token, int(card.value), {})
    with pytest.raises(server.GameError, match="not your turn"):
        room.play_human(room.host_token, int(gs.table[gs.current_player]["hand"][0].value), {})


def test_room_truly_full():
    room = make_room(total=2, local=["Host"], ai=0)
    room.claim_seats(["Friend"])
    with pytest.raises(server.GameError, match="full"):
        room.claim_seats(["Late"])


def test_partial_claim_when_not_enough_seats():
    room = make_room(total=2, local=["Host"], ai=0)
    token, seats = room.claim_seats(["B1", "B2"])  # only one seat left
    assert seats == [1]


def test_per_seat_ai_difficulty():
    room = server.Room(total=4, local_names=["Host"], ai=["easy", "hard"], deck='classic',
                       fair_start=False)
    assert room.seats[2]["difficulty"] == "easy" and "🐣" in room.seats[2]["name"]
    assert room.seats[3]["difficulty"] == "hard" and "🧠" in room.seats[3]["name"]
    view = room.serialize(room.host_token)
    assert [p["difficulty"] for p in view["players"]] == [None, None, "easy", "hard"]


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_full_ai_game_all_difficulties(difficulty):
    room = make_room(total=3, local=["Host"], ai=2, deck='mixed', difficulty=difficulty)
    assert all(s["difficulty"] == difficulty for s in room.seats if s["is_ai"])
    gs = room.state
    for _ in range(500):
        if gs.finished:
            break
        if gs.current_player == 0:
            hand = gs.table[0]["hand"]
            if hand:
                room.play_human(room.host_token, int(hand[0].value), {})
            else:
                room._skip_finished()
        else:
            room.last_ai_move = 0
            room.tick()
    assert gs.finished
    assert len(gs.cards_in_bar) + len(gs.cards_in_thrash) + len(gs.queue) == 36


def test_serialize_personalizes_hands():
    room = make_room(total=2, local=["Host"], ai=0)
    token, _ = room.claim_seats(["Friend"])
    host_view = room.serialize(room.host_token)
    friend_view = room.serialize(token)
    stranger_view = room.serialize(None)
    assert host_view["you_seats"] == [0] and len(host_view["hands"]["0"]) == 4
    assert friend_view["you_seats"] == [1] and "0" not in friend_view["hands"]
    assert stranger_view["you_seats"] == [] and stranger_view["hands"] == {}


# ---------- persistence (db-backed sessions, archive, leaderboard) ----------

import tempfile
import time as _time


def _fresh_db(tmp_path):
    server.db._conn = None
    server.db.init(str(tmp_path / "test.db"))


def test_room_survives_restart(tmp_path):
    _fresh_db(tmp_path)
    room = make_room(total=2, local=["Host"], ai=1)
    gs = room.state
    card = gs.table[0]["hand"][0]
    room.play_human(room.host_token, int(card.value), {})
    room.persist()
    before = room.serialize(room.host_token)

    # simulate a server restart: rebuild the room from the database
    restored = server.Room.from_doc(server.db.load_room(room.id))
    after = restored.serialize(room.host_token)
    assert after["queue"] == before["queue"]
    assert after["hands"] == before["hands"]
    assert after["log_total"] == before["log_total"]
    assert restored.seats == room.seats

    # the old token still plays in the restored room
    restored.last_ai_move = 0
    restored.tick()  # AI turn
    gs2 = restored.state
    assert gs2.current_player == 0
    card = gs2.table[0]["hand"][0]
    restored.play_human(room.host_token, int(card.value), {})


def test_finished_game_recorded_and_leaderboard(tmp_path):
    _fresh_db(tmp_path)
    room = make_room(total=2, local=["Winner", "Loser"], ai=0, deck='new_beasts')
    gs = room.state
    for _ in range(100):
        if gs.finished:
            break
        p = gs.current_player
        hand = gs.table[p]["hand"]
        if hand:
            room.play_human(room.host_token, int(hand[0].value), {})
        else:
            room._skip_finished()
    assert gs.finished
    room.persist()
    assert room.recorded
    room.persist()  # idempotent: no double recording

    games = server.db.recent_games()
    assert len(games) == 1
    assert games[0]["deck"] == "new_beasts"
    assert {p["name"] for p in games[0]["players"]} == {"Winner", "Loser"}
    assert sum(p["won"] for p in games[0]["players"]) >= 1

    month = _time.strftime("%Y-%m")
    board = server.db.leaderboard(month)
    assert {r["name"] for r in board} == {"Winner", "Loser"}
    assert board[0]["wins"] >= board[-1]["wins"]
    assert server.db.leaderboard("2001-01") == []


def test_prune_keeps_long_running_games(tmp_path):
    _fresh_db(tmp_path)
    now = _time.time()
    day = 24 * 3600
    server.db.save_room("paused-3d", {"x": 1}, now - 3 * day, finished=False)
    server.db.save_room("dead-20d", {"x": 1}, now - 20 * day, finished=False)
    server.db.save_room("done-1d", {"x": 1}, now - 1 * day, finished=True)
    server.db.save_room("done-5d", {"x": 1}, now - 5 * day, finished=True)
    server.db.prune_rooms(now - server.UNFINISHED_TTL, now - server.FINISHED_TTL)
    assert server.db.load_room("paused-3d")    # mid-game pause survives weeks
    assert server.db.load_room("done-1d")
    assert server.db.load_room("dead-20d") is None
    assert server.db.load_room("done-5d") is None


def test_fair_start_varies_opener_and_seating():
    import random
    random.seed(123)
    openers, host_seats = set(), set()
    for _ in range(30):
        room = server.Room(total=4, local_names=["Host"], ai=["easy"] * 3,
                           deck='classic', fair_start=True)
        openers.add(room.state.current_player)
        host_seats.add(room.seats_of(room.host_token)[0])
    assert len(openers) > 1, "the same player always starts"
    assert len(host_seats) > 1, "the host always sits in seat 0"


def test_misplay_review_recorded(tmp_path):
    _fresh_db(tmp_path)
    room = make_room(total=2, local=["Hero"], ai=["ultra"])
    gs = room.state
    for _ in range(100):
        if gs.finished:
            break
        p = gs.current_player
        if p == 0:
            hand = gs.table[0]["hand"]
            if hand:
                room.play_human(room.host_token, int(hand[0].value), {})
            else:
                room._skip_finished()
        else:
            room.last_ai_move = 0
            room.tick()
    assert gs.finished
    moves = room.reviews.get("0", [])
    assert len(moves) == 12      # every human move was analyzed
    for m in moves:
        assert m["best_score"] >= m["chosen_score"] - 1e-6
        assert "played" in m and "best" in m
    # only the owner sees their review
    view = room.serialize(room.host_token)
    assert len(view["review"]["0"]) == 12
    stranger = room.serialize(None)
    assert stranger.get("review", {}) == {}
    # reviews survive a restart
    room.persist()
    restored = server.Room.from_doc(server.db.load_room(room.id))
    assert len(restored.reviews["0"]) == 12
