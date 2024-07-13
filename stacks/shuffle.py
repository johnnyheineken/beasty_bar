import random

from cards.first_game_deck import Chameleon, Croc, Gazelle, Hippo, Kangaroo, Lion, Monkey, Parrot, Seal, Skunk, Snake, \
    Zebra
from cards.base import ANIMALS

NORMAL_CARDS = [Skunk, Kangaroo, Monkey, Seal, Zebra, Gazelle, Snake, Croc, Hippo, Lion]
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


def init(strategies: dict):
    players = {}
    for player, strategy in strategies.items():
        all_cards = NORMAL_CARDS.copy()
        chameleon = strategy.chameleon() or Chameleon
        parrot = strategy.parrot() or Parrot
        all_cards += [chameleon, parrot]

        personal_cards = [card(player) for card in all_cards]
        random.shuffle(personal_cards)
        players[player] = {
            'hand': [personal_cards.pop() for _ in range(4)],
            'deck': [personal_cards.pop() for _ in range(6)],
            'thrown': personal_cards,
            'strategy': strategy(),
            'finished': False
        }
    return players
