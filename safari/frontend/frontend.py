import pyxel
from .constants import PLAYER_COLORS, MAPPING, INVISIBLE_COLOR


class TableCard:
    def __init__(self, card_value, owner):
        self.card_value = card_value
        self.owner = owner
        self.x = 0
        self.y = 0
        self.target_x = 0
        self.target_y = 0
        self.is_moving = False
        self.finished_moving_callback = None

    def draw_small(self, x=None, y=None):
        if x is not None and y is not None:
            self.x = x
            self.y = y
        pyxel.rect(self.x, self.y, 16, 16, PLAYER_COLORS[self.owner])
        pyxel.blt(self.x, self.y, 0, MAPPING[self.card_value][0], MAPPING[self.card_value][1], 16, 16, INVISIBLE_COLOR)

    def draw_big(self, x=None, y=None):
        if x is not None and y is not None:
            self.x = x
            self.y = y
        pyxel.rect(self.x, self.y, 32, 32, PLAYER_COLORS[self.owner])
        pyxel.blt(self.x, self.y, 0, MAPPING[self.card_value][0], MAPPING[self.card_value][1], 32, 32, INVISIBLE_COLOR)

    def start_move(self, start_x, start_y, target_x, target_y, callback=None):
        print(f"Starting move from ({start_x}, {start_y}) to ({target_x}, {target_y})")
        self.x = start_x
        self.y = start_y
        self.target_x = target_x
        self.target_y = target_y
        self.is_moving = True
        self.finished_moving_callback = callback

    def update_position(self):
        if self.is_moving:
            self.x += (self.target_x - self.x) * 0.1
            self.y += (self.target_y - self.y) * 0.1
            if abs(self.x - self.target_x) < 0.5 and abs(self.y - self.target_y) < 0.5:
                print(f"Card reached target position ({self.target_x}, {self.target_y})")
                self.x = self.target_x
                self.y = self.target_y
                self.is_moving = False
                if self.finished_moving_callback:
                    self.finished_moving_callback(self, self.owner)

