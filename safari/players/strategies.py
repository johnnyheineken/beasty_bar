def strategy_max(cards):

    played = cards[cards.index(max(cards, key=lambda x: x.value))]

    return played


def strategy_first(cards):
    return cards.pop(0)


def strategy_min(cards):
    return cards.pop(cards.index(min(cards, key=lambda x: x.value)))


class Strategy:
    def strategy(cards):
        raise NotImplementedError
    def chameleon():
        return None
    def parrot():
        return None

class Max(Strategy):
    def __str__(self):
        return 'max'
    def strategy(self, cards):
        return strategy_max(cards)

class Player(Strategy):
    def __str__(self):
        return 'player'
    def strategy(self, cards):
        return None