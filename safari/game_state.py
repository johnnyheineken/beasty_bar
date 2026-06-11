import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Type, Optional
from safari.stacks.queue import Queue
from safari.players.strategies import Player, Max, Strategy  # Import all strategy classes
from safari.cards.base import Card, ANIMALS
from safari.cards.new_beasts_deck import Vulture
from safari.stacks.shuffle import ANIMAL_MAPPING, CARD_CLASSES

# Create a mapping of strategy names to strategy classes
STRATEGY_MAP: Dict[str, Type[Strategy]] = {
    'Max': Max,
    'Player': Player,
    # Add other strategy classes here
    # 'SomeOtherStrategy': SomeOtherStrategy,
}

@dataclass
class QueueEvaluationResult:
    to_winners: List[Card] = field(default_factory=list)
    to_losers: List[Card] = field(default_factory=list)
    new_queue: Queue = field(default_factory=Queue)

@dataclass
class GameState:
    cards_in_bar: List[Card] = field(default_factory=list)
    cards_in_thrash: List[Card] = field(default_factory=list)
    queue: Queue = field(default_factory=Queue)
    old_queue: Queue = field(default_factory=Queue)
    players: List[int] = field(default_factory=list)
    current_player: int = 0
    n_players: int = 0
    turn_number: int = 0
    table: Dict[int, Dict] = field(default_factory=dict)
    finished: bool = False
    results: Dict[int, int] = field(default_factory=dict)
    last_queue_evaluation: Optional[QueueEvaluationResult] = None
    # 'count' = base game (most guests, ties broken by lower total value);
    # 'points' = New Beasts in Town / mixed (sum of card points, ties stand)
    scoring: str = 'count'

    def set_queue_evaluation_result(self, to_winners, to_losers, new_queue):
        self.last_queue_evaluation = QueueEvaluationResult(
            to_winners=to_winners,
            to_losers=to_losers,
            new_queue=new_queue
        )

    def to_json(self):
        def serialize_card(card):
            return {
                "animal": int(card.value),
                "kind": card.__class__.__name__,
                "player": card.player
            }

        data = asdict(self)
        data['cards_in_bar'] = [serialize_card(card) for card in self.cards_in_bar]
        data['cards_in_thrash'] = [serialize_card(card) for card in self.cards_in_thrash]
        data['queue'] = [serialize_card(card) for card in self.queue]
        data['old_queue'] = [serialize_card(card) for card in self.old_queue]

        serialized_table = {}
        for player, info in data['table'].items():
            serialized_table[str(player)] = {
                'hand': [serialize_card(card) for card in info['hand']],
                'deck': [serialize_card(card) for card in info['deck']],
                'thrown': [serialize_card(card) for card in info['thrown']],
                'strategy': info['strategy'].__class__.__name__,
                'finished': info['finished']
            }
        data['table'] = serialized_table

        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)

        def deserialize_card(card_data):
            if 'kind' in card_data:
                return CARD_CLASSES[card_data['kind']](card_data['player'])
            return ANIMAL_MAPPING[ANIMALS(card_data['animal'])](card_data['player'])

        data['cards_in_bar'] = [deserialize_card(card) for card in data['cards_in_bar']]
        data['cards_in_thrash'] = [deserialize_card(card) for card in data['cards_in_thrash']]
        data['queue'] = Queue([deserialize_card(card) for card in data['queue']])
        data['old_queue'] = Queue([deserialize_card(card) for card in data['old_queue']])

        deserialized_table = {}
        for player, info in data['table'].items():
            strategy_class = STRATEGY_MAP.get(info['strategy'])
            if not strategy_class:
                raise ValueError(f"Unknown strategy: {info['strategy']}")

            deserialized_table[int(player)] = {
                'hand': [deserialize_card(card) for card in info['hand']],
                'deck': [deserialize_card(card) for card in info['deck']],
                'thrown': [deserialize_card(card) for card in info['thrown']],
                'strategy': strategy_class(),
                'finished': info['finished']
            }
        data['table'] = deserialized_table

        return cls(**data)

    def update_queue(self, card):
        self.old_queue = self.queue.copy()
        if isinstance(card, Vulture):
            self._play_vulture(card)
            return
        new_queue, dropped = self.queue.resolve(card)
        self.queue = new_queue
        self.cards_in_thrash.extend(dropped)

    def _play_vulture(self, vulture):
        """The vulture never joins the line. It revives the top card of
        THAT'S IT, which re-joins the line and carries out its action;
        the vulture itself lands on THAT'S IT at the end of the turn.
        If it revives another vulture, both immediately enter the bar."""
        trash = self.cards_in_thrash
        if trash and isinstance(trash[-1], Vulture):
            other = trash.pop()
            self.cards_in_bar.extend([other, vulture])
            new_queue, dropped = self.queue.run_recurring()
            self.queue = new_queue
            trash.extend(dropped)
            return
        if trash:
            revived = trash.pop()
            for attr, value in (vulture.revive_params or {}).items():
                setattr(revived, attr, value)
            new_queue, dropped = self.queue.resolve(revived)
            self.queue = new_queue
            trash.extend(dropped)
        else:
            new_queue, dropped = self.queue.run_recurring()
            self.queue = new_queue
            trash.extend(dropped)
        trash.append(vulture)

    def add_winner(self, player):
        self.cards_in_bar.append(player)

    def add_loser(self, player):
        self.cards_in_thrash.append(player)

    def next_player(self):
        self.current_player = (self.current_player + 1) % self.n_players

    def increment_turn(self):
        self.turn_number += 1

    def is_game_finished(self):
        return all(self.table[p]['finished'] for p in self.table)

    def update_results(self):
        self.results = {p: 0 for p in self.players}
        for winner in self.cards_in_bar:
            gain = winner.point_value if self.scoring == 'points' else 1
            self.results[winner.player] = self.results.get(winner.player, 0) + gain

    def get_winners(self):
        """Base game ('count'): most guests in the bar wins, ties broken by
        the LOWER sum of card values. New Beasts/mixed ('points'): most
        points wins, ties stand. Several players can tie either way."""
        if not self.results:
            return []
        best = max(self.results.values())
        tied = [p for p, n in self.results.items() if n == best]
        if len(tied) == 1 or self.scoring == 'points':
            return tied
        value_sums = {
            p: sum(int(c.value) for c in self.cards_in_bar if c.player == p)
            for p in tied
        }
        lowest = min(value_sums.values())
        return [p for p in tied if value_sums[p] == lowest]

    def get_player_hand(self, player):
        return self.table[player]['hand']

    def remove_card_from_hand(self, player, card):
        hand = self.table[player]['hand']
        hand.remove(card)

    def draw_card(self, player):
        deck = self.table[player]['deck']
        hand = self.table[player]['hand']
        if deck:
            hand.append(deck.pop(0))

    def mark_player_finished(self, player):
        self.table[player]['finished'] = True

    def to_dict(self):
        return {
            'cards_in_bar': self.cards_in_bar,
            'cards_in_thrash': self.cards_in_thrash,
            'queue': self.queue,
            'old_queue': self.old_queue,
            'players': self.players,
            'current_player': self.current_player,
            'n_players': self.n_players,
            'turn_number': self.turn_number,
            'table': self.table,
            'finished': self.finished,
            'results': self.results
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)