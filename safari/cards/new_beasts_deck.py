"""The "New Beasts in Town" expansion deck (Zoch, 2019).

Same queue framework as the base game. Specialties:
- Only the tiger and the llama have recurring actions.
- The porcupine permanently reflects "Big Bruisers" (rhino, tiger,
  cheetah): the attacker goes to THAT'S IT instead of the porcupine.
- The bat permanently burns up whenever it is first in line.
- The vulture never joins the line; it revives the top card of the
  THAT'S IT pile (handled in GameState, since it touches the piles).
- Scoring uses the point values printed on the cards, not guest count.
"""
from safari.cards.base import Card
from safari.stacks.queue import Queue


def _take_place(attacker, queue: Queue, victim_index: int):
    """Big Bruiser attack: the attacker eats the victim and takes its
    place — unless the victim is a porcupine, which reflects the attack."""
    victim = queue[victim_index]
    if getattr(victim, 'reflects_bruisers', False):
        if any(c is attacker for c in queue):
            queue.pop(next(i for i, c in enumerate(queue) if c is attacker))
        return Queue(queue), [attacker]
    queue[victim_index] = attacker
    return Queue(queue), [victim]


def _prefer_opponent(candidates, queue, player):
    """Among tied candidates, default to a card not owned by the player."""
    opponents = [i for i in candidates if queue[i].player != player]
    return (opponents or candidates)[0]


class Rhino(Card):
    """Rams the strongest animal in the queue onto THAT'S IT and takes
    its place (owner picks among ties via `target_index`)."""

    value = 12
    point_value = 3

    def action(self, queue: Queue):
        if not queue:
            return Queue(queue + [self]), []
        strongest = max(c.value for c in queue)
        candidates = [i for i, c in enumerate(queue) if c.value == strongest]
        target = getattr(self, 'target_index', None)
        if target not in candidates:
            target = _prefer_opponent(candidates, queue, self.player)
        return _take_place(self, queue, target)


class Bear(Card):
    """Drags all animals of the two lowest strengths (if weaker than 11)
    out of the line; they re-queue behind the bear in unchanged order."""

    value = 11
    point_value = 2

    def action(self, queue: Queue):
        queue = queue + [self]
        weaker = sorted({c.value for c in queue if c is not self and c.value < self.value})
        to_move = weaker[:2]
        stay = [c for c in queue if c is self or c.value not in to_move]
        moved = [c for c in queue if c is not self and c.value in to_move]
        return Queue(stay + moved), []


class Tiger(Card):
    """Recurring: jumps onto the animal two positions ahead of it and
    eats it if weaker than 10 (it may leap over a stronger animal in
    between). Jumps once per activation."""

    value = 10
    point_value = 3
    repeating_action = True

    def action(self, queue: Queue):
        if not any(c is self for c in queue):
            queue = queue + [self]
        i = next(i for i, c in enumerate(queue) if c is self)
        j = i - 2
        if j < 0 or queue[j].value >= self.value:
            return Queue(queue), []
        queue.pop(i)
        return _take_place(self, queue, j)


class Cheetah(Card):
    """Eats the weakest animal in the line (if weaker than 9) and takes
    its place (owner picks among ties via `target_index`)."""

    value = 9
    point_value = 4

    def action(self, queue: Queue):
        if not queue or min(c.value for c in queue) >= self.value:
            return Queue(queue + [self]), []
        weakest = min(c.value for c in queue)
        candidates = [i for i, c in enumerate(queue) if c.value == weakest]
        target = getattr(self, 'target_index', None)
        if target not in candidates:
            target = _prefer_opponent(candidates, queue, self.player)
        return _take_place(self, queue, target)


class Llama(Card):
    """Recurring: spits at the animal directly in front of it unless its
    strength is higher than 7; the spit-at animal bolts to the end of
    the line."""

    value = 8
    point_value = 4
    repeating_action = True

    def action(self, queue: Queue):
        if not any(c is self for c in queue):
            queue = queue + [self]
        i = next(i for i, c in enumerate(queue) if c is self)
        if i > 0 and queue[i - 1].value < self.value:
            grossed_out = queue.pop(i - 1)
            queue.append(grossed_out)
        return Queue(queue), []


class Porcupine(Card):
    """Permanent: if a Big Bruiser (rhino, tiger, cheetah) would send it
    to THAT'S IT, the attacker lands there instead."""

    value = 7
    point_value = 4
    reflects_bruisers = True

    def action(self, queue: Queue):
        return Queue(queue + [self]), []


