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
LEVELS = ('easy', 'medium', 'hard', 'ultra')

# value of standing at position 0..4 (position 0 enters the bar next)
POSITION_WEIGHT = [5.0, 4.0, 2.5, 1.5, 1.0]

# self-play analysis showed these cards swing from ~25% to ~75% bar rate
# depending on WHEN they are played: they decide the gate, so they should
# be held until they can complete (or nearly complete) the line
CLOSERS = ('Snake', 'Seal', 'Lion', 'Dog')


def choose(level, gs, seat):
    """Pick (card, setup) for the given seat. `setup` is a dict of card
    attributes (target_index, jump, parity, imitate, imitate_value)."""
    hand = gs.table[seat]['hand']
    if level == 'easy':
        return random.choice(hand), {}
    if level == 'ultra':
        return choose_ultra(gs, seat)

    best = None
    for card in hand:
        setups = candidate_setups(gs, seat, card) if level == 'hard' else [{}]
        for setup in setups:
            try:
                score, _, _ = score_play(gs, seat, card, setup, level)
            except Exception:
                continue
            if level == 'medium':
                score += random.uniform(-5.0, 5.0)  # imperfect on purpose
            if best is None or score > best[0]:
                best = (score, card, setup)
    if best is None:
        return random.choice(hand), {}
    return best[1], best[2]


def choose_ultra(gs, seat, shortlist=5, samples=2):
    """Two-ply search: shortlist moves with the ultra scoring, then judge
    each by the position AFTER the next opponent's best reply, with their
    hand sampled from the cards they can still be holding."""
    cands = []
    for card in gs.table[seat]['hand']:
        for setup in candidate_setups(gs, seat, card):
            try:
                score, _, _ = score_play(gs, seat, card, setup, 'ultra')
            except Exception:
                continue
            cands.append((score, card, setup))
    if not cands:
        return random.choice(gs.table[seat]['hand']), {}
    cands.sort(key=lambda x: -x[0])

    best = None
    for base, card, setup in cands[:shortlist]:
        try:
            sim, _, _ = simulate(gs, seat, card, setup)
        except Exception:
            continue
        after = _lookahead_value(sim, seat, samples)
        total = base if after is None else 0.35 * base + 0.65 * after
        if best is None or total > best[0]:
            best = (total, card, setup)
    return (best[1], best[2]) if best else (cands[0][1], cands[0][2])


def _lookahead_value(sim, seat, samples):
    """Expected value of `seat`'s position after the next opponent's best
    reply. The opponent's remaining cards are public knowledge (a deck is
    12 known animals minus what's visible) — which 4 they HOLD is not, so
    hands are sampled rather than peeked at."""
    opp = None
    for k in range(1, sim.n_players):
        cand = (seat + k) % sim.n_players
        if sim.table[cand]['hand']:
            opp = cand
            break
    if opp is None:
        return None
    pool = [c.__class__ for c in sim.table[opp]['hand'] + sim.table[opp]['deck']]
    if not pool:
        return None
    hand_size = min(len(sim.table[opp]['hand']), len(pool))
    values = []
    for _ in range(samples):
        random.shuffle(pool)
        trial = copy.deepcopy(sim)
        trial.table[opp]['hand'] = [cls(opp) for cls in pool[:hand_size]]
        trial.table[opp]['deck'] = [cls(opp) for cls in pool[hand_size:]]
        try:
            card, setup = choose('hard', trial, opp)
            after, _, _ = simulate(trial, opp, card, setup)
        except Exception:
            continue
        values.append(position_value(after, seat))
    return sum(values) / len(values) if values else None


def position_value(state, seat):
    """Absolute worth of a full state from `seat`'s point of view, on the
    same scale as evaluate()."""
    def unit(c):
        return c.point_value if state.scoring == 'points' else 1

    v = 0.0
    for c in state.cards_in_bar:
        v += (10 if c.player == seat else -10) * unit(c)
    for c in state.cards_in_thrash:
        v += (-7 if c.player == seat else 6) * unit(c)
    for i, c in enumerate(state.queue):
        w = POSITION_WEIGHT[i] if i < len(POSITION_WEIGHT) else 1.0
        v += (w if c.player == seat else -w * 0.7) * unit(c) * 0.8
    return v


def score_play(gs, seat, card, setup, level='ultra'):
    """Simulate one candidate play and score the outcome."""
    sim, to_bar, to_trash = simulate(gs, seat, card, setup)
    score = evaluate(sim, to_bar, to_trash, seat)
    if level in ('hard', 'ultra'):
        score += threat_term(sim, seat)
    if level == 'ultra':
        score += ultra_priors(gs, seat, card, sim, to_bar, to_trash)
    return score, to_bar, to_trash


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


# weights for the ultra priors (tuned by self-play sweep, see analysis/)
ULTRA_W = {'handoff': 3.0, 'leader': 1.0}


def ultra_priors(gs, seat, card, sim, to_bar, to_trash):
    """Strategy distilled from self-play analysis: the decisive moment is
    handing over a 4-card line — score it with exact gate math instead of
    positional guesses — and removal should punch at the leader."""
    score = ULTRA_W['handoff'] * gate_handoff_term(sim, seat)

    def unit(c):
        return c.point_value if sim.scoring == 'points' else 1

    totals = {}
    for c in sim.cards_in_bar:
        totals[c.player] = totals.get(c.player, 0) + unit(c)
    rivals = {p: v for p, v in totals.items() if p != seat}
    if rivals:
        leader = max(rivals, key=rivals.get)
        score += ULTRA_W['leader'] * sum(1 for c in to_trash if c.player == leader)
        score -= ULTRA_W['leader'] * sum(1 for c in to_bar if c.player == leader)
    return score


def gate_handoff_term(sim, seat):
    """When our move leaves exactly 4 in line, the next player completes
    it and the gate opens at once. Average our net entering points over
    their canonical replies: plain join, a lion-style cut to the front,
    a snake-style sort, and a seal-style reversal."""
    queue = sim.queue
    if len(queue) != 4:
        return 0.0

    def unit(c):
        return c.point_value if sim.scoring == 'points' else 1

    def net(entering):
        return sum(unit(c) if c.player == seat else -unit(c) * 0.6 for c in entering)

    plain = net(queue[:2])                       # they join at the back
    cut = net(queue[:1])                          # their card takes spot 1
    by_strength = sorted(queue, key=lambda c: -int(c.value))
    sort = net(by_strength[:2])                   # snake-style re-sort
    reverse = net(list(queue)[::-1][:2])          # seal-style reversal
    # plain joins dominate in practice; the disruptions split the rest
    return 0.55 * plain + 0.15 * cut + 0.15 * sort + 0.15 * reverse


def review_move(gs, seat, chosen_card):
    """Score the play the player chose (decisions already attached to the
    card) against the best alternative the ultra bot can find. Returns
    the raw material for a post-game 'misplays' report."""
    chosen_score, _, _ = score_play(gs, seat, chosen_card, {})
    best = None
    for card in gs.table[seat]['hand']:
        for setup in candidate_setups(gs, seat, card):
            try:
                score, _, _ = score_play(gs, seat, card, setup)
            except Exception:
                continue
            if best is None or score > best[0]:
                best = (score, card, setup)
    if best is None:
        best = (chosen_score, chosen_card, {})
    return {
        'chosen_score': round(chosen_score, 2),
        'best_score': round(best[0], 2),
        'best_card': best[1],
        'best_setup': best[2],
    }


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
