import random

from safari.cards.first_game_deck import Chameleon, Croc, Gazelle, Hippo, Kangaroo, Lion, Monkey, Parrot, Seal, Skunk, Snake, \
    Zebra
from safari.cards.new_beasts_deck import NEW_BEASTS
from safari.cards.base import ANIMALS

NORMAL_CARDS = [Skunk, Kangaroo, Monkey, Seal, Zebra, Gazelle, Snake, Croc, Hippo, Lion]
CLASSIC_DECK = [Skunk, Parrot, Kangaroo, Monkey, Chameleon, Seal, Zebra, Gazelle, Snake, Croc, Hippo, Lion]
ANIMAL_MAPPING = {
    ANIMALS.CHAMELEON: Chameleon,
    ANIMALS.CROC: Croc,
    ANIMALS.GAZELLE: Gazelle,
    ANIMALS.HIPPO: Hippo,
    ANIMALS.KANGAROO: Kangaroo,
    ANIMALS.LION: Lion,
    ANIMALS.MONKEY: Monkey,
    ANIMALS.PARROT: Parrot,
    ANIMALS.SEAL: Seal,
    ANIMALS.SKUNK: Skunk,
    ANIMALS.SNAKE: Snake,
    ANIMALS.ZEBRA: Zebra
}

# every card class from both sets, keyed by class name (for serialization)
CARD_CLASSES = {cls.__name__: cls for cls in CLASSIC_DECK + NEW_BEASTS}

DECKS = {
    'classic': lambda: list(CLASSIC_DECK),
    'new_beasts': lambda: list(NEW_BEASTS),
    # Official combined rules: each player builds a deck with one animal of
    # each value (1-12) from the two sets. Here every player gets a random
    # pick per value.
    'mixed': lambda: [random.choice(pair) for pair in zip(sorted(CLASSIC_DECK, key=lambda c: int(c.value)),
                                                          sorted(NEW_BEASTS, key=lambda c: int(c.value)))],
}


def build_deck(deck: str):
    try:
        return DECKS[deck]()
    except KeyError:
        raise ValueError(f"Unknown deck '{deck}'; pick one of {sorted(DECKS)}")


def init(strategies: dict, deck: str = 'classic'):
    players = {}
    for player, strategy in strategies.items():
        all_cards = build_deck(deck)

        personal_cards = [card(player) for card in all_cards]
        random.shuffle(personal_cards)
        # Base rules: 4 cards in hand, the remaining 8 form the draw pile.
        players[player] = {
            'hand': [personal_cards.pop() for _ in range(4)],
            'deck': personal_cards,
            'thrown': [],
            'strategy': strategy(),
            'finished': False
        }
    return players
