import json
import pytest
from safari.game_state import GameState, STRATEGY_MAP
from safari.stacks.queue import Queue
from safari.cards.first_game_deck import Lion, Monkey, Hippo
from safari.players.strategies import Max


@pytest.fixture
def sample_game_state():
    return GameState(
        cards_in_bar=[Lion(0)],
        cards_in_thrash=[Monkey(1)],
        queue=Queue([Lion(0), Monkey(1)]),
        old_queue=Queue([Hippo(2)]),
        players=[0, 1, 2],
        current_player=0,
        n_players=3,
        turn_number=5,
        table={
            0: {'hand': [Lion(0), Monkey(0)], 'deck': [Hippo(0)], 'thrown': [], 'strategy': Max(), 'finished': False},
            1: {'hand': [Monkey(1), Hippo(1)], 'deck': [Lion(1)], 'thrown': [], 'strategy': Max(), 'finished': False},
            2: {'hand': [Hippo(2), Lion(2)], 'deck': [Monkey(2)], 'thrown': [], 'strategy': Max(), 'finished': False},
        },
        finished=False,
        results={}
    )


def test_game_state_initialization(sample_game_state):
    assert len(sample_game_state.cards_in_bar) == 1
    assert len(sample_game_state.cards_in_thrash) == 1
    assert len(sample_game_state.queue) == 2
    assert len(sample_game_state.old_queue) == 1
    assert sample_game_state.current_player == 0
    assert sample_game_state.n_players == 3
    assert sample_game_state.turn_number == 5
    assert not sample_game_state.finished


def test_game_state_to_json(sample_game_state):
    json_str = sample_game_state.to_json()
    assert isinstance(json_str, str)
    assert "cards_in_bar" in json_str
    assert "cards_in_thrash" in json_str
    assert "queue" in json_str
    assert "old_queue" in json_str
    assert "table" in json_str


def test_game_state_from_json(sample_game_state):
    json_str = sample_game_state.to_json()
    reconstructed_state = GameState.from_json(json_str)

    assert len(reconstructed_state.cards_in_bar) == len(sample_game_state.cards_in_bar)
    assert len(reconstructed_state.cards_in_thrash) == len(sample_game_state.cards_in_thrash)
    assert len(reconstructed_state.queue) == len(sample_game_state.queue)
    assert len(reconstructed_state.old_queue) == len(sample_game_state.old_queue)
    assert reconstructed_state.current_player == sample_game_state.current_player
    assert reconstructed_state.n_players == sample_game_state.n_players
    assert reconstructed_state.turn_number == sample_game_state.turn_number
    assert reconstructed_state.finished == sample_game_state.finished

    for player in sample_game_state.table:
        assert player in reconstructed_state.table
        assert len(reconstructed_state.table[player]['hand']) == len(sample_game_state.table[player]['hand'])
        assert len(reconstructed_state.table[player]['deck']) == len(sample_game_state.table[player]['deck'])
        assert isinstance(reconstructed_state.table[player]['strategy'], Max)


def test_unknown_strategy_error(sample_game_state):
    json_str = sample_game_state.to_json()
    data = json.loads(json_str)
    data['table']['0']['strategy'] = 'UnknownStrategy'
    modified_json = json.dumps(data)

    with pytest.raises(ValueError, match="Unknown strategy: UnknownStrategy"):
        GameState.from_json(modified_json)


def test_update_queue(sample_game_state):
    new_card = Hippo(1)
    sample_game_state.update_queue(new_card)

    assert new_card in sample_game_state.queue
    assert len(sample_game_state.old_queue) == len(sample_game_state.queue) - 1


def test_add_winner(sample_game_state):
    new_winner = Monkey(2)
    initial_bar_count = len(sample_game_state.cards_in_bar)
    sample_game_state.add_winner(new_winner)
    assert len(sample_game_state.cards_in_bar) == initial_bar_count + 1
    assert new_winner in sample_game_state.cards_in_bar


def test_add_loser(sample_game_state):
    new_loser = Hippo(1)
    initial_thrash_count = len(sample_game_state.cards_in_thrash)
    sample_game_state.add_loser(new_loser)
    assert len(sample_game_state.cards_in_thrash) == initial_thrash_count + 1
    assert new_loser in sample_game_state.cards_in_thrash


def test_next_player(sample_game_state):
    initial_player = sample_game_state.current_player
    sample_game_state.next_player()
    assert sample_game_state.current_player == (initial_player + 1) % sample_game_state.n_players


def test_increment_turn(sample_game_state):
    initial_turn = sample_game_state.turn_number
    sample_game_state.increment_turn()
    assert sample_game_state.turn_number == initial_turn + 1


def test_is_game_finished(sample_game_state):
    assert not sample_game_state.is_game_finished()

    for player in sample_game_state.table:
        sample_game_state.table[player]['finished'] = True

    assert sample_game_state.is_game_finished()


def test_update_results(sample_game_state):
    sample_game_state.cards_in_bar = [Lion(0), Monkey(1), Hippo(0)]
    sample_game_state.update_results()
    assert sample_game_state.results[0] == Lion(0).point_value + Hippo(0).point_value
    assert sample_game_state.results[1] == Monkey(1).point_value
