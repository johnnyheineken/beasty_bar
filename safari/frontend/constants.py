import pyxel
from safari.cards.base import ANIMALS

INVISIBLE_COLOR = pyxel.COLOR_PURPLE

PLAYER_COLORS = [
    pyxel.COLOR_RED,
    pyxel.COLOR_GREEN,
    pyxel.COLOR_YELLOW,
    pyxel.COLOR_NAVY,
]

MAPPING = {
    ANIMALS.SKUNK: (0, 0),
    ANIMALS.PARROT: (16, 0),
    ANIMALS.KANGAROO: (32, 0),
    ANIMALS.MONKEY: (48, 0),
    ANIMALS.CHAMELEON: (0, 16),
    ANIMALS.SEAL: (16, 16),
    ANIMALS.ZEBRA: (32, 16),
    ANIMALS.GAZELLE: (48, 16),
    ANIMALS.SNAKE: (0, 32),
    ANIMALS.CROC: (16, 32),
    ANIMALS.HIPPO: (32, 32),
    ANIMALS.LION: (48, 32),
}
