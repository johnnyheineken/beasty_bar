from textwrap import dedent

from helpers import create_logger
from shuffle import assign_strategy, init
from stacks import Queue
from strategies import strategy_first, strategy_max, strategy_min


class GameRunner:
    def __init__(self):
        self.logger = create_logger('Safari', level=20)
        self.game_log = {}

    def run(self, table, queue_length=5):
        total_game_length = self.get_game_length(table)
        queue = Queue()
        player_order = list(table.keys())
        self.game_log['start'] = {'game_length': total_game_length,
                                  'players': len(player_order),
                                  'strategies': [player["strategy"]["description"] for player in table.values()]}

        winners = []
        losers = []

        for turn_number in range(total_game_length):
            player = self.player_carousel(player_order)
            cards, chosen_card = self.get_played_card(player, table)
            queue_before = queue.copy()
            queue, dropped = queue.resolve(chosen_card)

            self.logger.info(dedent(f'''
            Turn #{turn_number}
            Queue before: {', '.join([str(i) for i in queue_before])}
            Added card: {chosen_card}
            Queue now: {', '.join([str(i) for i in queue])}
            {'' if dropped else dropped}
            \n
            '''))
            self.game_log[turn_number] = {'queue_before': repr(queue_before), 'added': repr(chosen_card),
                                          'queue_now': repr(queue)}
            # self.turn_info(dropped, hand, played, queue)

            losers += dropped
            if deck := cards['deck']:
                taken = [deck.pop(0)]
                cards['hand'] += taken


            losers, queue, winners = self.evaluate_queue(losers, queue, queue_length, winners)
        self.logger.debug(f"{winners=}")
        self.logger.debug(f"{losers=}")
        results = {}
        for i in winners:
            results[i.player] = results.get(i.player, 0) + 1
        self.logger.info(results)
        self.logger.info(f"Player {max(results, key=results.get)} wins.")
        return self.game_log

    def get_game_length(self, table):
        total_game_length = sum([len(x['hand']) + len(x['deck']) for x in table.values()])
        return total_game_length

    def get_played_card(self, player, table):
        cards = table[player]
        hand = cards['hand']
        hand_for_log = hand.copy()
        played = cards['strategy']['fn'](hand)

        self.logger.debug(dedent(f'''
        🧍 Player {player}
        🤲 Cards in hand: {', '.join([str(x) for x in hand_for_log])}
        Applies strategy "{cards['strategy']['description']}"
        Chooses {played}
        '''))
        return cards, played

    def player_carousel(self, player_order):
        player = player_order.pop(0)
        player_order.append(player)
        return player


    def evaluate_queue(self, losers, queue, queue_length, winners):
        if len(queue) == queue_length:
            to_winners = queue[:2]
            to_losers = [queue[-1]]
            self.logger.info(f"""
                {'#' * 30}
                {'EVALUATING'}
                {queue}
                🏆 {', '.join([str(i) for i in to_winners])}
                💩 {', '.join([str(i) for i in to_losers])}
                new queue: {Queue(queue[2:queue_length-1])}
                {'#' * 30}
                """
                             )
            
            winners += to_winners
            losers += to_losers
            
            queue = Queue(queue[2:queue_length-1])
        return losers, queue, winners


def main():
    strategies = {'max': strategy_max, 'first': strategy_first, 'min': strategy_min}
    table = init(4)
    table = assign_strategy(table, strategies)
    gr = GameRunner()
    game_log = gr.run(table)
    print(game_log)


if __name__ == '__main__':
    main()
