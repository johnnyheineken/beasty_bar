import pytest

from safari.cards.base import ANIMALS
from safari.cards.first_game_deck import Chameleon, Croc, Gazelle, Hippo, Kangaroo, Lion, Monkey, Parrot, Seal, \
    Skunk, Snake, Zebra
from safari.stacks.queue import Queue


def compare(a: Queue, b: Queue):
    for i, j in zip(a, b):
        assert i.name == j.name, f'{a=}\n {b=}'
        assert i.value == j.value, f'{a=}\n {b=}'
        assert i.player == j.player, f'{a=}\n {b=}'


@pytest.mark.parametrize('queue,final', [
    (
            Queue([Monkey(1), Lion(1)]),
            Queue([Monkey(1), Lion(1), Hippo(1)])
    ),
    (
            Queue([Monkey(1), Monkey(0)]),
            Queue([Hippo(1), Monkey(1), Monkey(0)])
    )
])
def test_hippo(queue, final):
    queue, dropped = queue.resolve(Hippo(1))
    compare(queue, final)


@pytest.mark.parametrize('queue,final', [
    (
            Queue([Monkey(1), Lion(1)]),
            Queue([Monkey(1), Lion(1)])
    ),
    (
            Queue([Monkey(1), Monkey(0)]),
            Queue([Lion(1)])
    ),
    (
            Queue([Hippo(1)]),
            Queue([Lion(1), Hippo(1)])
    )
])
def test_lion(queue, final):
    queue, dropped = queue.resolve(Lion(1))
    compare(queue, final)


@pytest.mark.parametrize('queue,final', [
    (
            Queue([Monkey(1), Lion(1)]),
            Queue([Monkey(0), Monkey(1), Lion(1)])
    ),
    (
            Queue([Lion(1), Monkey(1)]),
            Queue([Monkey(0), Monkey(1), Lion(1)])
    ),
    (
            Queue([Hippo(1)]),
            Queue([Hippo(1), Monkey(0)])
    ),
    (
            Queue([Hippo(1), Monkey(1)]),
            Queue([Monkey(0), Monkey(1)])
    )
])
def test_monkey(queue, final):
    queue, dropped = queue.resolve(Monkey(0))
    compare(queue, final)


@pytest.mark.parametrize('queue,final', [
    (
            Queue([Monkey(1), Lion(1)]),
            Queue([Seal(1), Lion(1), Monkey(1)])
    ),
    (
            Queue([Croc(1)]),
            Queue([Croc(1)])
    ),
    (
            Queue([Hippo(1)]),
            Queue([Hippo(1), Seal(1)])
    ),
    (
            Queue([Hippo(1), Croc(1)]),
            Queue([Hippo(1), Croc(1)])
    ),
])
def test_seal(queue, final):
    queue, dropped = queue.resolve(Seal(1))
    compare(queue, final)


@pytest.mark.parametrize('queue,final', [
    (
            Queue([Hippo(1)]),
            Queue([Hippo(1), Chameleon(1)])
    ),
    (
            Queue([Croc(1), Skunk(1)]),
            Queue([Croc(1), Chameleon(1)])
    ),
    (
            Queue([Lion(1), Skunk(1)]),
            Queue([Lion(1), Skunk(1)])
    ),
    (
            Queue([Chameleon(0)]),
            Queue([Chameleon(0), Chameleon(1)])
    ),
])
def test_chameleon(queue, final):
    queue, dropped = queue.resolve(Chameleon(1))
    compare(queue, final)


@pytest.mark.parametrize('queue,final', [
    (
            Queue([Hippo(1)]),
            Queue([Skunk(1)])
    ),
    (
            Queue([Hippo(1), Croc(0), Croc(1)]),
            Queue([Skunk(1)])
    ),
    (
            Queue([Lion(1), Hippo(1), Croc(1)]),
            Queue([Croc(1), Skunk(1)])
    ),
    (
            Queue([Skunk(0)]),
            Queue([Skunk(0), Skunk(1)])
    ),
])
def test_skunk(queue, final):
    queue, dropped = queue.resolve(Skunk(1))
    compare(queue, final)


