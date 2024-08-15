import random
import pyxel
from safari.frontend.draw_handler import DrawingHandler
from safari.frontend.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASSET_W_BIG, ASSET_H_BIG
from safari.frontend.frontend import TableCard
from safari.frontend import constants as cst
from safari.frontend.ui_state import UIStateEnum, UIState
from safari.stacks.shuffle import init, ANIMAL_MAPPING
from safari.players.strategies import Max, Player
from logic import GameRunner
from safari.cards.base import ANIMALS
from safari.utils.helpers import create_logger

logger = create_logger(__name__)

PLAYER_START_POSITIONS = {
    0: (SCREEN_WIDTH // 2, 0),  # Bottom
    1: (SCREEN_WIDTH - 16, SCREEN_HEIGHT // 2),  # Right
    2: (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 16),  # Top
    3: (0, SCREEN_HEIGHT // 2),  # Left
}

# New constants for animation
ANIMATION_SPEED = 2
BAR_PILE_POS = (10, 10)
THRASH_PILE_POS = (SCREEN_WIDTH - 10 - ASSET_W_BIG, 10)


class App:
    def __init__(self):
        logger.info("Initializing Safari Bar application")
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Safari Bar")
        pyxel.mouse(True)
        pyxel.load("assets.pyxres")
        self.ui_state = UIState()
        self.drawing_handler = DrawingHandler()
        self.bar_pile_count = 0
        self.thrash_pile_count = 0
        logger.info("Application initialized, starting game loop")
        pyxel.run(self.update, self.draw)

    def reset_game(self):
        logger.info("Resetting game")
        self.setup_players()
        self.setup_game()
        self.update_game_state()

    def setup_players(self):
        self.strategies = {i: Max for i in range(4)}
        self.player_index = random.choice(list(self.strategies.keys()))
        self.player_start_positions = {(i - self.player_index) % 4: position for i, position in
                                       PLAYER_START_POSITIONS.items()}
        self.strategies[self.player_index] = Player

    def setup_game(self):
        table = init(strategies=self.strategies)
        self.game_runner = GameRunner(table)

    def update_game_state(self):
        game_state = self.game_runner.game_state

        if game_state.last_queue_evaluation:
            # Queue evaluation animation
            self.start_queue_evaluation_animation(game_state.last_queue_evaluation)
        else:
            # Regular update
            self.ui_state.update_table_cards([TableCard(i.value, i.player) for i in game_state.queue])

        self.ui_state.update_hand_cards([TableCard(i.value, self.player_index) for i in
                                         game_state.table[self.player_index]['hand']])
        logger.info('Game state updated')

    def start_queue_evaluation_animation(self, queue_evaluation):
        def find_table_card(card):
            for table_card in self.ui_state.table_cards:
                if table_card.card_value == card.value and table_card.owner == card.player:
                    return table_card
            logger.warning(f"Could not find TableCard for {card}")
            return None

        to_winners = [find_table_card(card) for card in queue_evaluation.to_winners]
        to_losers = [find_table_card(card) for card in queue_evaluation.to_losers]
        new_queue = [find_table_card(card) for card in queue_evaluation.new_queue]

        # Remove None values (cards that weren't found)
        to_winners = [card for card in to_winners if card is not None]
        to_losers = [card for card in to_losers if card is not None]
        new_queue = [card for card in new_queue if card is not None]

        for card in to_winners:
            card.start_move(card.x, card.y, BAR_PILE_POS[0], BAR_PILE_POS[1], self.on_card_to_bar)
            self.ui_state.add_animating_card(card)

        for card in to_losers:
            card.start_move(card.x, card.y, THRASH_PILE_POS[0], THRASH_PILE_POS[1], self.on_card_to_thrash)
            self.ui_state.add_animating_card(card)

        self.ui_state.update_table_cards(new_queue)

    def on_card_to_bar(self, card, owner=None):
        self.bar_pile_count += 1
        self.ui_state.animating_cards.remove(card)

    def on_card_to_thrash(self, card, owner=None):
        self.thrash_pile_count += 1
        self.ui_state.animating_cards.remove(card)

    def update(self):
        self.ui_state.increment_frame()

        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.handle_mouse_click()

        if self.ui_state.current_state == UIStateEnum.GAME and not self.ui_state.animation_in_progress:
            self.update_game()

        self.update_animations()

    def handle_mouse_click(self):
        x, y = pyxel.mouse_x, pyxel.mouse_y
        logger.info(f"Mouse clicked at ({x}, {y})")
        click_handlers = {
            UIStateEnum.MENU: self.handle_menu_click,
            UIStateEnum.SUBMENU: self.handle_submenu_click,
            UIStateEnum.END: self.handle_end_click,
            UIStateEnum.CHAMELEON: self.handle_chameleon_click,
            UIStateEnum.PARROT: self.handle_parrot_click
        }
        click_handlers.get(self.ui_state.current_state, lambda x, y: None)(x, y)

    def handle_menu_click(self, x, y):
        if 30 <= x <= 90:
            if 50 <= y <= 70:
                self.ui_state.change_state(UIStateEnum.SUBMENU)
            elif 90 <= y <= 110:
                self.reset_game()
                self.ui_state.change_state(UIStateEnum.GAME)

    def handle_submenu_click(self, x, y):
        if 30 <= x <= 90 and 90 <= y <= 110:
            self.ui_state.change_state(UIStateEnum.MENU)

    def handle_end_click(self, x, y):
        if 30 <= x <= 90:
            if 90 <= y <= 110:
                self.reset_game()
                self.ui_state.change_state(UIStateEnum.GAME)
            elif 120 <= y <= 140:
                self.ui_state.change_state(UIStateEnum.MENU)

    def handle_chameleon_click(self, x, y):
        start_x = (SCREEN_WIDTH - (5 * cst.ASSET_W_BIG + 4 * 4)) // 2
        y_pos = 60

        for i, card in enumerate(self.ui_state.table_cards):
            card_x = start_x + i * (cst.ASSET_W_BIG + 4)
            if card_x <= x <= card_x + cst.ASSET_W_BIG and y_pos <= y <= y_pos + cst.ASSET_H_BIG:
                self.perform_chameleon_action(card)
                self.ui_state.change_state(UIStateEnum.GAME)

                return

        self.ui_state.change_state(UIStateEnum.GAME)

    def handle_parrot_click(self, x, y):
        # Implement parrot click logic here
        pass

    def perform_chameleon_action(self, card):
        print(f"Chameleon action performed on card {card.card_value}")
        chameleon = self.ui_state.chameleon
        chameleon.action = ANIMAL_MAPPING[card.card_value].action
        self.play_card(self.ui_state.chameleon, self.ui_state.chameleon.x, self.ui_state.chameleon.y)
        self.ui_state.clear_chameleon()
        self.update_game_state()

    def update_game(self):
        if self.game_runner.game_state.finished:
            self.ui_state.change_state(UIStateEnum.END)
            return

        if self.game_runner.game_state.current_player != self.player_index:
            if self.ui_state.is_ai_delay_passed():
                self.execute_ai_move()
        else:
            self.handle_player_move()
            if self.ui_state.frame_count % 60 == 0:  # Log once per second
                logger.debug("Waiting for player move")

    def execute_ai_move(self):
        card = self.game_runner.get_played_card()
        if card is None:
            self.game_runner.game_state.mark_player_finished(self.game_runner.game_state.current_player)
        else:
            self.ui_state.start_animation()
            self.animate_card_move(card.value, card.player)

    def handle_player_move(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            x, y = pyxel.mouse_x, pyxel.mouse_y
            hand_start_x = (SCREEN_WIDTH - (
                    len(self.ui_state.hand_cards) * cst.ASSET_W_BIG + (len(self.ui_state.hand_cards) - 1) * 4)) // 2
            hand_y = SCREEN_HEIGHT - cst.ASSET_H_BIG - 5

            for i, card in enumerate(self.ui_state.hand_cards):
                card_x = hand_start_x + i * (cst.ASSET_W_BIG + 4)
                if card_x <= x <= card_x + cst.ASSET_W_BIG and hand_y <= y <= hand_y + cst.ASSET_H_BIG:
                    print(f"Player clicked on card {card.card_value} at ({card_x}, {hand_y})")
                    if card.card_value == ANIMALS.CHAMELEON:
                        self.ui_state.change_state(UIStateEnum.CHAMELEON)
                        self.ui_state.set_chameleon(card)
                    else:
                        self.play_card(card, card_x, hand_y)
                    break
    def animate_queue_changes(self, old_queue, new_queue):
        old_cards = {(card.value, card.player): card for card in old_queue}
        new_cards = {(card.value, card.player): card for card in new_queue}

        # Find cards that were removed (sent to thrash)
        removed_cards = [card for key, card in old_cards.items() if key not in new_cards]

        # Find cards that were moved within the queue
        moved_cards = [card for key, card in new_cards.items() if key in old_cards and old_queue.index(old_cards[key]) != new_queue.index(card)]

        # Animate removed cards
        for card in removed_cards:
            table_card = self.find_table_card(card)
            if table_card:
                table_card.start_move(table_card.x, table_card.y, THRASH_PILE_POS[0], THRASH_PILE_POS[1], self.on_card_to_thrash)
                self.ui_state.add_animating_card(table_card)

        # Animate moved cards
        queue_start_x = (SCREEN_WIDTH - (5 * cst.ASSET_W_BIG + 4 * 4)) // 2
        queue_y = 60
        for i, card in enumerate(new_queue):
            if card in moved_cards:
                table_card = self.find_table_card(card)
                if table_card:
                    new_x = queue_start_x + i * (cst.ASSET_W_BIG + 4)
                    table_card.start_move(table_card.x, table_card.y, new_x, queue_y, self.on_card_animation_complete)
                    self.ui_state.add_animating_card(table_card)

        self.ui_state.update_table_cards([self.find_table_card(card) for card in new_queue if self.find_table_card(card)])

    def find_table_card(self, card):
        for table_card in self.ui_state.table_cards:
            if table_card.card_value == card.value and table_card.owner == card.player:
                return table_card
        return None

    def play_card(self, card, card_x, card_y):
        self.ui_state.start_animation()
        target_x, target_y = self.get_table_target_position()
        card.start_move(card_x, card_y, target_x, target_y, self.on_card_animation_complete)
        self.ui_state.add_animating_card(card)
        self.ui_state.hand_cards.remove(card)

    def on_card_animation_complete(self, card, owner=None):
        print(f"Card {card.card_value} animation complete")
        if owner is None:
            owner = self.player_index
        self.game_runner.update_game_state(ANIMAL_MAPPING[card.card_value](owner))
        self.update_game_state()
        self.ui_state.stop_animation()
        self.ui_state.remove_animating_card(card)

    def animate_card_move(self, card_value, owner):
        start_x, start_y = self.player_start_positions[owner]
        target_x, target_y = self.get_table_target_position()
        card = TableCard(card_value, owner)
        card.start_move(start_x, start_y, target_x, target_y, self.on_card_animation_complete)
        self.ui_state.add_animating_card(card)

    def get_table_target_position(self):
        start_x = (SCREEN_WIDTH - (5 * cst.ASSET_W_BIG + 4 * 4)) // 2
        return start_x + len(self.ui_state.table_cards) * (cst.ASSET_W_BIG + 4), 60

    def update_animations(self):
        for card in self.ui_state.animating_cards:
            card.update_position()
        self.ui_state.animating_cards = [card for card in self.ui_state.animating_cards if card.is_moving]
        if not self.ui_state.animating_cards:
            self.ui_state.stop_animation()

    def draw(self):
        self.drawing_handler.draw(self.ui_state)

        # Draw bar and thrash piles
        pyxel.rect(BAR_PILE_POS[0], BAR_PILE_POS[1], ASSET_W_BIG, ASSET_H_BIG, pyxel.COLOR_RED)
        pyxel.text(BAR_PILE_POS[0] + 2, BAR_PILE_POS[1] + 2, str(self.bar_pile_count), pyxel.COLOR_WHITE)

        pyxel.rect(THRASH_PILE_POS[0], THRASH_PILE_POS[1], ASSET_W_BIG, ASSET_H_BIG, pyxel.COLOR_LIGHT_BLUE)
        pyxel.text(THRASH_PILE_POS[0] + 2, THRASH_PILE_POS[1] + 2, str(self.thrash_pile_count), pyxel.COLOR_WHITE)




# Run the application
if __name__ == "__main__":
    App()
