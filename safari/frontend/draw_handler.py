import pyxel
from safari.frontend import constants as cst
from safari.frontend.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from safari.frontend.ui_state import UIState, UIStateEnum
from safari.utils.helpers import create_logger

logger = create_logger(__name__)
N_LOGGING_FRAMES = 60
class DrawingHandler:
    def __init__(self):
        self.ui_state:UIState = UIState()
        logger.debug("DrawingHandler initialized")

    def log(self, message):
        if self.ui_state.frame_count % N_LOGGING_FRAMES:
            logger.debug(message)
    def draw(self, ui_state):
        self.ui_state = ui_state
        pyxel.cls(0)
        draw_handlers = {
            UIStateEnum.MENU: self.draw_menu,
            UIStateEnum.SUBMENU: self.draw_submenu,
            UIStateEnum.GAME: self.draw_game,
            UIStateEnum.END: self.draw_end,
            UIStateEnum.CHAMELEON: self.draw_game_with_highlight,
            UIStateEnum.PARROT: self.draw_game_with_highlight
        }
        current_state = self.ui_state.current_state
        self.log(f"Drawing UI for state: {current_state}")
        draw_handlers.get(current_state, lambda: None)()

        for card in self.ui_state.animating_cards:
            card.draw_big()
        self.log(f"Drew {len(self.ui_state.animating_cards)} animating cards")

    def draw_menu(self):
        self.draw_text_centered(35, 30, "Main Menu", pyxel.COLOR_WHITE)
        self.draw_button(30, 50, "Submenu")
        self.draw_button(30, 90, "Start Game")

    def draw_submenu(self):
        self.log("Drawing submenu")
        self.draw_text_centered(40, 30, "Submenu", pyxel.COLOR_WHITE)
        self.draw_button(30, 90, "Back")

    def draw_game(self):
        self.log("Drawing game screen")
        self.draw_background()
        self.draw_hand_cards()
        self.draw_table_card_slots()
        self.draw_table_cards()

    def draw_game_with_highlight(self):
        self.log("Drawing game screen with highlighted cards")
        self.draw_game()
        self.highlight_table_cards()

    def draw_end(self):
        self.log("Drawing end game screen")
        pyxel.cls(0)
        self.draw_text_centered(35, 30, "Game Over", pyxel.COLOR_WHITE)
        self.draw_button(30, 90, "Play Again")
        self.draw_button(30, 120, "Menu")

    def draw_background(self):
        pyxel.rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, pyxel.COLOR_DARK_BLUE)

    def draw_hand_cards(self):
        hand_start_x = (SCREEN_WIDTH - (len(self.ui_state.hand_cards) * cst.ASSET_W_BIG + (len(self.ui_state.hand_cards) - 1) * 4)) // 2
        hand_y = SCREEN_HEIGHT - cst.ASSET_H_BIG - 5
        for i, card in enumerate(self.ui_state.hand_cards):
            card.draw_big(hand_start_x + i * (cst.ASSET_W_BIG + 4), hand_y)

    def draw_table_card_slots(self):
        self.draw_card_slots((SCREEN_WIDTH - (5 * cst.ASSET_W_BIG + 4 * 4)) // 2, 60, 5)

    def draw_table_cards(self):
        start_x = (SCREEN_WIDTH - (5 * cst.ASSET_W_BIG + 4 * 4)) // 2
        y = 60
        for i, card in enumerate(self.ui_state.table_cards):
            card_x = start_x + i * (cst.ASSET_W_BIG + 4)
            card.draw_big(card_x, y)

    def highlight_table_cards(self):
        start_x = (SCREEN_WIDTH - (5 * cst.ASSET_W_BIG + 4 * 4)) // 2
        y = 60
        for i in range(len(self.ui_state.table_cards)):
            card_x = start_x + i * (cst.ASSET_W_BIG + 4)
            pyxel.rectb(card_x - 1, y - 1, cst.ASSET_W_BIG + 2, cst.ASSET_H_BIG + 2, pyxel.COLOR_YELLOW)

    @staticmethod
    def draw_text_centered(x, y, text, color):
        pyxel.text(x, y, text, color)

    @staticmethod
    def draw_button(x, y, text):
        pyxel.rect(x, y, 60, 20, pyxel.COLOR_RED)
        pyxel.text(x + 10, y + 7, text, pyxel.COLOR_WHITE)

    def draw_card_slots(self, start_x, y, count):
        self.log(f"Drawing {count} card slots at ({start_x}, {y})")
        for i in range(count):
            x = start_x + i * (cst.ASSET_W_BIG + 4)
            pyxel.rectb(x, y, cst.ASSET_W_BIG, cst.ASSET_H_BIG, pyxel.COLOR_WHITE)
