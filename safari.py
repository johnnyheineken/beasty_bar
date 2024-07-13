import pprint
import random
from textwrap import dedent

from utils.helpers import create_logger
from stacks.shuffle import init, ANIMAL_MAPPING
from stacks.queue import Queue
from players.strategies import Max, Player

BAR_QUEUE_LENGTH = 5


class GameRunner:
    def __init__(self, table):
        self.logger = create_logger("Safari", level=20)
        self.game_log = []
        players = list(table.keys())
        self.game_state = {
            'winners': [],
            'losers': [],
            'queue': Queue(),
            'players': players,
            'current_player': 0,
            'n_players': len(players),
            'turn_number': 0,
            'table': table,
        }

    def update_game_state(self, card):

        print('\n\n' + '#' * 40)
        print(f'{self.game_state['current_player']=}')
        print(f'{self.game_state['players']=}')
        print('#' * 40)

        queue, dropped = self.game_state['queue'].resolve(card)
        self.game_state['queue'] = queue
        self.game_state['losers'] += dropped

        self.game_state['queue'] = self.evaluate_queue(queue)

        print(f'{self.game_state['queue']=}')

        self.game_state['turn_number'] += 1
        self.game_log += [self.game_state.copy()]
        self.player_carousel()

    def run(self, game_state=None):
        if game_state:
            self.game_state = game_state

        while True:
            player = self.game_state['current_player']

            chosen_card = self.get_played_card()
            if chosen_card is None:
                break

            self.update_game_state(chosen_card)

        results = {}
        for i in self.game_state['winners']:
            results[i.player] = results.get(i.player, 0) + 1
        self.logger.info(results)
        self.logger.info(f"Player {max(results, key=results.get)} wins.")
        return self.game_log

    def get_played_card(self):
        player = self.game_state['current_player']
        cards = self.game_state['table'][player]
        # print(cards)
        hand = cards["hand"]
        print(f'{hand=}')
        print(f'{type(cards['strategy'])=}')
        if isinstance(cards['strategy'], Player):

            print(self.game_state['queue'])
            print('Your hand')
            print([i.__str__() for i in cards['hand']])
            played, hand = self.get_players_card(player, hand)

        else:
            played, hand = cards["strategy"].strategy(hand)

        self.game_state['table'][player]['hand'] = hand

        return played

    def draw_card(self):
        player = self.game_state['current_player']
        deck = self.game_state['table'][player]['deck']
        hand = self.game_state['table'][player]['hand']
        if deck:
            self.game_state['table'][player]['hand'] = hand + [deck.pop(0)]

    def play_card(self, card):
        player = self.game_state['current_player']

        hand = self.game_state['table'][player]['hand']
        print(hand)
        hand.pop(hand.index(card(player)))
        self.game_state['table'][player]['hand'] = hand

    def get_players_card(self, player, hand):
        tries = 0
        while True:
            played_card = input('Your card:')
            try:
                played_card = int(played_card)
            except:
                print('wrong')
                tries += 1
                continue
            card = ANIMAL_MAPPING[played_card](player)
            print(card)
            if card not in hand:
                print('not in your hand')
                tries += 1
                if tries < 2:
                    continue
                raise ValueError('are you stupid?')
            break

        card = hand.pop(hand.index(card))
        return card, hand

    def player_carousel(self, ):
        players = self.game_state['players']
        player = players.pop(0)
        players.append(player)
        self.game_state['players'] = players
        self.game_state['current_player'] = self.game_state['players'][0]

    def evaluate_queue(self, queue):
        if len(queue) == BAR_QUEUE_LENGTH:
            to_winners = queue[:2]
            to_losers = [queue[-1]]
            self.logger.info(
                f"""
                {'#' * 30}
                {'EVALUATING'}
                {queue}
                🏆 {', '.join([str(i) for i in to_winners])}
                💩 {', '.join([str(i) for i in to_losers])}
                new queue: {Queue(queue[2:BAR_QUEUE_LENGTH - 1])}
                {'#' * 30}
                """
            )

            queue = Queue(queue[2: BAR_QUEUE_LENGTH - 1])
            self.game_state['losers'] += to_losers
            self.game_state['winners'] = to_winners
        return queue


def single_player():
    strategies = {0: Max, 1: Max, 2: Max, 3: Max}
    p = random.choice(list(strategies.keys()))
    strategies[p] = Player
    table = init(strategies=strategies)
    gr = GameRunner(table)
    a = pprint.PrettyPrinter(indent=4)
    while True:
        card = gr.get_played_card()
        gr.draw_card()
        gr.update_game_state(card)
        a.pprint(gr.game_log[-1])


def main():

    strategies = {0: Max, 1: Max, 2: Max, 3: Max}
    table = init(strategies=strategies)
    gr = GameRunner(table)
    game_log = gr.run()


if __name__ == "__main__":
    single_player()
