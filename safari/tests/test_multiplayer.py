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
    return server.Room(total=total, local_names=local or ["Host"], ai=ai,
                       deck=deck, difficulty=difficulty)


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


@pytest.mark.parametrize("difficulty", ["easy", "medium", "hard"])
def test_full_ai_game_all_difficulties(difficulty):
    room = make_room(total=3, local=["Host"], ai=2, deck='mixed', difficulty=difficulty)
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