@pytest.mark.parametrize('queue,final', [
    (
            Queue([Hippo(1)]),
            Queue([Parrot(1)])
    ),
    (
            # default target: the strongest animal NOT owned by the parrot's
            # player (here Croc(0)); Hippo(1) and Croc(1) are its own
            Queue([Hippo(1), Croc(0), Croc(1)]),
            Queue([Hippo(1), Croc(1), Parrot(1)])
    ),
    (
            Queue([Lion(1), Hippo(1), Croc(1)]),
            Queue([Hippo(1), Croc(1), Parrot(1)])
    ),
    (
            Queue([Skunk(0)]),
            Queue([Parrot(1)])
    ),
])
def test_parrot(queue, final):
    queue, dropped = queue.resolve(Parrot(1))
    compare(queue, final)


@pytest.mark.parametrize('queue,final', [
    (
            Queue([Parrot(1), Parrot(0)]),
            Queue([Parrot(1), Gazelle(1), Parrot(0)])
    ),
    (
            Queue([Hippo(1), Croc(0), Croc(1)]),
            Queue([Hippo(1), Croc(0), Croc(1), Gazelle(1)])
    ),
])
def test_gazelle(queue, final):
    queue, dropped = queue.resolve(Gazelle(1))
    compare(queue, final)


@pytest.mark.parametrize('queue,added,final', [
    (
            Queue([Chameleon(3), Gazelle(0), Gazelle(1)]),
            Zebra(2),
            Queue([Gazelle(0), Gazelle(1), Chameleon(3), Zebra(2)])
    )
])
def test_random(queue, added, final):
    queue, dropped = queue.resolve(added)
    compare(queue, final)

def test_added_and_stopped_croc():
    q = Queue([Gazelle(3), Gazelle(2), Zebra(1)])
    q, dropped = q.resolve(Croc(2))
    assert dropped == []

def test_added_seal_to_croc():
    q = Queue([Croc(2), Zebra(0), Croc(1)])
    q, dropped = q.resolve(Seal(3))
    assert dropped == [Seal(3)]
    assert q == Queue([Croc(1), Zebra(0), Croc(2)])


def test_snake_sort_is_stable():
    # Rule: "Members of the same species don't change the order among them."
    q = Queue([Snake(0), Zebra(1), Parrot(0)])
    q, dropped = q.resolve(Snake(1))
    compare(q, Queue([Snake(0), Snake(1), Zebra(1), Parrot(0)]))
    assert dropped == []


def test_gazelle_does_not_pass_equal_gazelle():
    # The giraffe passes only strictly weaker animals.
    q = Queue([Gazelle(0)])
    q, dropped = q.resolve(Gazelle(1))
    compare(q, Queue([Gazelle(0), Gazelle(1)]))


def test_kangaroo_jumps_one_or_two():
    kangaroo = Kangaroo(1)
    kangaroo.jump = 1
    q, _ = Queue([Parrot(0), Zebra(0)]).resolve(kangaroo)
    compare(q, Queue([Parrot(0), Kangaroo(1), Zebra(0)]))

    kangaroo = Kangaroo(1)
    kangaroo.jump = 2
    q, _ = Queue([Parrot(0), Zebra(0)]).resolve(kangaroo)
    compare(q, Queue([Kangaroo(1), Parrot(0), Zebra(0)]))


def test_parrot_chosen_target():
    parrot = Parrot(1)
    parrot.target_index = 1
    q, dropped = Queue([Hippo(0), Skunk(0)]).resolve(parrot)
    compare(q, Queue([Hippo(0), Parrot(1)]))
    assert dropped == [Skunk(0)]


def test_chameleon_chosen_species():
    chameleon = Chameleon(1)
    chameleon.imitate = ANIMALS.MONKEY
    q, dropped = Queue([Hippo(0), Monkey(0)]).resolve(chameleon)
    compare(q, Queue([Chameleon(1), Monkey(0)]))
    assert dropped == [Hippo(0)]
    assert chameleon.value == ANIMALS.CHAMELEON  # strength reverts after the action