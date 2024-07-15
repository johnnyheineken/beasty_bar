import random
import pyxel
import time

from safari.frontend.frontend import TableCard
from safari.frontend.constants import PLAYER_COLORS
from safari.stacks.shuffle import init, ANIMAL_MAPPING
from safari.players.strategies import Max, Player
from safari.safari import GameRunner

SCREEN_WIDTH = 120
SCREEN_HEIGHT = 160
AI_DELAY = 0.5  # Half a second delay for AI players

PLAYER_START_POSITIONS = {
    0: (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 16),  # Bottom
    1: (0, SCREEN_HEIGHT // 2),  # Left
    2: (SCREEN_WIDTH // 2, 0),  # Top
    3: (SCREEN_WIDTH - 16, SCREEN_HEIGHT // 2),  # Right
}

class App:
    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Safari Bar")
        pyxel.mouse(True)
        pyxel.load("assets.pyxres")
        self.reset_game()
        pyxel.run(self.update, self.draw)

    def reset_game(self):
        self.setup_players()
        self.setup_game()
        self.update_game_state()
        self.state = "menu"
        self.last_ai_action_time = time.time()
        self.animation_in_progress = False

    def setup_players(self):
        self.strategies = {0: Max, 1: Max, 2: Max, 3: Max}
        self.player_index = random.choice(list(self.strategies.keys()))
        self.strategies[self.player_index] = Player

    def setup_game(self):
        table = init(strategies=self.strategies)
        self.game_runner = GameRunner(table)
        self.table_cards = []
        self.hand_cards = []
        self.animating_cards = []

    def update_game_state(self):
        self.table_cards = [TableCard(i.value, i.player) for i in self.game_runner.game_state['queue']]
        self.hand_cards = [TableCard(i.value, self.player_index) for i in
                           self.game_runner.game_state['table'][self.player_index]['hand']]
        self.finished = self.check_if_game_finished()
        print("Game state updated")

    def check_if_game_finished(self):
        return self.game_runner.game_state['finished']

    def update(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            self.handle_mouse_click()

        if self.state == "game" and not self.animation_in_progress:
            self.update_game()

        self.update_animations()

    def handle_mouse_click(self):
        x, y = pyxel.mouse_x, pyxel.mouse_y
        click_handlers = {
            "menu": self.handle_menu_click,
            "submenu": self.handle_submenu_click,
            "end": self.handle_end_click
        }
        click_handlers.get(self.state, lambda x, y: None)(x, y)

    def handle_menu_click(self, x, y):
        if 30 <= x <= 90:
            if 50 <= y <= 70:
                self.state = "submenu"
            elif 90 <= y <= 110:
                self.state = "game"

    def handle_submenu_click(self, x, y):
        if 30 <= x <= 90 and 90 <= y <= 110:
            self.state = "menu"

    def handle_end_click(self, x, y):
        if 30 <= x <= 90:
            if 90 <= y <= 110:
                self.reset_game()
                self.state = "game"
            elif 120 <= y <= 140:
                self.state = "menu"

    def update_game(self):
        if self.finished:
            self.state = "end"
            return

        if self.game_runner.game_state['current_player'] != self.player_index:
            if time.time() - self.last_ai_action_time >= AI_DELAY:
                self.execute_ai_move()
        else:
            self.handle_player_move()

    def execute_ai_move(self):
        card = self.game_runner.get_played_card()
        self.animation_in_progress = True
        self.animate_card_move(card.value, card.player)

    def handle_player_move(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            x, y = pyxel.mouse_x, pyxel.mouse_y
            hand_start_x = (SCREEN_WIDTH - (len(self.hand_cards) * 16 + (len(self.hand_cards) - 1) * 4)) // 2
            hand_y = 140

            for i, card in enumerate(self.hand_cards):
                card_x = hand_start_x + i * (16 + 4)
                if card_x <= x <= card_x + 16 and hand_y <= y <= hand_y + 16:
                    print(f"Player clicked on card {card.card_value} at ({card_x}, {hand_y})")
                    self.play_card(card, card_x, hand_y, i)
                    break

    def play_card(self, card, card_x, card_y, index):
        self.animation_in_progress = True
        target_x, target_y = self.get_table_target_position()
        card.start_move(card_x, card_y, target_x, target_y, self.on_card_animation_complete)
        self.animating_cards.append(card)
        self.hand_cards.pop(index)

    def on_card_animation_complete(self, card, owner):
        print(f"Card {card.card_value} animation complete")
        self.game_runner.update_game_state(ANIMAL_MAPPING[card.card_value](owner))
        self.update_game_state()
        self.animation_in_progress = False

    def animate_card_move(self, card_value, owner):
        start_x, start_y = PLAYER_START_POSITIONS[owner]
        target_x, target_y = self.get_table_target_position()
        card = TableCard(card_value, owner)
        card.start_move(start_x, start_y, target_x, target_y, self.on_card_animation_complete)
        self.animating_cards.append(card)

    def get_table_target_position(self):
        start_x = (SCREEN_WIDTH - (5 * 16 + 4 * 4)) // 2
        return start_x + len(self.table_cards) * (16 + 4), 60

    def update_animations(self):
        for card in self.animating_cards:
            card.update_position()
        self.animating_cards = [card for card in self.animating_cards if card.is_moving]
        if not self.animating_cards:
            self.animation_in_progress = False

    def draw(self):
        pyxel.cls(0)
        draw_handlers = {
            "menu": self.draw_menu,
            "submenu": self.draw_submenu,
            "game": self.draw_game,
            "end": self.draw_end
        }
        draw_handlers.get(self.state, lambda: None)()

        for card in self.animating_cards:
            card.draw_small()

    def draw_menu(self):
        self.draw_text_centered(35, 30, "Main Menu", pyxel.COLOR_WHITE)
        self.draw_button(30, 50, "Submenu")
        self.draw_button(30, 90, "Start Game")

    def draw_submenu(self):
        self.draw_text_centered(40, 30, "Submenu", pyxel.COLOR_WHITE)
        self.draw_button(30, 90, "Back")

    def draw_game(self):
        self.draw_background()
        self.draw_hand_cards()
        self.draw_table_card_slots()
        self.draw_table_cards()

    def draw_background(self):
        pyxel.rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, pyxel.COLOR_DARK_BLUE)

    def draw_table_card_slots(self):
        self.draw_card_slots((SCREEN_WIDTH - (5 * 16 + 4 * 4)) // 2, 60, 5)

    def draw_table_cards(self):
        start_x = (SCREEN_WIDTH - (5 * 16 + 4 * 4)) // 2
        y = 60
        for i, card in enumerate(self.table_cards):
            card_x = start_x + i * (16 + 4)
            card.draw_small(card_x, y)

    def draw_hand_cards(self):
        hand_start_x = (SCREEN_WIDTH - (len(self.hand_cards) * 16 + (len(self.hand_cards) - 1) * 4)) // 2
        hand_y = 140
        for i, card in enumerate(self.hand_cards):
            card.draw_small(hand_start_x + i * (16 + 4), hand_y)

    def draw_end(self):
        pyxel.cls(0)
        results = self.game_runner.game_state['results']
        self.draw_text_centered(35, 30, "Game Over", pyxel.COLOR_WHITE)
        for i, (player, points) in enumerate(results.items()):
            pyxel.text(20, 50 + i * 10, f"Player {player}: {points} points", PLAYER_COLORS[player])
        self.draw_button(30, 90, "Play Again")
        self.draw_button(30, 120, "Menu")

    def draw_text_centered(self, x, y, text, color):
        pyxel.text(x, y, text, color)

    def draw_button(self, x, y, text):
        pyxel.rect(x, y, 60, 20, pyxel.COLOR_RED)
        pyxel.text(x + 10, y + 7, text, pyxel.COLOR_WHITE)

    def draw_card_slots(self, start_x, y, count):
        for i in range(count):
            x = start_x + i * (16 + 4)
            pyxel.rectb(x, y, 16, 16, pyxel.COLOR_WHITE)


# Run the application
App()
