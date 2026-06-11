import pytest

from safari.cards.new_beasts_deck import Bat, Bear, Cheetah, Dog, Llama, Ostrich, Peacock, Penguin, Porcupine, \
    Rhino, Tiger, Vulture
from safari.game_state import GameState
from safari.stacks.queue import Queue
from safari.tests.test_animals import compare


def test_rhino_rams_strongest():
    # rulebook example 5: the strongest animal is rammed, rhino takes its place
    q = Queue([Penguin(0), Ostrich(0), Bat(0)])
    q, dropped = q.resolve(Rhino(1))
    compare(q, Queue([Penguin(0), Rhino(1), Bat(0)]))
    assert dropped == [Ostrich(0)]


def test_bear_sends_two_weakest_species_back():
    # rulebook example 6: peacock and both dogs re-queue behind the bear
    q = Queue([Peacock(0), Ostrich(0), Dog(1), Dog(2)])
    q, dropped = q.resolve(Bear(1))
    compare(q, Queue([Ostrich(0), Bear(1), Peacock(0), Dog(1), Dog(2)]))
    assert dropped == []


def test_tiger_jumps_over_stronger_and_eats():
    # rulebook example 7: tiger leaps over the rhino and eats the peacock
    q = Queue([Peacock(0), Rhino(0)])
    q, dropped = q.resolve(Tiger(1))
    compare(q, Queue([Tiger(1), Rhino(0)]))
    assert dropped == [Peacock(0)]


def test_tiger_blocked_by_stronger_target():
    # rulebook example 8: the animal two steps ahead is a stronger bear
    q = Queue([Peacock(0), Dog(0), Bear(0), Porcupine(0)])
    q, dropped = q.resolve(Tiger(1))
    compare(q, Queue([Peacock(0), Dog(0), Bear(0), Porcupine(0), Tiger(1)]))
    assert dropped == []


def test_cheetah_eats_weakest():
    # rulebook example 9: cheetah eats one of the weakest animals
    q = Queue([Ostrich(0), Bear(0), Penguin(1), Penguin(2)])
    cheetah = Cheetah(1)
    cheetah.target_index = 3
    q, dropped = q.resolve(cheetah)
    compare(q, Queue([Ostrich(0), Bear(0), Penguin(1), Cheetah(1)]))
    assert dropped == [Penguin(2)]


def test_llama_spits_recurringly():
    # llama sends the weaker animal in front of it to the end of the line
    q = Queue([Bear(0), Porcupine(0)])
    q, dropped = q.resolve(Llama(1))
    compare(q, Queue([Bear(0), Llama(1), Porcupine(0)]))
    assert dropped == []


def test_llama_does_not_spit_at_stronger():
    q = Queue([Tiger(0)])
    q, dropped = q.resolve(Llama(1))
    compare(q, Queue([Tiger(0), Llama(1)]))


def test_porcupine_reflects_tiger():
    # rulebook example 10: tiger jumps onto the porcupine and lands on THAT'S IT
    q = Queue([Porcupine(0), Peacock(0)])
    q, dropped = q.resolve(Tiger(1))
    compare(q, Queue([Porcupine(0), Peacock(0)]))
    assert dropped == [Tiger(1)]


def test_porcupine_reflects_rhino_and_cheetah():
    q, dropped = Queue([Porcupine(0)]).resolve(Rhino(1))
    compare(q, Queue([Porcupine(0)]))
    assert dropped == [Rhino(1)]

    q, dropped = Queue([Porcupine(0), Bear(0)]).resolve(Cheetah(1))
    compare(q, Queue([Porcupine(0), Bear(0)]))
    assert dropped == [Cheetah(1)]


def test_ostrich_runs_past_odd():
    # rulebook example 11: ostrich passes cheetah & porcupine, stops behind the dog
    q = Queue([Dog(0), Porcupine(0), Cheetah(0)])
    ostrich = Ostrich(1)
    ostrich.parity = 'odd'
    q, dropped = q.resolve(ostrich)
    compare(q, Queue([Dog(0), Ostrich(1), Porcupine(0), Cheetah(0)]))


