import random
import pyxel
from cards.base import ANIMALS

from stacks.queue import Queue
from stacks.shuffle import init, ANIMAL_MAPPING
from players.strategies import Max, Player
from safari import GameRunner

SCREEN_WIDTH = 120
SCREEN_HEIGHT = 160

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

PLAYER_COLORS = [pyxel.COLOR_RED, pyxel.COLOR_GREEN, pyxel.COLOR_YELLOW, pyxel.COLOR_NAVY]

class App:
    def __init__(self):
        strategies = {0: Max, 1: Max, 2: Max, 3: Max}
        self.p = random.choice(list(strategies.keys()))
        strategies[self.p] = Player
        table = init(strategies=strategies)
        self.gr = GameRunner(table)
        self.table_cards = [i.value for i in self.gr.game_state['queue']]  # Start with an empty list for table cards
        self.hand_cards = [i.value for i in self.gr.game_state['table'][self.p]['hand']]  # Example card IDs in hand
        self.card_owners = []  # Track which player played each card
        self.state = "menu"

        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Hello Pyxel")
        pyxel.mouse(True)
        pyxel.load("assets.pyxres")
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            x = pyxel.mouse_x
            y = pyxel.mouse_y

            if self.state == "menu":
                if 30 <= x <= 90 and 50 <= y <= 70:  # First button coordinates
                    self.state = "submenu"
                elif 30 <= x <= 90 and 90 <= y <= 110:  # Second button coordinates
                    self.state = "game"
            elif self.state == "submenu":
                if 30 <= x <= 90 and 90 <= y <= 110:  # Back button coordinates
                    self.state = "menu"

        if self.state == "game":
            self.update_game()

    def single_player_game_state_update(self, card):
        self.gr.update_game_state(card)

    def update_game(self):
        if self.gr.game_state['current_player'] != self.p:

            card = self.gr.get_played_card()
            self.gr.play_card(card)
            self.gr.draw_card()
            self.gr.update_game_state(card)
            # Add background and append to table cards
            self.table_cards = [i.value for i in self.gr.game_state['queue']]
            self.card_owners = [i.player for i in self.gr.game_state['queue']]
            self.hand_cards = [i.value for i in self.gr.game_state['table'][self.p]['hand']]
        else:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                x = pyxel.mouse_x
                y = pyxel.mouse_y

                # Check if a hand card is clicked
                hand_start_x = (120 - (len(self.hand_cards) * 16 + (len(self.hand_cards) - 1) * 4)) // 2
                hand_y = 140  # Fixed y position for hand cards

                for i, card in enumerate(self.hand_cards):
                    card_x = hand_start_x + i * (16 + 4)
                    if card_x <= x <= card_x + 16 and hand_y <= y <= hand_y + 16:
                        # Add the clicked card to the table cards if there is space
                        self.gr.play_card(ANIMAL_MAPPING[card])
                        self.gr.draw_card()
                        self.gr.update_game_state(ANIMAL_MAPPING[card](self.p))

                        self.table_cards = [i.value for i in self.gr.game_state['queue']]
                        self.card_owners = [i.player for i in self.gr.game_state['queue']]
                        self.hand_cards = [i.value for i in self.gr.game_state['table'][self.p]['hand']]


                        break

    def draw(self):
        pyxel.cls(0)
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "submenu":
            self.draw_submenu()
        elif self.state == "game":
            self.draw_game()

    def draw_menu(self):
        pyxel.text(35, 30, "Main Menu", pyxel.COLOR_WHITE)
        pyxel.rect(30, 50, 60, 20, pyxel.COLOR_RED)
        pyxel.text(45, 57, "Submenu", pyxel.COLOR_WHITE)
        pyxel.rect(30, 90, 60, 20, pyxel.COLOR_RED)
        pyxel.text(40, 97, "Start Game", pyxel.COLOR_WHITE)

    def draw_submenu(self):
        pyxel.text(40, 30, "Submenu", pyxel.COLOR_WHITE)
        pyxel.rect(30, 90, 60, 20, pyxel.COLOR_RED)
        pyxel.text(50, 97, "Back", pyxel.COLOR_WHITE)

    def draw_game(self):
        pyxel.cls(0)
        self.draw_background()
        self.draw_hand_cards()
        self.draw_table_card_slots()
        self.draw_table_cards()

    def draw_background(self):
        pyxel.rect(0, 0, 120, 160, pyxel.COLOR_DARK_BLUE)  # Dark blue background

    def draw_table_card_slots(self):
        start_x = (120 - (5 * 16 + 4 * 4)) // 2
        y = 60  # Fixed y position for table cards

        for i in range(5):
            x = start_x + i * (16 + 4)
            pyxel.rectb(x, y, 16, 16, pyxel.COLOR_WHITE)  # Draw rectangle slots

    def draw_table_cards(self):
        start_x = (120 - (5 * 16 + 4 * 4)) // 2
        y = 60  # Fixed y position for table cards

        for i, card in enumerate(self.table_cards):
            x = start_x + i * (16 + 4)
            owner_color = PLAYER_COLORS[self.card_owners[i]]
            pyxel.rect(x, y, 16, 16, owner_color)  # Draw the player's color background
            pyxel.blt(x, y, 0, MAPPING[card][0], MAPPING[card][1], 16, 16, 11)  # Draw card sprite from the resource file

    def draw_hand_cards(self):
        start_x = (120 - (len(self.hand_cards) * 16 + (len(self.hand_cards) - 1) * 4)) // 2
        y = 140  # Fixed y position for hand cards
        for i, card in enumerate(self.hand_cards):
            x = start_x + i * (16 + 4)
            pyxel.blt(x, y, 0, MAPPING[card][0], MAPPING[card][1], 16, 16, 11)


# Run the application
App()