class Ostrich(Card):
    """Runs past all animals of even or odd strength (player's choice
    via `parity`: 'even'/'odd') and stops behind the first animal of
    the other parity."""

    value = 6
    point_value = 3

    def action(self, queue: Queue):
        # helpers are referenced via the class: `self` may be a chameleon
        # or penguin that is imitating the ostrich
        parity = getattr(self, 'parity', None)
        if parity not in ('even', 'odd'):
            parity = 'even' if Ostrich._run_length(queue, 'even') >= Ostrich._run_length(queue, 'odd') else 'odd'
        position = len(queue) - Ostrich._run_length(queue, parity)
        queue = queue[:position] + [self] + queue[position:]
        return Queue(queue), []

    @staticmethod
    def _run_length(queue, parity):
        wanted = 0 if parity == 'even' else 1
        run = 0
        for card in reversed(queue):
            if card.value % 2 != wanted:
                break
            run += 1
        return run


class Penguin(Card):
    """Imitates another animal from the owner's hand (revealed, stays in
    hand): set `imitate_class` to that card's class. The penguin takes
    on the imitated value for that action only, then is a 5 again."""

    value = 5
    point_value = 3
    taken_form_of = None
    imitate_class = None

    def __str__(self):
        desc = super().__str__()
        desc += "" if self.taken_form_of is None else f" as {self.taken_form_of}"
        return desc

    def action(self, queue: Queue):
        mimic = self.imitate_class
        if mimic is None:
            return Queue(queue + [self]), []
        self.taken_form_of = mimic.__name__
        self.value = mimic.value
        try:
            queue, dropped = mimic.action(self, queue)
        finally:
            self.value = Penguin.value
        return Queue(queue), dropped


class Dog(Card):
    """Sorts the whole line by strength, weakest next to Heaven's Gate.
    Animals of the same value don't pass each other."""

    value = 4
    point_value = 2

    def action(self, queue: Queue):
        queue = queue + [self]
        return Queue(sorted(queue, key=lambda c: c.value)), []


class Peacock(Card):
    """Positions itself directly in front of the strongest animal in the
    line (owner picks among ties via `target_index`)."""

    value = 3
    point_value = 2

    def action(self, queue: Queue):
        if not queue:
            return Queue([self]), []
        strongest = max(c.value for c in queue)
        candidates = [i for i, c in enumerate(queue) if c.value == strongest]
        target = getattr(self, 'target_index', None)
        if target not in candidates:
            target = candidates[0]
        queue = queue[:target] + [self] + queue[target:]
        return Queue(queue), []


class Vulture(Card):
    """Never joins the line: revives the top card of the THAT'S IT pile,
    which re-joins the line and carries out its action. The vulture goes
    onto THAT'S IT at the end of the turn. If it revives another
    vulture, both immediately enter the bar. Handled in GameState."""

    value = 2
    point_value = 2
    revive_params = None

    def action(self, queue: Queue):
        # Only reached outside GameState (e.g. direct queue tests):
        # without a trash pile there is nothing to revive.
        return Queue(queue), [self]


class Bat(Card):
    """Sends any one animal in the line (via `target_index`) to THAT'S IT
    and takes its place. Permanent: whenever the bat is first in line,
    it burns up immediately."""

    value = 1
    point_value = 4
    burns_at_gate = True

    def action(self, queue: Queue):
        dropped = []
        target = getattr(self, 'target_index', None)
        if target is None or not 0 <= target < len(queue):
            # via the class: `self` may be an imitating chameleon/penguin
            target = Bat._default_target(self, queue)
        if target is None:
            queue = queue + [self]
        else:
            dropped.append(queue[target])
            queue[target] = self
        # burning up when in first position is checked by the queue sweep
        return Queue(queue), dropped

    def _default_target(self, queue):
        # never burn up voluntarily: only attack positions behind the gate
        candidates = [i for i in range(1, len(queue))]
        if not candidates:
            return None
        opponents = [i for i in candidates if queue[i].player != self.player]
        pool = opponents or candidates
        return max(pool, key=lambda i: queue[i].value)


NEW_BEASTS = [Bat, Vulture, Peacock, Dog, Penguin, Ostrich, Porcupine, Llama, Cheetah, Tiger, Bear, Rhino]
