"""Adversarial dynamics on the classic deck: does retaliation pay, and
how much does it hurt to be ganged up on?

- tit-for-tat: a bot that biases its removal toward whoever trashed its
  cards most recently
- 3v1: three bots share a fixed target and weight all damage to them

Run: python analysis/adversarial.py [games]
"""
import logging
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from logic import GameRunner  # noqa: E402
from safari.players import bots  # noqa: E402
from safari.players.strategies import Max  # noqa: E402
from safari.stacks.shuffle import init  # noqa: E402


def choose_biased(gs, seat, weights):
    """Hard-bot choice with extra reward for hurting weighted opponents."""
    def unit(c):
        return c.point_value if gs.scoring == 'points' else 1

    best = None
    for card in gs.table[seat]['hand']:
        for setup in bots.candidate_setups(gs, seat, card):
            try:
                score, to_bar, to_trash = bots.score_play(gs, seat, card, setup, 'hard')
            except Exception:
                continue
            for c in to_trash:
                score += weights.get(c.player, 0) * unit(c)
            for c in to_bar:
                score -= weights.get(c.player, 0) * unit(c)
            if best is None or score > best[0]:
                best = (score, card, setup)
    if best is None:
        return random.choice(gs.table[seat]['hand']), {}
    return best[1], best[2]


def play_game(chooser_by_seat, n_players=4, deck='classic'):
    runner = GameRunner(init(strategies={i: Max for i in range(n_players)}, deck=deck))
    gs = runner.game_state
    gs.scoring = 'points'
    grudges = defaultdict(Counter)   # victim -> {offender: count}
    guard = 0
    while not gs.finished:
        guard += 1
        assert guard < 500
        p = gs.current_player
        hand = gs.table[p]['hand']
        if not hand:
            gs.mark_player_finished(p)
            runner.check_game_end()
            gs.increment_turn()
            gs.next_player()
            continue
        trash_before = len(gs.cards_in_thrash)
        card, setup = chooser_by_seat[p](gs, p, grudges)
        bots.apply_setup(card, setup, hand)
        runner.update_game_state(card)
        for victim_card in gs.cards_in_thrash[trash_before:]:
            if victim_card.player != p:
                grudges[victim_card.player][p] += 1
    gs.update_results()
    return gs.get_winners(), gs.results


def hard(gs, seat, grudges):
    return bots.choose('hard', gs, seat)


def tit_for_tat(gs, seat, grudges):
    # retaliate proportionally to recent offenses against us
    weights = {off: min(3.0, 1.0 * n) for off, n in grudges[seat].items()}
    return choose_biased(gs, seat, weights)


def gang(target):
    def chooser(gs, seat, grudges):
        return choose_biased(gs, seat, {target: 2.5})
    return chooser


def run(n_games):
    random.seed(404)

    print(f"=== tit-for-tat: 2 TFT + 2 hard, {n_games} games ===")
    wins = Counter()
    for g in range(n_games):
        # rotate which seats are TFT so seat effects cancel out
        tft_seats = [(g + 0) % 4, (g + 2) % 4]
        chooser = {s: (tit_for_tat if s in tft_seats else hard) for s in range(4)}
        winners, _ = play_game(chooser)
        for w in winners:
            wins['tit-for-tat' if w in tft_seats else 'hard'] += 1
    total = sum(wins.values())
    for k, v in wins.most_common():
        print(f"  {k}: {v} ({v/total:.0%})")

    print(f"\n=== 3 vs 1: three bots gang up on seat T, {n_games} games ===")
    wins = Counter()
    points_t, points_rest = [], []
    for g in range(n_games):
        target = g % 4
        chooser = {s: (hard if s == target else gang(target)) for s in range(4)}
        winners, results = play_game(chooser)
        for w in winners:
            wins['target' if w == target else 'gang'] += 1
        points_t.append(results.get(target, 0))
        points_rest.append(sum(v for p, v in results.items() if p != target) / 3)
    total = sum(wins.values())
    print(f"  target win share: {wins['target']/total:.0%} (fair would be 25%)")
    print(f"  target avg points: {sum(points_t)/len(points_t):.1f}"
          f"  vs avg ganger: {sum(points_rest)/len(points_rest):.1f}")


if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
