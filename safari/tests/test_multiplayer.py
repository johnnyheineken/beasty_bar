import importlib.util
import sys
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "webapp_server", Path(__file__).resolve().parents[2] / "webapp" / "server.py")
server = importlib.util.module_from_spec(_spec)
sys.modules["webapp_server"] = server
_spec.loader.exec_module(server)


def make_room(total=4, humans=1, deck='classic'):
    return server.Room(total=total, humans=humans, deck=deck, host_name="Host")


def test_invite_works_with_default_one_human():
    """Regression: a friend opening the invite link of a 1-human game used
    to get 'room already full' — now they take over an AI seat."""
    room = make_room(total=4, humans=1)
    assert room.started  # solo + AI games start immediately
    seat, token = room.claim_seat("Friend")
    assert room.seats[seat]["is_ai"] is False
    assert room.seats[seat]["name"] == "Friend"
    assert token
    assert room.started  # still started, friend plays the converted seat


def test_open_human_seats_are_claimed_first():
    room = make_room(total=4, humans=3)
    assert not room.started
    s1, _ = room.claim_seat("A")
    s2, _ = room.claim_seat("B")
    assert (s1, s2) == (1, 2)
    assert room.started
    # next joiner converts an AI seat
    s3, _ = room.claim_seat("C")
    assert s3 == 3
    assert all(not s["is_ai"] for s in room.seats)


def test_room_truly_full():
    room = make_room(total=2, humans=2)
    room.claim_seat("Friend")
    with pytest.raises(server.GameError, match="full"):
        room.claim_seat("Late")


def test_join_midgame_takes_over_ai():
    room = make_room(total=3, humans=1)
    # let some AI turns happen
    room.last_ai_move = 0
    room.tick()
    seat, token = room.claim_seat("Friend")
    assert room.seats[seat]["is_ai"] is False
    # the converted seat is no longer auto-played
    gs = room.state
    while not gs.finished and gs.current_player != seat:
        room.last_ai_move = 0
        before = gs.turn_number
        room.tick()
        if gs.turn_number == before and gs.current_player == 0:
            # host's (unplayed) turn would block — play for them
            room.play_human(room.seats[0]["token"], int(gs.table[0]["hand"][0].value), {})
    turn = gs.turn_number
    room.tick()
    assert gs.turn_number == turn  # tick must NOT play for the human seat


def test_full_game_with_two_humans():
    room = make_room(total=4, humans=2)
    seat, token = room.claim_seat("Friend")
    tokens = {0: room.seats[0]["token"], seat: token}
    gs = room.state
    for _ in range(500):
        if gs.finished:
            break
        p = gs.current_player
        if p in tokens:
            hand = gs.table[p]["hand"]
            if hand:
                room.play_human(tokens[p], int(hand[0].value), {})
            else:
                room._skip_finished()
        else:
            room.last_ai_move = 0
            room.tick()
    assert gs.finished
    assert len(gs.cards_in_bar) + len(gs.cards_in_thrash) + len(gs.queue) == 48


def test_serialize_personalizes_hand():
    room = make_room(total=2, humans=2)
    seat, token = room.claim_seat("Friend")
    host_view = room.serialize(room.seats[0]["token"])
    friend_view = room.serialize(token)
    stranger_view = room.serialize(None)
    assert host_view["you"] == 0 and len(host_view["hand"]) == 4
    assert friend_view["you"] == 1 and len(friend_view["hand"]) == 4
    assert stranger_view["you"] is None and stranger_view["hand"] == []
