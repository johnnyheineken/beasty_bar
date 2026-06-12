"""Empirical strategy analysis for the classic deck.

Self-play games between hard bots; for every card we track when it was
played (queue length, game phase) and where it ended (bar / trash), and
whether its owner won. Run: python analysis/strategy_stats.py [games]
"""
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
logging.disable(logging.CRITICAL)

from logic import GameRunner  # noqa: E402
from safari.players import bots  # noqa: E402
from safari.players.strategies import Max  # noqa: E402
from safari.stacks.shuffle import init  # noqa: E402

NAMES = {12: 'Lion', 11: 'Hippo', 10: 'Croc', 9: 'Snake', 8: 'Giraffe', 7: 'Zebra',
         6: 'Seal', 5: 'Chameleon', 4: 'Monkey', 3: 'Kangaroo', 2: 'Parrot', 1: 'Skunk'}


def play_game(n_players=4):
    runner = GameRunner(init(strategies={i: Max for i in range(n_players)}, deck='classic'))
    gs = runner.game_state
    gs.scoring = 'points'
    plays = []   # (player, value, queue_len_before, turn_no)
    guard = 0
    while not gs.finished:
        guard += 1
        assert guard < 400
        p = gs.current_player
        hand = gs.table[p]['hand']
        if not hand:
            gs.mark_player_finished(p)
            runner.check_game_end()
            gs.increment_turn()
            gs.next_player()
            continue
        card, setup = bots.choose('hard', gs, p)
        bots.apply_setup(card, setup, hand)
        plays.append((p, int(card.value), len(gs.queue), gs.turn_number))
        runner.update_game_state(card)
    gs.update_results()
    winners = set(gs.get_winners())
    in_bar = {(c.player, int(c.value)) for c in gs.cards_in_bar}
    return plays, winners, in_bar


def main(n_games=1500):
    fate = defaultdict(lambda: [0, 0])            # value -> [in_bar, played]
    fate_by_qlen = defaultdict(lambda: [0, 0])    # (value, qlen) -> [in_bar, played]
    fate_by_phase = defaultdict(lambda: [0, 0])   # (value, phase) -> [in_bar, played]
    win_qlen = defaultdict(lambda: [0, 0])        # (value, qlen) -> [owner_won, played]
    seat_wins = defaultdict(int)

    for g in range(n_games):
        plays, winners, in_bar = play_game()
        max_turn = max(t for _, _, _, t in plays) or 1
        for p, v, qlen, turn in plays:
            phase = min(2, 3 * turn // (max_turn + 1))   # 0 early, 1 mid, 2 late
            ok = (p, v) in in_bar
            won = p in winners
            fate[v][0] += ok; fate[v][1] += 1
            fate_by_qlen[(v, qlen)][0] += ok; fate_by_qlen[(v, qlen)][1] += 1
            fate_by_phase[(v, phase)][0] += ok; fate_by_phase[(v, phase)][1] += 1
            win_qlen[(v, qlen)][0] += won; win_qlen[(v, qlen)][1] += 1
        for w in winners:
            seat_wins[w] += 1 / len(winners)

    print(f"=== {n_games} games, 4 hard bots, classic deck, points scoring ===\n")
    print("card           reaches bar   (worth)   expected points/play")
    points = {12: 2, 11: 2, 10: 2, 9: 2, 8: 3, 7: 3, 6: 3, 5: 3, 4: 4, 3: 4, 2: 4, 1: 4}
    for v in range(12, 0, -1):
        ok, n = fate[v]
        rate = ok / n if n else 0
        print(f"{NAMES[v]:<11}{rate:>10.0%}        {points[v]}pt      {rate * points[v]:.2f}")

    print("\ncard x queue length when played -> chance it reaches the bar")
    print(f"{'card':<11}" + "".join(f"q={q:<5}" for q in range(5)))
    for v in range(12, 0, -1):
        row = f"{NAMES[v]:<11}"
        for q in range(5):
            ok, n = fate_by_qlen[(v, q)]
            row += f"{ok/n:>4.0%} " if n >= 30 else "  ·  "
        print(row)

    print("\ncard x game phase -> chance it reaches the bar (early/mid/late)")
    for v in range(12, 0, -1):
        row = f"{NAMES[v]:<11}"
        for ph in range(3):
            ok, n = fate_by_phase[(v, ph)]
            row += f"{ok/n:>5.0%} " if n >= 30 else "   ·  "
        print(row)

    print("\nseat -> win share (fair start, share of wins incl. ties)")
    total = sum(seat_wins.values())
    for s in sorted(seat_wins):
        print(f"  seat {s}: {seat_wins[s]/total:.1%}")


if __name__ == "__main__":
    random.seed(2026)
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1500)
