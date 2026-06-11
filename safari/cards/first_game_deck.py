from safari.cards.base import ANIMALS, Card
from safari.stacks.queue import Queue


class Monkey(Card):
    """
    If there is one or more monkeys in the queue:
        - monkeys go to the start of the queue in the reversed order
        - hippo & cric goes away
    """

    value = ANIMALS.MONKEY
    point_value = 3

    def action(self, queue: Queue) -> (Queue, list):
        dropped = []
        monkeys = queue.find_indices_of(ANIMALS.MONKEY)
        if monkeys:
            queue = Queue([self] + [queue.pop(i) for i in reversed(monkeys)] + queue)
            dropped += queue.drop_card_values(ANIMALS.HIPPO)
            dropped += queue.drop_card_values(ANIMALS.CROC)

        else:
            queue.append(self)

        return queue, dropped


class Lion(Card):
    """
    Go to the start of the line, unless there is already Lion in the queue.
    If there are monkeys in the queue, throw them out.
    """

    value = ANIMALS.LION
    point_value = 2

    def action(self, queue: Queue):
        dropped = []
        lions = queue.find_indices_of(ANIMALS.LION)
        if lions:
            dropped = [self]
        else:
            dropped += queue.drop_card_values(ANIMALS.MONKEY)
            queue = [self] + queue
        return Queue(queue), dropped


class Hippo(Card):
    """
    Repeating action.
    Go to the strt of the queue, unless there is Lion, Zebra, or Hippo in front of you.
    """

    value = ANIMALS.HIPPO
    point_value = 2
    repeating_action = True

    def action(self, queue: Queue):
        dropped = []
        rest = []
        if self in queue:
            rest = Queue(queue[queue.index(self) + 1 :])
            queue = Queue(queue[: queue.index(self)])

        stopping_animals = sorted(
            queue.find_indices_of(ANIMALS.ZEBRA)
            + queue.find_indices_of(ANIMALS.LION)
            + queue.find_indices_of(ANIMALS.HIPPO)
        )
        if stopping_animals:
            queue = (
                queue[: stopping_animals[-1] + 1]
                + [self]
                + queue[stopping_animals[-1] + 1 :]
            )
        else:
            queue = [self] + queue
        queue = queue + rest

        return Queue(queue), dropped


class Croc(Card):
    """
    Repeating action.
    Eat any animal, which is not Lion, Hippo, Zebra or Croc in front of you.
    (Smaller, but not Zebra.)
    """

    value = ANIMALS.CROC
    point_value = 3
    repeating_action = True

    def action(self, queue: Queue):
        dropped = []
        rest = []
        if self in queue:
            rest = Queue(queue[queue.index(self) + 1 :])
            queue = Queue(queue[: queue.index(self)])

        stopping_animals = sorted(
            queue.find_indices_of(ANIMALS.ZEBRA)
            + queue.find_indices_of(ANIMALS.LION)
            + queue.find_indices_of(ANIMALS.HIPPO)
            + queue.find_indices_of(ANIMALS.CROC)
        )
        if stopping_animals:
            dropped += queue[stopping_animals[-1] + 1 :]
            queue = queue[: stopping_animals[-1] + 1] + [self]
        else:
            dropped = queue
            queue = [self]

        queue = queue + rest
        return Queue(queue), dropped


class Snake(Card):
    """
    Sort all cards by their value, strongest closest to the gate.
    Members of the same species keep their relative order.
    """

    value = ANIMALS.SNAKE
    point_value = 2

    def action(self, queue: Queue):
        dropped = []
        queue += [self]
        queue = sorted(queue, key=lambda x: -x.value)
        return Queue(queue), dropped


class Gazelle(Card):
    """
    Repeating action.
    Jump one animal with strictly lower value in front of you (one per turn).
    """

    value = ANIMALS.GAZELLE
    point_value = 3
    repeating_action = True

    def action(self, queue: Queue):
        dropped = []
        rest = []
        if self in queue:
            rest = Queue(queue[queue.index(self) + 1 :])
            queue = Queue(queue[: queue.index(self)])
        if len(queue) == 0:
            queue += [self]
        else:
            animal_in_front = queue[-1]
            if animal_in_front.value < self.value:
                queue = queue[:-1] + [self] + [animal_in_front]
            else:
                queue += [self]
        queue += rest

        return Queue(queue), dropped


class Zebra(Card):
    """
    Stops action of most animals.
    """

    value = ANIMALS.ZEBRA
    point_value = 4

    def action(self, queue: Queue):
        dropped = []
        queue = queue + [self]

        return Queue(queue), dropped


class Seal(Card):
    """
    Reverse the queue.
    """

    value = ANIMALS.SEAL
    point_value = 2

    def action(self, queue: Queue):
        dropped = []
        queue = queue + [self]
        queue = reversed(queue)

        return Queue(queue), dropped


class Chameleon(Card):
    """
    Carry out the action of a species currently present in the queue,
    taking on its strength for that action only. Set `imitate` to the
    ANIMALS value of the chosen species (must be present in the queue);
    otherwise the first non-chameleon species in line is imitated.
    """

    value = ANIMALS.CHAMELEON
    point_value = 3
    taken_form_of = None
    imitate = None

    def __str__(self):
        desc = super().__str__()
        desc += "" if self.taken_form_of is None else f" as {self.taken_form_of}"
        return desc

    def action(self, queue: Queue):
        species = {
            i.value: i.__class__ for i in queue if not isinstance(i, Chameleon)
        }
        if not species:
            queue += [self]
            return Queue(queue), []

        chosen = self.imitate if self.imitate in species else next(iter(species))
        mimic = species[chosen]
        self.taken_form_of = mimic.__name__
        self.value = mimic.value
        try:
            queue, dropped = mimic.action(self, queue)
        finally:
            self.value = ANIMALS.CHAMELEON
        return Queue(queue), dropped


class Kangaroo(Card):
    """
    Jump over the last one or two animals in line (player's choice,
    via the `jump` attribute; defaults to two).
    """

    value = ANIMALS.KANGAROO
    point_value = 4

    def action(self, queue):
        dropped = []
        jump = getattr(self, 'jump', 2)
        jump = max(1, min(2, jump, len(queue)))
        cut = len(queue) - jump
        queue = queue[:cut] + [self] + queue[cut:]
        return Queue(queue), dropped


class Parrot(Card):
    """
    Throw an animal of the player's choice (via the `target_index`
    attribute) to the thrash. Parrot itself goes to the last position
    in the queue. Without an explicit choice, the strongest animal not
    owned by the parrot's player is thrown out.
    """

    value = ANIMALS.PARROT
    point_value = 4

    def action(self, queue):
        dropped = []
        if queue:
            target = getattr(self, 'target_index', None)
            if target is None or not 0 <= target < len(queue):
                target = self._default_target(queue)
            dropped = [queue.pop(target)]
        queue += [self]
        return Queue(queue), dropped

    def _default_target(self, queue):
        candidates = [i for i, c in enumerate(queue) if c.player != self.player]
        if not candidates:
            candidates = range(len(queue))
        return max(candidates, key=lambda i: queue[i].value)


class Skunk(Card):
    """
    All animals with the two highest values go to the thrash.
    """

    value = ANIMALS.SKUNK
    point_value = 4

    def action(self, queue):
        dropped = []
        card_values = [i.value for i in queue if i.value != ANIMALS.SKUNK]
        unique = sorted(list(set(card_values)))
        if len(unique) <= 2:
            to_drop = unique
        else:
            to_drop = unique[-2:]
        for i in to_drop:
            dropped += queue.drop_card_values(i)
        queue += [self]
        return Queue(queue), dropped
