import pyxel
from .constants import PLAYER_COLORS, ANIMAL_TO_ASSETS_MAPPING_SMALL, INVISIBLE_COLOR, ANIMAL_TO_ASSETS_MAPPING_BIG, \
    ASSET_H_BIG, ASSET_W_BIG, ASSET_H_SMALL, ASSET_W_SMALL


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
        pyxel.rect(self.x, self.y, ASSET_W_SMALL, ASSET_H_SMALL, PLAYER_COLORS[self.owner])
        pyxel.blt(self.x, self.y, 0, ANIMAL_TO_ASSETS_MAPPING_SMALL[self.card_value][0],
                  ANIMAL_TO_ASSETS_MAPPING_SMALL[self.card_value][1], ASSET_W_SMALL, ASSET_H_SMALL, INVISIBLE_COLOR)

    def draw_big(self, x=None, y=None):
        if x is not None and y is not None:
            self.x = x
            self.y = y
        pyxel.rect(self.x, self.y, ASSET_W_BIG, ASSET_H_BIG, PLAYER_COLORS[self.owner])
        pyxel.blt(self.x, self.y, 0, ANIMAL_TO_ASSETS_MAPPING_BIG[self.card_value][0],
                  ANIMAL_TO_ASSETS_MAPPING_BIG[self.card_value][1], ASSET_W_BIG, ASSET_H_BIG, INVISIBLE_COLOR)

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
            self.x += (self.target_x - self.x) * 0.2
            self.y += (self.target_y - self.y) * 0.2
            if abs(self.x - self.target_x) < 0.5 and abs(self.y - self.target_y) < 0.5:
                print(f"Card reached target position ({self.target_x}, {self.target_y})")
                self.x = self.target_x
                self.y = self.target_y
                self.is_moving = False
                if self.finished_moving_callback:
                    self.finished_moving_callback(self, self.owner)
