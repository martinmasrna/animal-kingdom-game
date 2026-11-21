"""How fast the engine is: clone-and-apply pairs a second on one core, over positions from random games (every action
legal at each position, ending the turn included, applied to its own copy of the position). A bot's search is made of
these pairs, so this is the number its thinking time buys.

    .venv/bin/python tools/engine_rs/speed.py [--games 40] [--seconds 1.0]
"""
import argparse, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # this tree, not an installed copy
from animal_kingdom.game import CARDS, ENGINE, LEADERS


def positions(games, seed=0):
    """Positions from random games on the real cards: one every few actions."""
    rng = random.Random(seed)
    pool = sorted(c.id for c in CARDS.values() if c.collectible and c.id not in LEADERS)
    out = []
    for g in range(games):
        decks = []
        for _ in "AB":
            lead = rng.choice(sorted(LEADERS))
            decks.append((rng.sample(pool, 12) * 2 + [lead], lead))
        st = ENGINE.new_game(decks[0][0], decks[1][0], seed * 1000 + g, None, {"A": decks[0][1], "B": decks[1][1]})
        n = 0
        while st.is_terminal() is None and n < 600:
            legal = st.legal_actions()
            st.apply_action({"kind": "pass"} if st.can_pass() and rng.random() < 0.1 else rng.choice(legal), False)
            n += 1
            if n % 5 == 0 and st.is_terminal() is None:
                out.append(st.clone())
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--games", type=int, default=40)
    p.add_argument("--seconds", type=float, default=1.0)
    args = p.parse_args()
    pos = positions(args.games)
    pairs, seconds, reps = 0, 0.0, 50
    while seconds < args.seconds:
        for st in pos:
            n, t = st.bench_clone_apply(reps)
            pairs, seconds = pairs + n, seconds + t
    print(f"{len(pos)} positions from {args.games} random games")
    print(f"{pairs / seconds:,.0f} clone-and-apply pairs a second ({pairs} pairs in {seconds:.2f}s)")


if __name__ == "__main__":
    main()
