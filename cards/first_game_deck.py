from cards.base import ANIMALS, Card
from stacks.queue import Queue


class Monkey(Card):
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
    value = ANIMALS.HIPPO
    point_value = 2
    repeating_action = True

    def action(self, queue: Queue):
        dropped = []
        rest = []
        if self in queue:
            rest = Queue(queue[queue.index(self) + 1:])
            queue = Queue(queue[:queue.index(self)])

        stopping_animals = sorted(
            queue.find_indices_of(ANIMALS.ZEBRA) + queue.find_indices_of(ANIMALS.LION) + queue.find_indices_of(
                ANIMALS.HIPPO))
        if stopping_animals:
            queue = queue[:stopping_animals[-1] + 1] + [self] + queue[stopping_animals[-1] + 1:]
        else:
            queue = [self] + queue
        queue = queue + rest

        return Queue(queue), dropped


class Croc(Card):
    value = ANIMALS.CROC
    point_value = 3
    repeating_action = True

    def action(self, queue: Queue):
        dropped = []
        rest = []
        if self in queue:
            rest = Queue(queue[queue.index(self) + 1:])
            queue = Queue(queue[:queue.index(self)])

        stopping_animals = sorted(queue.find_indices_of(ANIMALS.ZEBRA)
                                  + queue.find_indices_of(ANIMALS.LION)
                                  + queue.find_indices_of(ANIMALS.HIPPO)
                                  + queue.find_indices_of(ANIMALS.CROC))
        if stopping_animals:
            queue = queue[:stopping_animals[-1] + 1] + [self]
            dropped += queue[stopping_animals[-1] + 1:]
        else:
            queue = [self]
            dropped = queue
        queue = queue + rest
        return Queue(queue), dropped


class Snake(Card):
    value = ANIMALS.SNAKE
    point_value = 2

    def action(self, queue: Queue):
        dropped = []
        queue += [self]
        queue = reversed(sorted(queue, key=lambda x: x.value))
        return Queue(queue), dropped


class Gazelle(Card):
    value = ANIMALS.GAZELLE
    point_value = 3
    repeating_action = True
    
    def action(self, queue: Queue):
        dropped = []
        rest = []
        if self in queue:
            rest = Queue(queue[queue.index(self) + 1:])
            queue = Queue(queue[:queue.index(self)])
        if len(queue) == 0:
            queue += [self]
        else:
            animal_in_front = queue[-1]
            if animal_in_front.value <= self.value:
                queue = queue[:-1] + [self] + [animal_in_front]
            else:
                queue += [self]
        queue += rest


        return Queue(queue), dropped


class Zebra(Card):
    value = ANIMALS.ZEBRA
    point_value = 4

    def action(self, queue: Queue):
        dropped = []
        queue = queue + [self]

        return Queue(queue), dropped


class Seal(Card):
    value = ANIMALS.SEAL
    point_value = 2

    def action(self, queue: Queue):
        dropped = []
        queue = queue + [self]
        queue = reversed(queue)

        return Queue(queue), dropped


class Chameleon(Card):
    value = ANIMALS.CHAMELEON
    point_value = 3
    taken_form_of = None

    def __str__(self):
        desc = super().__str__()
        desc += '' if self.taken_form_of is None else f' as {self.taken_form_of}'
        return desc

    def resolve_action(self, queue: Queue, resolver=None):
        if resolver is None:
            classes_in_queue = [i.__class__ for i in queue if not isinstance(i, Chameleon)]
            if classes_in_queue:
                action = lambda x: classes_in_queue[0].action(self, x)
                self.taken_form_of = classes_in_queue[0].__name__
            else:
                action = lambda x: Zebra.action(self, x)
        else:
            action = resolver
        self.action = action


class Kangaroo(Card):
    value = ANIMALS.KANGAROO
    point_value = 4

    def action(self, queue):
        dropped = []
        if len(queue) < 2:
            queue = [self] + queue
        else:
            queue = queue[:-2] + [self] + queue[-2:]
        return Queue(queue), dropped


class Parrot(Card):
    value = ANIMALS.PARROT
    point_value = 4

    def action(self, queue):
        dropped = []
        if queue:
            dropped = [queue.pop(0)]
        queue += [self]
        return queue, dropped

    def resolve_action(self, queue: Queue, resolver=None):
        if resolver is None:
            pass
        else:
            action = resolver(queue)
            self.action = action


class Skunk(Card):
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
