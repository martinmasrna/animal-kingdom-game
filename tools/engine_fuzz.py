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
    .venv/bin/python tools/engine_fuzz.py --biased --games 20000 --seed 5     # effect-biased games (below)
    .venv/bin/python tools/engine_fuzz.py --human [--root results/human_games] # every action at every logged position

--biased: each deck holds at least six cards with a Roar, Dawn, Dusk, Fall, Flee, Spikes, Poison, Apex Predator or Roam
(EFFECT_WORDS); the action stream picks by weight: a placement of such a card x4, a placement covering an enemy x3
(they multiply), a skip of a pending choice x0.2, everything else x1. --replay of a biased seed needs --biased too.

--human: replays each logged human game that still replays on today's cards (old ids read through web/renamed.py; a log
that no longer replays is counted and skipped). At every position on the way it applies every legal action once, each on
its own clone, and records an exception or a refusal as above, its reproduction the log (path:line) and action index.

While a mulligan waits under the other seat's, that seat sometimes makes its choice first (rules.apply_early_mulligan),
as two people mulliganing at once do.
"""
from __future__ import annotations

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))   # this tree, not an installed copy

import argparse, glob, json, random, re, time, traceback
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

from animal_kingdom.engine import rules
from animal_kingdom.engine.actions import SKIP, ChoiceAction, PassAction, PlaceAction
from animal_kingdom.engine.cards import load_cards
from animal_kingdom.engine.config import Config
from animal_kingdom.engine.state import EngineError, new_game, other_player

ENGINE_DIR = _os.path.join("animal_kingdom", "engine")
LIMITS = {"common": 3, "rare": 2, "legendary": 1}

EFFECT_WORDS = ("Roar", "Dawn", "Dusk", "Fall", "Flee", "Spikes", "Poison", "Apex Predator", "Roam")
_EFFECT_RE = re.compile(r"\b(" + "|".join(EFFECT_WORDS) + r")\b")

_CARDS = None
_POOL = None
_EFFECT_POOL = None


def cards_and_pool():
    global _CARDS, _POOL, _EFFECT_POOL
    if _CARDS is None:
        _CARDS = load_cards()
        _POOL = sorted(c for c, card in _CARDS.items() if card.collectible)
        _EFFECT_POOL = [c for c in _POOL if is_effect_card(_CARDS[c])]
    return _CARDS, _POOL


def is_effect_card(card) -> bool:
    return bool(_EFFECT_RE.search(card.text or "")) or any(k in EFFECT_WORDS for k in card.keywords)


def biased_deck(rng: random.Random, pool: list[str], cards) -> list[str]:
    """A random 30-card deck holding at least six effect cards (6 to 15 of them drawn first)."""
    deck = random_deck(rng, _EFFECT_POOL, cards)[:rng.randint(6, 15)]
    tries = 0
    while len(deck) < 30 and tries < 10000:
        tries += 1
        c = rng.choice(pool)
        if deck.count(c) < LIMITS.get(cards[c].rarity, 3):
            deck.append(c)
    return deck


def action_weight(state, action) -> float:
    if isinstance(action, ChoiceAction):
        return 0.2 if action.choice == SKIP else 1.0
    if not isinstance(action, PlaceAction):
        return 1.0
    w = 4.0 if is_effect_card(state.cards[action.card_id]) else 1.0
    if action.target[0] == "cr":
        me = state.pending["chooser"] if state.pending else state.current
        stack = state.board.get(action.target[1])
        if stack and stack[-1].owner != me:
            w *= 3.0
    return w


def weighted_pick(rng: random.Random, state, legal):
    weights = [action_weight(state, a) for a in legal]
    r = rng.random() * sum(weights)
    for a, w in zip(legal, weights):
        r -= w
        if r < 0:
            return a
    return legal[-1]


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
         stop_at: Optional[int] = None, decks=None, biased: bool = False):
    """Play one game. Returns (failure record or None, actions applied, state). `stop_at` stops before action index
    `stop_at` is chosen and returns the state there (for building a test position)."""
    cards, pool = cards_and_pool()
    rng = random.Random(seed)
    make = biased_deck if biased else random_deck
    deck_a, deck_b = make(rng, pool, cards), make(rng, pool, cards)
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
        elif biased:
            action = weighted_pick(rng, state, legal)
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
    seeds, max_actions, pass_rate, biased = args
    out, total = [], 0
    for s in seeds:
        rec, n, _ = play(s, max_actions=max_actions, pass_rate=pass_rate, biased=biased)
        if rec:
            rec["biased"] = biased
        total += n
        if rec:
            out.append(rec)
    return out, total, len(seeds)


def human_logs(root: str):
    """(path, line, log) for every game record under `root`, old card ids read as their successors."""
    from animal_kingdom.web.renamed import renamed
    for path in sorted(glob.glob(_os.path.join(root, "**", "*.jsonl"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            for line_no, line in enumerate(fh):
                if line.strip():
                    yield _os.path.relpath(path), line_no, renamed(json.loads(line))


def _log_state(log):
    from animal_kingdom.decks import load_premade_deck
    deck_a, deck_b = log.get("lists") or (load_premade_deck(log["deck_a"]), load_premade_deck(log["deck_b"]))
    state = new_game(list(deck_a), list(deck_b), log["seed"], map_id=log.get("map_id", "map_b"),
                     config=Config.default().for_log(log), first_player=log["first_player"])
    return state, list(deck_a), list(deck_b)


def _skip_unlogged_mulligans(state, adict):
    """Logs leave out the mulligans a player kept without choosing: skip them as the replayer does."""
    while state.pending is not None and state.effect_stack and state.effect_stack[-1].get("op") == "mulligan" \
            and adict["kind"] != "choice":
        rules.apply_action(state, ChoiceAction(SKIP))


def replays(log) -> bool:
    """Whether the log still replays to its end on today's cards and rules."""
    try:
        state, _, _ = _log_state(log)
        for adict in log["actions"]:
            _skip_unlogged_mulligans(state, adict)
            rules.apply_logged(state, adict)
    except Exception:
        return False
    return True


