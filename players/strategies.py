def strategy_max(cards):
    return cards.pop(cards.index(max(cards, key=lambda x: x.value)))


def strategy_first(cards):
    return cards.pop(0)


def strategy_min(cards):
    return cards.pop(cards.index(min(cards, key=lambda x: x.value)))