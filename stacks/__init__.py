from cards import Card

class Queue(list):
    @property
    def values(self):
        return [i.value for i in self]

    def find_indices_of(self, card):
        # https://stackoverflow.com/a/6294205/4672992
        return [i for i, x in enumerate(self.values) if x == card]

    def drop_card_values(self, card):
        return [self.pop(i) for i in reversed(self.find_indices_of(card))]
    
    def resolve(self, added_card: Card):
        all_dropped = []
        if hasattr(added_card, 'resolve_action'):
            added_card.resolve_action(self)
        queue, dropped = added_card.action(self)
        all_dropped += dropped
        for card in reversed(queue):
            if card == added_card:
                continue
            if card.repeating_action:
                queue, dropped = card.action(queue)
                all_dropped += dropped
            
        return queue, all_dropped



