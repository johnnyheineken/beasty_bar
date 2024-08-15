from safari.cards.base import Card


class Queue(list):
    def __init__(self, *args):
        super().__init__(*args)

    def __getitem__(self, key):
        result = super().__getitem__(key)
        if isinstance(key, slice):
            return Queue(result)
        return result

    def __setitem__(self, key, value):
        if isinstance(value, Queue):
            super().__setitem__(key, list(value))
        else:
            super().__setitem__(key, value)

    def __repr__(self):
        return f"Queue({super().__repr__()})"

    def __add__(self, other):
        return Queue(super().__add__(other))

    def __radd__(self, other):
        return Queue(other) + self

    def copy(self):
        return Queue(self)

    @property
    def values(self):
        return [i.value for i in self]

    def find_indices_of(self, card):
        return [i for i, x in enumerate(self.values) if x == card]

    def drop_card_values(self, card):
        return [self.pop(i) for i in reversed(self.find_indices_of(card))]

    def resolve(self, added_card: Card):
        all_dropped = []
        if hasattr(added_card, 'resolve_action'):
            added_card.resolve_action(self)
        queue, dropped = added_card.action(self)
        all_dropped += dropped
        for card in queue:
            if card == added_card:
                continue
            if card.repeating_action:
                queue, dropped = card.action(queue)
                all_dropped += dropped

        return queue, all_dropped