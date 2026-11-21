"""Speed of the two engines on the same positions: positions sampled from random games, and at each one every legal
action (ending the turn too, where it is legal) applied to its own clone of the position, which is what a bot's search
does all day. Prints clone-and-apply pairs per second for each engine, on one core.

    .venv/bin/python tools/engine_rs/speed.py [--games 40] [--seed 0] [--every 5]
"""
import argparse, random, sys, time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from common import engines
from fuzz import random_deck

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import PassAction
from animal_kingdom.engine.state import new_game


def positions(games, seed, every, cards, config):
    """Positions from random games on the real cards: every `every`th one a game passes through."""
    pool, out = sorted(cards), []
    for g in range(games):
        rng = random.Random(seed * 1000 + g)
        (deck_a, lead_a), (deck_b, lead_b) = random_deck(rng, pool, cards, ()), random_deck(rng, pool, cards, ())
        st = new_game(deck_a, deck_b, rng.getrandbits(32), cards=cards, config=config, leaders={"A": lead_a, "B": lead_b})
        step = 0
        while rules.is_terminal(st) is None and step < 2000:
            legal = rules.legal_actions(st)
            if step % every == 0:
                out.append(st.clone())
            # a random play most of the time, so boards fill up as they do in a real game
            action = PassAction() if rules.can_pass(st) and rng.random() < 0.15 else legal[rng.randrange(len(legal))]
            rules.apply_action(st, action, validate=False)
            step += 1
    return out


def python_pairs(st, reps):
    acts = list(rules.legal_actions(st))
    if rules.can_pass(st) and not any(isinstance(x, PassAction) for x in acts):
        acts.append(PassAction())
    t = time.perf_counter()
    for _ in range(reps):
        for act in acts:
            rules.apply_action(st.clone(), act, validate=False)
    return reps * len(acts), time.perf_counter() - t


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--every", type=int, default=5)
    a = ap.parse_args()
    cards, config, eng = engines()
    pos = positions(a.games, a.seed, a.every, cards, config)
    py_n = py_t = rs_n = rs_t = 0
    for st in pos:
        n, t = python_pairs(st, 2)
        py_n, py_t = py_n + n, py_t + t
        n, t = eng.from_dict(st.to_dict()).bench_clone_apply(400)
        rs_n, rs_t = rs_n + n, rs_t + t
    py_rate, rs_rate = py_n / py_t, rs_n / rs_t
    print(f"{len(pos)} positions from {a.games} random games, {py_n // 2 / len(pos):.1f} actions a position on average")
    print(f"Python: {py_rate:>12,.0f} clone-and-apply pairs a second ({py_n} pairs in {py_t:.2f}s)")
    print(f"Rust:   {rs_rate:>12,.0f} clone-and-apply pairs a second ({rs_n} pairs in {rs_t:.2f}s)")
    print(f"Rust is {rs_rate / py_rate:.0f} times the Python engine")
