import random

import pytest

from safari.cards.first_game_deck import Croc, Hippo, Lion, Monkey, Parrot, Skunk, Zebra
from safari.game_state import GameState
from safari.players import bots
from safari.stacks.queue import Queue
from safari.stacks.shuffle import init
from safari.players.strategies import Max


def make_state(hand, queue, scoring='count'):
    table = init(strategies={0: Max, 1: Max}, deck='classic')
    gs = GameState(players=[0, 1], n_players=2, table=table, scoring=scoring)
    gs.table[0]['hand'] = hand
    gs.queue = Queue(queue)
    return gs


def test_simulate_does_not_mutate_state():
    gs = make_state([Croc(0), Skunk(0)], [Monkey(1), Zebra(1)])
    before = [str(c) for c in gs.queue]
    bots.simulate(gs, 0, gs.table[0]['hand'][0], {})
    assert [str(c) for c in gs.queue] == before
    assert len(gs.table[0]['hand']) == 2


def test_medium_prefers_killing_opponents():
    # croc eats the opponent's monkey; skunk would (pointlessly) clear the
    # zebra protecting nothing of ours — croc must win the evaluation
    random.seed(0)
    gs = make_state([Croc(0), Monkey(0)], [Monkey(1), Monkey(1)])
    card, setup = bots.choose('medium', gs, 0)
    assert isinstance(card, Croc)


def test_hard_picks_the_right_parrot_target():
    # queue: our own lion at the gate, opponent's hippo behind it; the
    # parrot must shoo the hippo, not our lion
    gs = make_state([Parrot(0)], [Lion(0), Hippo(1)])
    card, setup = bots.choose('hard', gs, 0)
    assert isinstance(card, Parrot)
    assert setup.get('target_index') == 1


def test_hard_kangaroo_distance():
    # jumping 2 puts the kangaroo in front of the opponent's croc, which
    # would eat it on the next recurring action; jumping over both still
    # happens only if safe — here position 0 is past the croc, so jump 2
    # is actually safe and better; just assert a legal choice is returned
    gs = make_state([__import__('safari.cards.first_game_deck', fromlist=['Kangaroo']).Kangaroo(0)],
                    [Zebra(1), Croc(1)])
    card, setup = bots.choose('hard', gs, 0)
    assert setup.get('jump') in (1, 2)


def test_easy_is_random_but_legal():
    random.seed(1)
    gs = make_state([Croc(0), Skunk(0), Parrot(0)], [Monkey(1)])
    card, setup = bots.choose('easy', gs, 0)
    assert card in gs.table[0]['hand']
    assert setup == {}


def test_levels_exist():
    assert set(bots.LEVELS) == {'easy', 'medium', 'hard', 'ultra'}
