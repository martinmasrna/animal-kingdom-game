"""Crash fuzzer for the Python engine: random games over every collectible card, a random legal action each step from
whichever seat is to act, chosen by one seeded stream. It records

  - every exception raised by legal_actions, apply_action or is_terminal ("crash"),
  - every action legal_actions offered that apply_action refused with an EngineError ("refused"),
  - every game past --max-actions actions without ending ("long"),

groups them by the last engine frame of the traceback, and keeps the shortest reproduction per group (seed, decks,
action index). A game is fully determined by its seed: the decks and the action stream come from random.Random(seed),
the engine's own chance from new_game(seed).

    .venv/bin/python tools/engine_fuzz.py [--games 5000] [--seed 0] [--jobs 4] [--out results/engine_fuzz.json]
    .venv/bin/python tools/engine_fuzz.py --replay SEED [--show]     # replay one game, print where it fails

While a mulligan waits under the other seat's, that seat sometimes makes its choice first (rules.apply_early_mulligan),
as two people mulliganing at once do.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # this tree, not an installed copy

import argparse, json, random, time, traceback
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, PassAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import EngineError, new_game, other_player

ENGINE_DIR = _os.path.join("animal_kingdom", "engine")
LIMITS = {"common": 3, "rare": 2, "legendary": 1}

_CARDS = None
_POOL = None


def cards_and_pool():
    global _CARDS, _POOL
    if _CARDS is None:
        _CARDS = load_cards()
        _POOL = sorted(c for c, card in _CARDS.items() if card.collectible)
    return _CARDS, _POOL


def random_deck(rng: random.Random, pool: list[str], cards) -> list[str]:
    """30 cards within the copy limits (legendary 1 / rare 2 / common 3)."""
    deck: list[str] = []
    tries = 0
    while len(deck) < 30 and tries < 10000:
        tries += 1
        c = rng.choice(pool)
        if deck.count(c) < LIMITS.get(cards[c].rarity, 3):
            deck.append(c)
    return deck


def last_engine_frame(tb) -> str:
    """'file:line function' of the deepest traceback frame inside the engine package, else of the deepest frame."""
    frames = traceback.extract_tb(tb)
    eng = [f for f in frames if ENGINE_DIR in f.filename.replace("\\", "/")]
    f = (eng or frames)[-1]
    return f"{_os.path.relpath(f.filename)}:{f.lineno} {f.name}"


def _record(kind, where, exc, seed, index, deck_a, deck_b, action, call):
    return {"kind": kind, "where": where, "call": call, "error": f"{type(exc).__name__}: {exc}"[:500],
            "seed": seed, "index": index, "deck_a": deck_a, "deck_b": deck_b, "action": action,
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]}


def play(seed: int, *, max_actions: int = 300, pass_rate: float = 0.03, early_mull_rate: float = 0.3,
         stop_at: Optional[int] = None, decks=None):
    """Play one game. Returns (failure record or None, actions applied, state). `stop_at` stops before action index
    `stop_at` is chosen and returns the state there (for building a test position)."""
    cards, pool = cards_and_pool()
    rng = random.Random(seed)
    deck_a, deck_b = random_deck(rng, pool, cards), random_deck(rng, pool, cards)
    if decks is not None:
        deck_a, deck_b = list(decks[0]), list(decks[1])
    config = Config.default()
    state = new_game(list(deck_a), list(deck_b), seed, map_id="map_b", config=config)
    index = 0
    while True:
        try:
            term = rules.is_terminal(state)
        except Exception as e:
            return _record("crash", last_engine_frame(e.__traceback__), e, seed, index, deck_a, deck_b, None,
                           "is_terminal"), index, state
        if term is not None:
            return None, index, state
        if index >= max_actions:
            where = f"pending:{state.pending.get('kind')}" if state.pending else "top-level"
            return {"kind": "long", "where": f"past {max_actions} actions", "call": None, "seed": seed,
                    "index": index, "deck_a": deck_a, "deck_b": deck_b, "action": None,
                    "error": f"turn {state.turn_counter}, {where}", "traceback": ""}, index, state
        if stop_at is not None and index == stop_at:
            return None, index, state
        try:
            legal = rules.legal_actions(state)
        except Exception as e:
            return _record("crash", last_engine_frame(e.__traceback__), e, seed, index, deck_a, deck_b, None,
                           "legal_actions"), index, state
        early_by = None
        waiting = other_player(state.pending["chooser"]) if state.pending and state.pending.get("kind") == "mulligan" else None
        if waiting and rules.early_mulligan(state, waiting) is not None and rng.random() < early_mull_rate:
            req = rules.mulligan_request(state, waiting)
            opts = [ChoiceAction(o) for o in req["options"]] + [ChoiceAction(SKIP)]
            action, early_by = opts[rng.randrange(len(opts))], waiting
        elif not legal:
            e = RuntimeError("no legal actions but not terminal")
            return {"kind": "crash", "where": "no legal actions", "call": "legal_actions", "seed": seed,
                    "index": index, "deck_a": deck_a, "deck_b": deck_b, "action": None,
                    "error": str(e), "traceback": ""}, index, state
        elif rules.can_pass(state) and state.actions_taken_this_turn > 0 and rng.random() < pass_rate:
            action = PassAction()
        else:
            action = legal[rng.randrange(len(legal))]
        adict = action.to_dict()
        if early_by:
            adict["by"] = early_by
        try:
            if early_by:
                rules.apply_early_mulligan(state, early_by, action)
            else:
                rules.apply_action(state, action)
        except EngineError as e:
            return _record("refused", last_engine_frame(e.__traceback__), e, seed, index, deck_a, deck_b, adict,
                           "apply_early_mulligan" if early_by else "apply_action"), index, state
        except Exception as e:
            return _record("crash", last_engine_frame(e.__traceback__), e, seed, index, deck_a, deck_b, adict,
                           "apply_early_mulligan" if early_by else "apply_action"), index, state
        index += 1


def _run_chunk(args):
    seeds, max_actions, pass_rate = args
    out, total = [], 0
    for s in seeds:
        rec, n, _ = play(s, max_actions=max_actions, pass_rate=pass_rate)
        total += n
        if rec:
            out.append(rec)
    return out, total, len(seeds)


def group_key(rec) -> str:
    return f"{rec['kind']} | {rec['where']} | {rec['error'].split(':')[0]}" if rec["kind"] != "long" else "long"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--games", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=0, help="seeds run from SEED*100000")
    ap.add_argument("--jobs", type=int, default=_os.cpu_count() or 1)
    ap.add_argument("--max-actions", type=int, default=300)
    ap.add_argument("--pass-rate", type=float, default=0.03)
    ap.add_argument("--out", default="results/engine_fuzz.json")
    ap.add_argument("--replay", type=int, help="replay one seed and print its failure")
    ap.add_argument("--show", action="store_true", help="with --replay: print the traceback")
    a = ap.parse_args()

    if a.replay is not None:
        rec, n, state = play(a.replay, max_actions=a.max_actions, pass_rate=a.pass_rate)
        if not rec:
            print(f"seed {a.replay}: no failure, ended after {n} actions: {rules.is_terminal(state)}")
            return 0
        print(f"seed {a.replay}: {rec['kind']} at action index {rec['index']} ({rec['call']}) at {rec['where']}")
        print(f"  {rec['error']}\n  action: {rec['action']}")
        if a.show:
            print(rec["traceback"])
        return 1

    seeds = [a.seed * 100000 + k for k in range(a.games)]
    chunks = [(seeds[i::a.jobs * 8], a.max_actions, a.pass_rate) for i in range(a.jobs * 8)]
    t0 = time.time()
    records, total, games = [], 0, 0
    with ProcessPoolExecutor(a.jobs) as ex:
        for out, n, g in ex.map(_run_chunk, chunks):
            records += out; total += n; games += g
    groups: dict[str, dict] = {}
    for r in records:
        k = group_key(r)
        g = groups.setdefault(k, {"key": k, "count": 0, "seeds": [], "repro": r})
        g["count"] += 1
        g["seeds"].append(r["seed"])
        if (r["index"], r["seed"]) < (g["repro"]["index"], g["repro"]["seed"]):
            g["repro"] = r
    for g in groups.values():
        g["seeds"] = sorted(g["seeds"])[:50]
    summary = {"games": games, "actions": total, "failed_games": len(records), "seconds": round(time.time() - t0),
               "max_actions": a.max_actions, "pass_rate": a.pass_rate,
               "groups": sorted(groups.values(), key=lambda g: -g["count"])}
    _os.makedirs(_os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(summary, f, indent=1)
    print(f"=== {games} games, {total} actions, {len(records)} failed, {len(groups)} groups, {summary['seconds']}s -> {a.out}")
    for g in summary["groups"]:
        r = g["repro"]
        print(f"{g['count']:5d}  {g['key']}\n       repro: seed {r['seed']} index {r['index']}: {r['error'][:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
