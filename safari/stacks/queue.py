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

    def resolve(self, added_card: Card, events=None):
        """Resolve a played card. When `events` is a list, every action that
        changed the line is recorded as a step:
        {'actor': card, 'before': [cards], 'after': [cards], 'out': [cards]}
        — the raw material for the client to act the turn out card by card."""
        all_dropped = []
        before = list(self)
        queue, dropped = added_card.action(self)
        queue, burned = Queue(queue).burn_bats()
        dropped = list(dropped) + burned
        all_dropped += dropped
        if events is not None:
            events.append({'actor': added_card, 'before': before,
                           'after': list(queue), 'out': dropped})
        queue, dropped = Queue(queue).run_recurring(skip=added_card, events=events)
        all_dropped += dropped
        return queue, all_dropped

    def run_recurring(self, skip=None, events=None):
        """Recurring actions run once per turn, starting with the animal
        closest to the gate. The just-played card is skipped: its action
        already ran, and it only starts recurring on subsequent turns."""
        all_dropped = []
        queue, dropped = Queue(self).burn_bats()
        all_dropped += dropped
        if events is not None and dropped:
            events.append({'actor': dropped[0], 'before': list(self),
                           'after': list(queue), 'out': list(dropped)})
        for card in list(queue):
            if card is skip:
                continue
            if not card.repeating_action:
                continue
            if not any(c is card for c in queue):
                continue  # already removed by an earlier recurring action
            before = list(queue)
            queue, dropped = card.action(queue)
            queue, burned = Queue(queue).burn_bats()
            dropped = list(dropped) + burned
            all_dropped += dropped
            if events is not None and (dropped or before != list(queue)):
                events.append({'actor': card, 'before': before,
                               'after': list(queue), 'out': dropped})
        return Queue(queue), all_dropped

    def burn_bats(self):
        """Permanent rule from New Beasts in Town: a bat that is first in
        line (directly at Heaven's Gate) burns up immediately."""
        queue, dropped = Queue(self), []
        while queue and getattr(queue[0], 'burns_at_gate', False):
            dropped.append(queue.pop(0))
        return queue, dropped