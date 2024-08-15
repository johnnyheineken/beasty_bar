import random
from safari.game_state import GameState
from safari.utils.helpers import create_logger
from safari.stacks.shuffle import init, ANIMAL_MAPPING
from safari.players.strategies import Max, Player

BAR_QUEUE_LENGTH = 5


class GameRunner:
    def __init__(self, table):
        self.logger = create_logger("Safari", level=20)
        self.game_log = []
        self.game_state = GameState(
            players=list(table.keys()),
            n_players=len(table),
            table=table
        )

    def run(self):
        self.logger.info("Starting new game")
        while not self.game_state.finished:
            self.play_turn()
            self.game_log.append(self.game_state.to_dict())

        self.log_results()
        return self.game_log

    def play_turn(self):
        self.logger.info(f"Turn {self.game_state.turn_number + 1} - Player {self.game_state.current_player}'s turn")
        self.logger.debug(f"Current queue: {[str(card) for card in self.game_state.queue]}")

        card = self.get_played_card()
        self.logger.info(f"Player {self.game_state.current_player} played: {card}")

        old_queue = self.game_state.queue.copy()
        self.update_game_state(card)

        self.log_queue_changes(old_queue, self.game_state.queue)
        self.check_game_end()

    def get_played_card(self):
        player = self.game_state.current_player
        cards = self.game_state.table[player]
        hand = cards["hand"]

        self.logger.debug(f"Player {player}'s hand: {[str(card) for card in hand]}")

        if not hand:
            self.logger.warning(f"Player {player}'s hand is empty!")
            return None

        if isinstance(cards['strategy'], Player):
            return self.get_human_player_card(hand)
        else:
            return cards["strategy"].strategy(hand)

    def update_game_state(self, card):
        self.logger.debug(f"Updating game state after playing {card}")
        self.game_state.update_queue(card)
        self.evaluate_queue()
        self.game_state.remove_card_from_hand(self.game_state.current_player, card)
        self.game_state.draw_card(self.game_state.current_player)
        self.check_player_finished()
        self.check_game_end()
        self.game_state.increment_turn()
        self.game_state.next_player()

    def evaluate_queue(self):
        if len(self.game_state.queue) == BAR_QUEUE_LENGTH:
            to_winners = self.game_state.queue[:2]
            to_losers = [self.game_state.queue[-1]]

            self.log_queue_evaluation(to_winners, to_losers)
            self.game_state.queue = self.game_state.queue[2:BAR_QUEUE_LENGTH - 1]
            self.game_state.cards_in_bar.extend(to_winners)
            self.game_state.cards_in_thrash.extend(to_losers)

            # Set the queue evaluation result in game state
            self.game_state.set_queue_evaluation_result(to_winners, to_losers, self.game_state.queue)
        else:
            self.game_state.last_queue_evaluation = None

    def log_queue_evaluation(self, winners, losers):
        self.logger.info(
            f"{'#' * 30}\n"
            f"EVALUATING QUEUE\n"
            f"Current queue: {[str(card) for card in self.game_state.queue]}\n"
            f"🏆 Winners: {', '.join(str(w) for w in winners)}\n"
            f"💩 Losers: {', '.join(str(l) for l in losers)}\n"
            f"New queue: {[str(card) for card in self.game_state.queue[2:BAR_QUEUE_LENGTH - 1]]}\n"
            f"{'#' * 30}"
        )

    def log_queue_changes(self, old_queue, new_queue):
        self.logger.info(f"Queue change:")
        self.logger.info(f"  Old queue: {[str(card) for card in old_queue]}")
        self.logger.info(f"  New queue: {[str(card) for card in new_queue]}")

        if len(old_queue) != len(new_queue):
            self.logger.info(f"  Queue length changed from {len(old_queue)} to {len(new_queue)}")

        for i, (old_card, new_card) in enumerate(zip(old_queue, new_queue)):
            if old_card != new_card:
                self.logger.info(f"  Position {i}: {old_card} -> {new_card}")

    def check_player_finished(self):
        player = self.game_state.current_player
        if not self.game_state.get_player_hand(player):
            self.logger.info(f"Player {player} has finished their cards")
            self.game_state.mark_player_finished(player)

    def check_game_end(self):
        if self.game_state.is_game_finished():
            self.game_state.finished = True
            self.game_state.update_results()
            self.logger.info("Game has ended")

    def log_results(self):
        self.logger.info("Final Game Results:")
        for player, points in self.game_state.results.items():
            self.logger.info(f"  Player {player}: {points} points")
        winner = max(self.game_state.results, key=self.game_state.results.get)
        self.logger.info(f"Player {winner} wins!")


def single_player():
    strategies = {i: Max for i in range(4)}
    # human_player = random.choice(list(strategies.keys()))
    # strategies[human_player] = Player
    table = init(strategies=strategies)
    gr = GameRunner(table)
    gr.run()


if __name__ == "__main__":
    single_player()