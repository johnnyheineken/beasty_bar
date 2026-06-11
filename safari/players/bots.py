"""AI opponents for the web game.

Three difficulty levels:
- easy   🐣  plays a random card with default decisions
- medium 🙂  simulates each hand card (default decisions) and picks the
             best outcome, with a little noise so it stays beatable
- hard   🧠  additionally searches the decision space of every card
             (parrot/bat targets, kangaroo distance, ostrich parity,
             chameleon/penguin imitations) before picking

All levels share one evaluation: a play is simulated on a copy of the
game state (including the five-animal check), then scored by who got
into the bar, who got thrown out, and how well-placed the bot's cards
are in the resulting line.
"""
import copy
import random

BAR_QUEUE_LENGTH = 5
LEVELS = ('easy', 'medium', 'hard')

# value of standing at position 0..4 (position 0 enters the bar next)
POSITION_WEIGHT = [5.0, 4.0, 2.5, 1.5, 1.0]


def choose(level, gs, seat):
    """Pick (card, setup) for the given seat. `setup` is a dict of card
    attributes (target_index, jump, parity, imitate, imitate_value)."""
    hand = gs.table[seat]['hand']
    if level == 'easy':
        return random.choice(hand), {}

    best = None
    for card in hand:
        setups = candidate_setups(gs, seat, card) if level == 'hard' else [{}]
        for setup in setups:
            try:
                sim, to_bar, to_trash = simulate(gs, seat, card, setup)
            except Exception:
                continue
            score = evaluate(sim, to_bar, to_trash, seat)
            if level == 'hard':
                # foresight: what will enemy crocs/tigers/hippos do to the
                # resulting line on their next recurring pass?
                score += threat_term(sim, seat)
            else:
                score += random.uniform(-5.0, 5.0)  # imperfect on purpose
            if best is None or score > best[0]:
                best = (score, card, setup)
    if best is None:
        return random.choice(hand), {}
    return best[1], best[2]


def apply_setup(card, setup, hand):
    for key, value in setup.items():
        if key == 'imitate_value':
            chosen = next((c for c in hand
                           if c is not card and int(c.value) == int(value)), None)
            if chosen is not None:
                card.imitate_class = chosen.__class__
        else:
            setattr(card, key, value)


def simulate(gs, seat, card, setup):
    """Dry-run playing `card` (a member of seat's hand) with the given
    decisions, including the five-animal check. Returns the simulated
    state and the cards that went to the bar / trash."""
    sim = copy.deepcopy(gs)
    hand = sim.get_player_hand(seat)
    sim_card = next(c for c in hand if int(c.value) == int(card.value))
    apply_setup(sim_card, setup, hand)
    bar0, trash0 = len(sim.cards_in_bar), len(sim.cards_in_thrash)

    sim.update_queue(sim_card)
    if len(sim.queue) == BAR_QUEUE_LENGTH:
        sim.cards_in_bar.extend(sim.queue[:2])
        sim.cards_in_thrash.append(sim.queue[-1])
        sim.queue = sim.queue[2:4]
        queue, burned = sim.queue.burn_bats()
        sim.queue = queue
        sim.cards_in_thrash.extend(burned)

    return sim, sim.cards_in_bar[bar0:], sim.cards_in_thrash[trash0:]


def evaluate(sim, to_bar, to_trash, seat):
    def unit(card):
        return card.point_value if sim.scoring == 'points' else 1

    score = 0.0
    for c in to_bar:
        score += (10 if c.player == seat else -10) * unit(c)
    for c in to_trash:
        score += (-7 if c.player == seat else 6) * unit(c)
    for i, c in enumerate(sim.queue):
        w = POSITION_WEIGHT[i] if i < len(POSITION_WEIGHT) else 1.0
        score += (w if c.player == seat else -w * 0.7) * unit(c) * 0.8
    return score


def threat_term(sim, seat):
    """Penalty/bonus for cards that standing recurring threats (enemy croc,
    tiger, hippo) will remove or pass on the next turn."""
    def unit(card):
        return card.point_value if sim.scoring == 'points' else 1

    queue = sim.queue
    score = 0.0
    for j, hunter in enumerate(queue):
        if hunter.player == seat:
            continue
        kind = hunter.__class__.__name__
        if kind == 'Croc':
            # eats everything weaker in front of it down to the last
            # stopper (lion / hippo / croc / zebra)
            stop = -1
            for i in range(j - 1, -1, -1):
                if queue[i].__class__.__name__ in ('Lion', 'Hippo', 'Croc', 'Zebra'):
                    stop = i
                    break
            for i in range(stop + 1, j):
                victim = queue[i]
                score += (-5 if victim.player == seat else 4) * unit(victim)
        elif kind == 'Tiger' and j >= 2:
            victim = queue[j - 2]
            if victim.value < hunter.value and not getattr(victim, 'reflects_bruisers', False):
                score += (-5 if victim.player == seat else 4) * unit(victim)
        elif kind == 'Hippo':
            # will push past weaker animals: our cards in front of it lose
            # their positional edge
            for i in range(j - 1, -1, -1):
                if queue[i].__class__.__name__ in ('Lion', 'Hippo', 'Zebra'):
                    break
                if queue[i].player == seat:
                    score -= 1.0 * unit(queue[i])
    return score


def candidate_setups(gs, seat, card):
    """All decision variants worth trying for a card (hard bots)."""
    name = card.__class__.__name__
    q = len(gs.queue)
    if name == 'Parrot' and q:
        return [{'target_index': i} for i in range(q)]
    if name == 'Bat' and q:
        return [{'target_index': i} for i in range(q)] + [{}]
    if name == 'Kangaroo' and q >= 2:
        return [{'jump': 1}, {'jump': 2}]
    if name == 'Ostrich' and q:
        return [{'parity': 'even'}, {'parity': 'odd'}]
    if name == 'Chameleon':
        species = sorted({int(c.value) for c in gs.queue
                          if c.__class__.__name__ != 'Chameleon'})
        return [{'imitate': v} for v in species] or [{}]
    if name == 'Penguin':
        hand = gs.table[seat]['hand']
        others = sorted({int(c.value) for c in hand if c is not card})
        return [{'imitate_value': v} for v in others] or [{}]
    return [{}]