def test_penguin_imitates_hand_card():
    # rulebook example 12: penguin acts as a tiger, eats the cheetah
    q = Queue([Cheetah(0), Rhino(0)])
    penguin = Penguin(1)
    penguin.imitate_class = Tiger
    q, dropped = q.resolve(penguin)
    compare(q, Queue([Penguin(1), Rhino(0)]))
    assert dropped == [Cheetah(0)]
    assert penguin.value == Penguin.value  # strength reverts after the action


def test_dog_sorts_weakest_first_stable():
    # rulebook example 13: bat at the gate (burns), older dog before newer one
    q = Queue([Bear(0), Bat(0), Dog(1)])
    q, dropped = q.resolve(Dog(2))
    # weakest first: bat would lead, but it burns up at the gate
    compare(q, Queue([Dog(1), Dog(2), Bear(0)]))
    assert dropped == [Bat(0)]


def test_peacock_in_front_of_strongest():
    # rulebook example 14
    q = Queue([Penguin(0), Bear(0), Ostrich(0), Tiger(0)])
    peacock = Peacock(1)
    peacock.target_index = 1
    q, dropped = q.resolve(peacock)
    compare(q, Queue([Penguin(0), Peacock(1), Bear(0), Ostrich(0), Tiger(0)]))


def test_bat_replaces_target_and_burns_at_gate():
    # rulebook example 16: bat takes the tiger's place
    q = Queue([Dog(0), Tiger(0), Porcupine(0)])
    bat = Bat(1)
    bat.target_index = 1
    q, dropped = q.resolve(bat)
    compare(q, Queue([Dog(0), Bat(1), Porcupine(0)]))
    assert dropped == [Tiger(0)]

    # taking first position burns the bat immediately
    q = Queue([Dog(0)])
    bat = Bat(1)
    bat.target_index = 0
    q, dropped = q.resolve(bat)
    compare(q, Queue([]))
    assert dropped == [Dog(0), Bat(1)]


def _vulture_state(trash):
    gs = GameState(players=[0, 1], n_players=2)
    gs.cards_in_thrash = trash
    return gs


def test_vulture_revives_top_of_trash():
    gs = _vulture_state([Bear(0), Peacock(1)])
    gs.queue = Queue([Tiger(0)])
    gs.update_queue(Vulture(1))
    # the peacock re-joins and acts (stands in front of the tiger);
    # the vulture itself lands on THAT'S IT afterwards
    compare(gs.queue, Queue([Peacock(1), Tiger(0)]))
    assert gs.cards_in_thrash == [Bear(0), Vulture(1)]


def test_double_vulture_enters_bar():
    gs = _vulture_state([Vulture(0)])
    gs.update_queue(Vulture(1))
    assert gs.cards_in_bar == [Vulture(0), Vulture(1)]
    assert gs.cards_in_thrash == []


def test_vulture_with_empty_trash():
    gs = _vulture_state([])
    gs.queue = Queue([Bear(0)])
    gs.update_queue(Vulture(1))
    compare(gs.queue, Queue([Bear(0)]))
    assert gs.cards_in_thrash == [Vulture(1)]


def test_points_scoring():
    gs = GameState(players=[0, 1], n_players=2, scoring='points')
    gs.cards_in_bar = [Rhino(0), Bat(1), Peacock(1)]
    gs.update_results()
    assert gs.results[0] == 3   # rhino
    assert gs.results[1] == 6   # bat 4 + peacock 2
    assert gs.get_winners() == [1]


def test_chameleon_imitates_new_beasts():
    # cross-set: chameleon (mixed deck) imitating an ostrich must not crash
    from safari.cards.first_game_deck import Chameleon
    q = Queue([Ostrich(0), Porcupine(0)])
    chameleon = Chameleon(1)
    chameleon.imitate = 6  # ostrich
    chameleon.parity = 'odd'
    q, dropped = q.resolve(chameleon)
    compare(q, Queue([Ostrich(0), Chameleon(1), Porcupine(0)]))


def test_penguin_imitates_bat_with_default_target():
    q = Queue([Dog(0), Bear(0)])
    penguin = Penguin(1)
    penguin.imitate_class = Bat
    q, dropped = q.resolve(penguin)
    compare(q, Queue([Dog(0), Penguin(1)]))
    assert dropped == [Bear(0)]
