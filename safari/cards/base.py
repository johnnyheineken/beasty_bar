from enum import Enum

from safari.cards import NAMES, PLAYERS, SHORT_NAMES


class Card:
    value: int
    point_value: int
    repeating_action: bool = False
    laying: bool = False

    def __init__(self, player):
        self.player = player
        self.name = NAMES[self.__class__.__name__]
        self.short_name = SHORT_NAMES[self.__class__.__name__] + PLAYERS[self.player]
        self.long_name = f'{self.name} {self.value} {PLAYERS[self.player]} ' \
               f'({self.point_value}pt)' \
               f'{" - repeating" if self.repeating_action else ""}'

    def action(self, queue):
        raise NotImplementedError

    def __str__(self):
        return f'{self.name} ({self.value}) {PLAYERS[self.player]} '

    def __repr__(self):
        return f'{self.__class__.__name__}({self.player})'

    def __eq__(self, other):
        return (self.name==other.name) & (self.player == other.player)


class ANIMALS(int, Enum):
    LION = 12
    HIPPO = 11
    CROC = 10
    SNAKE = 9
    GAZELLE = 8
    ZEBRA = 7
    SEAL = 6
    CHAMELEON = 5
    MONKEY = 4
    KANGAROO = 3
    PARROT = 2
    SKUNK = 1