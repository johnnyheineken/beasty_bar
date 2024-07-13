import pytest

from cards.first_game_deck import Chameleon, Croc, Gazelle, Hippo, Lion, Monkey, Parrot, Seal, Skunk, Zebra
from stacks.queue import Queue


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
            Queue([Hippo(1), Croc(0), Croc(1)]),
            Queue([Croc(0), Croc(1), Parrot(1)])
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