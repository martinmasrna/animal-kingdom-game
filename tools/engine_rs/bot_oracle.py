"""Bot oracle: the same positions, the same seed, the Python bot and the Rust bot; their moves (and for the searchers
their root scores) must agree. Positions come from random play through the Python engine.

    .venv/bin/python tools/engine_rs/bot_oracle.py [--specs greedy,turn,expert] [--positions 60] [--seed 0]
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))   # REPO_ROOT: this tree, not an installed copy
import argparse, dataclasses, json, os, random, re, sys, time

os.environ["AK_PY_BOTS"] = "1"   # the Python side of the oracle must be the Python bot

from animal_kingdom.engine import rules
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import new_game
from animal_kingdom.sim.runner import make_bot
from animal_kingdom.bots.learned_eval import load_eval
from animal_kingdom.web.match import EXPERT
import ak_engine


def rust_bot(spec, seed):
    """The Rust bot of `spec`; a `*_learned` kind gets its evaluator artifact, as `sim.runner._rust_bot` hands it over."""
    head, _, tail = spec.partition(":")
    ev = None
    if head.endswith("_learned"):
        name = dict(kv.split("=", 1) for kv in tail.split(",") if "=" in kv).get("eval", "rung0")
        ev = json.dumps(load_eval(name).to_dict())
    return ak_engine.Bot(spec, seed, ev)

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from oracle import canon, CARDS_JSON, MAPS_JSON
from fuzz import random_deck

SPECS = {
    "greedy": "greedy",
    "easy": "easy",
    "turn": "turn",
    "normal": "turn:w.hq_threat_reach=0.5",
    "referee": "referee",
    "expert": EXPERT.replace("time_budget=8", "time_budget=0"),
    # the hand-evaluation Expert (the shipped one until 2026-10-23), still the baseline of the paired benchmark's history
    "expert_hand": re.sub(r"referee_learned:eval=[^,]*,", "referee:", EXPERT).replace("time_budget=8", "time_budget=0"),
}


def positions(n, seed, cards, config, pool):
    """Random positions: a random game played to a random depth, the player to act with more than one option."""
    rng = random.Random(seed)
    out = []
    tries = 0
    while len(out) < n and tries < n * 20:
        tries += 1
        s = seed * 1000 + tries
        da, db = random_deck(rng, pool, cards), random_deck(rng, pool, cards)
        st = new_game(list(da), list(db), s, map_id="map_b", config=config)
        depth = rng.randrange(0, 40)
        ok = True
        for _ in range(depth):
            if rules.is_terminal(st) is not None:
                ok = False
                break
            legal = rules.legal_actions(st)
            if not legal:
                ok = False
                break
            rules.apply_action(st, legal[rng.randrange(len(legal))])
        if not ok or rules.is_terminal(st) is not None:
            continue
        if len(rules.legal_actions(st)) < 2:
            continue
        out.append((s, st))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--specs", default="greedy,turn,expert,expert_hand")
    ap.add_argument("--positions", type=int, default=60)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--stop", action="store_true")
    a = ap.parse_args()
    cards = load_cards()
    pool = sorted(c for c, card in cards.items() if card.collectible)
    config = Config.default()
    eng = ak_engine.Engine(CARDS_JSON, MAPS_JSON, json.dumps(dataclasses.asdict(config)), "map_b")
    pos = positions(a.positions, a.seed, cards, config, pool)
    print(f"{len(pos)} positions", flush=True)
    for name in a.specs.split(","):
        spec = SPECS.get(name, name)
        agree = 0
        fails = 0
        t_py = t_rs = 0.0
        for k, (seed, st) in enumerate(pos):
            me = st.player_to_act()
            legal = rules.legal_actions(st)
            py_bot = make_bot(spec, seed)
            py_roots = {}
            if hasattr(py_bot, "_record_root_scores"):
                py_bot._record_root_scores = lambda sc, d=py_roots: d.setdefault("r", [(x.to_dict(), s) for x, s in sc])
            t0 = time.time()
            py_action = py_bot.choose(st.view_for(me), legal, st).to_dict()
            t_py += time.time() - t0
            rs_state = eng.from_dict(st.to_dict())
            rs_bot = rust_bot(spec, seed)
            t0 = time.time()
            rs_action = rs_bot.choose(rs_state)
            t_rs += time.time() - t0
            rs_roots = rs_bot.root_scores(rs_state)
            same = canon(py_action) == canon(rs_action)
            roots_same = True
            if "r" in py_roots:
                # the same roots with the same scores, to a relative 1e-9: a decided line sits near +-4e8, where the two
                # engines' arithmetic differs in the last bits
                pr = sorted((canon(x), s) for x, s in py_roots["r"])
                rr = sorted((canon(x), s) for x, s in rs_roots)
                roots_same = len(pr) == len(rr) and all(a == b and abs(x - y) <= 1e-9 * max(1.0, abs(x)) for (a, x), (b, y) in zip(pr, rr))
            if same and roots_same:
                agree += 1
            else:
                fails += 1
                print(f"  DIFF {name} pos {k} seed {seed} turn {st.turn_counter} {me}: py={py_action} rs={rs_action}", flush=True)
                if "r" in py_roots and not roots_same:
                    print(f"    py roots {sorted(py_roots['r'], key=lambda x: -x[1])[:5]}", flush=True)
                    print(f"    rs roots {sorted(rs_roots, key=lambda x: -x[1])[:5]}", flush=True)
                if a.stop:
                    break
        print(f"=== {name}: {agree}/{len(pos)} agree; python {t_py:.1f}s, rust {t_rs:.2f}s ({t_py / max(t_rs, 1e-6):.0f}x)", flush=True)
