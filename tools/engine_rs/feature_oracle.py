"""Feature oracle: the rung-2 feature vector and the hand evaluation, Python against Rust, on random positions.

    .venv/bin/python tools/engine_rs/feature_oracle.py [--positions 200] [--seed 0]
"""
import argparse, dataclasses, json, math, sys

from animal_kingdom.bots import features
from animal_kingdom.bots.greedy_bot import GreedyWeights, evaluate
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.learn.episodes import extract_as_scored
import ak_engine

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from oracle import CARDS_JSON, MAPS_JSON
from bot_oracle import positions

EXPERT_W = {"pending_target": 1.5, "buried_presence": 0.25, "food_progress": 0, "food_curve": 3, "food_proximity": 60, "food_race": True}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--positions", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    cards = load_cards()
    pool = sorted(c for c, card in cards.items() if card.collectible)
    config = Config.default()
    eng = ak_engine.Engine(CARDS_JSON, MAPS_JSON, json.dumps(dataclasses.asdict(config)), "map_b")
    names = features.feature_names("rung2")
    bad = 0
    pos = positions(a.positions, a.seed, cards, config, pool)
    for k, (seed, st) in enumerate(pos):
        rs = eng.from_dict(st.to_dict())
        for me in ("A", "B"):
            py = features.extract(st, me, "rung2")
            rr = rs.extract(me, "rung2")
            diffs = [(n, x, y) for n, x, y in zip(names, py, rr) if not math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-9)]
            py2 = extract_as_scored(st, me, "rung2")
            rr2 = rs.extract(me, "rung2", True)
            diffs2 = [(n, x, y) for n, x, y in zip(names, py2, rr2) if not math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-9)]
            ev_py = evaluate(st, me, GreedyWeights(**EXPERT_W))
            ev_rs = rs.evaluate(me, json.dumps(EXPERT_W))
            ev_bad = not (ev_py == ev_rs or math.isclose(ev_py, ev_rs, rel_tol=1e-12, abs_tol=1e-9))
            if diffs or diffs2 or ev_bad:
                bad += 1
                print(f"DIFF pos {k} seed {seed} {me}: features {diffs[:4]} as_scored {diffs2[:4]} eval py={ev_py} rs={ev_rs}"[:400], flush=True)
    print(f"=== {len(pos) * 2 - bad}/{len(pos) * 2} agree", flush=True)