def probe_position(state, where_from: dict) -> list[dict]:
    """Apply every legal action once, each on its own clone; a record for each exception or refusal."""
    out = []
    try:
        legal = rules.legal_actions(state)
        rules.is_terminal(state)
    except Exception as e:
        return [{**where_from, **_record("crash", last_engine_frame(e.__traceback__), e, None, where_from["index"],
                                          None, None, None, "legal_actions")}]
    for action in legal:
        st = state.clone()
        try:
            rules.apply_action(st, action)
            rules.is_terminal(st)
            if st.result is None:
                rules.legal_actions(st)
        except EngineError as e:
            out.append({**where_from, **_record("refused", last_engine_frame(e.__traceback__), e, None,
                                                 where_from["index"], None, None, action.to_dict(), "apply_action")})
        except Exception as e:
            out.append({**where_from, **_record("crash", last_engine_frame(e.__traceback__), e, None,
                                                 where_from["index"], None, None, action.to_dict(), "apply_action")})
    return out


def probe_log(task):
    """Replay one human log, probing every position. (replayed?, positions, actions tried, records)."""
    path, line_no, log = task
    if not replays(log):
        return False, 0, 0, []
    state, _, _ = _log_state(log)
    recs, positions, tried = [], 0, 0
    for index, adict in enumerate(log["actions"]):
        _skip_unlogged_mulligans(state, adict)
        if rules.is_terminal(state) is not None:
            break
        positions += 1
        tried += len(rules.legal_actions(state))
        for r in probe_position(state, {"log": f"{path}:{line_no}", "index": index}):
            r["seed"] = log["seed"]
            recs.append(r)
        rules.apply_logged(state, adict)
    return True, positions, tried, recs


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
    ap.add_argument("--biased", action="store_true", help="effect-heavy decks and an effect-preferring action stream")
    ap.add_argument("--human", action="store_true", help="probe every position of every replayable human game")
    ap.add_argument("--root", default="results/human_games")
    a = ap.parse_args()

    if a.human:
        return main_human(a)
    if a.replay is not None:
        rec, n, state = play(a.replay, max_actions=a.max_actions, pass_rate=a.pass_rate, biased=a.biased)
        if not rec:
            print(f"seed {a.replay}: no failure, ended after {n} actions: {rules.is_terminal(state)}")
            return 0
        print(f"seed {a.replay}: {rec['kind']} at action index {rec['index']} ({rec['call']}) at {rec['where']}")
        print(f"  {rec['error']}\n  action: {rec['action']}")
        if a.show:
            print(rec["traceback"])
        return 1

    seeds = [a.seed * 100000 + k for k in range(a.games)]
    chunks = [(seeds[i::a.jobs * 8], a.max_actions, a.pass_rate, a.biased) for i in range(a.jobs * 8)]
    t0 = time.time()
    records, total, games = [], 0, 0
    with ProcessPoolExecutor(a.jobs) as ex:
        for out, n, g in ex.map(_run_chunk, chunks):
            records += out; total += n; games += g
    summary = {"games": games, "actions": total, "failed_games": len(records), "seconds": round(time.time() - t0),
               "max_actions": a.max_actions, "pass_rate": a.pass_rate, "biased": a.biased,
               "groups": grouped(records)}
    write_summary(a.out, summary)
    print(f"=== {games} games, {total} actions, {len(records)} failed, {len(summary['groups'])} groups, {summary['seconds']}s -> {a.out}")
    print_groups(summary)
    return 0


def main_human(a):
    t0 = time.time()
    tasks = list(human_logs(a.root))
    logs = replayed = positions = tried = 0
    records = []
    with ProcessPoolExecutor(a.jobs) as ex:
        for ok, n, k, recs in ex.map(probe_log, tasks, chunksize=4):
            logs += 1; replayed += ok; positions += n; tried += k; records += recs
    summary = {"logs": logs, "replayed": replayed, "positions": positions, "actions_tried": tried,
               "failures": len(records), "seconds": round(time.time() - t0), "groups": grouped(records)}
    write_summary(a.out, summary)
    print(f"=== {logs} logs, {replayed} replay, {positions} positions, {tried} actions tried, {len(records)} failures, "
          f"{len(summary['groups'])} groups, {summary['seconds']}s -> {a.out}")
    print_groups(summary)
    return 0


def grouped(records) -> list[dict]:
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
    return sorted(groups.values(), key=lambda g: -g["count"])


def write_summary(path, summary):
    _os.makedirs(_os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(summary, f, indent=1)


def print_groups(summary):
    for g in summary["groups"]:
        r = g["repro"]
        src = f"log {r['log']}" if r.get("log") else f"seed {r['seed']}{' --biased' if r.get('biased') else ''}"
        print(f"{g['count']:5d}  {g['key']}\n       repro: {src} index {r['index']} action {r['action']}: {r['error'][:200]}")


if __name__ == "__main__":
    raise SystemExit(main())
