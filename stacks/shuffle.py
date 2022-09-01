import random

from cards.first_game_deck import Chameleon, Croc, Gazelle, Hippo, Kangaroo, Lion, Monkey, Parrot, Seal, Skunk, Snake, Zebra


def init(n_players=2):
    all_cards = [Skunk, Parrot, Kangaroo, Monkey, Chameleon, Seal, Zebra, Gazelle, Snake, Croc, Hippo, Lion]
    players = {}
    for player in range(n_players):
        personal_cards = [card(player) for card in all_cards]
        random.shuffle(personal_cards)
        players[player] = {
            'hand': [personal_cards.pop() for _ in range(4)],
            'deck': [personal_cards.pop() for _ in range(6)],
            'thrown': personal_cards
        }
    return players


def assign_strategy(players, strategies):
    n_players = len(players)
    chosen_strategies = [random.randint(0, len(strategies) - 1) for _ in range(n_players)]
    print(chosen_strategies)
    chosen_strategies = [list(strategies.keys())[idx] for idx in chosen_strategies]
    for player, cards in players.items():
        description = chosen_strategies[player]
        cards['strategy'] = {'fn': strategies[description], 'description': description}
        players[player] = cards
    return players
