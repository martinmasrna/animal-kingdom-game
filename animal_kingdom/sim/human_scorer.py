"""Score bots against recorded human decisions (offline divergence read).

The lean instrument behind the human-benchmark work: for every *human* decision in a
recorded game, reconstruct the exact position the human faced and ask each bot "what would
you do here?", then measure how often the bot's top choice matches the human's. Sliced by
the human's deck and compared across bots, this shows whether more search closes the human
gap (a fixable execution shortfall) or leaves it open (a structural blind spot).

Honesty invariant: the bot decides from `state.view_for(actor)` — the same hidden-info-
stripped view it gets in real play — never the omniscient logged state. The full state is
passed only as the in-process search escape hatch, exactly as the sim runner does.

This is a navigation aid, not statistics: top-1 agreement is a crude metric (near-ties count
as disagreements), so read the cross-bot *contrasts* per deck, not absolute levels. A free
bot-vs-bot agreement baseline on the identical positions calibrates how much of the gap is
just near-tie noise.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import glob
import itertools
import json
from collections import defaultdict
from pathlib import Path
from typing import Iterator, Sequence

from ..bots.greedy_bot import GreedyWeights, _battlecry_fizzled, evaluate
from ..engine import rules
from ..engine.actions import Action, action_from_dict
from ..engine.config import Config
from ..engine.state import GameState
from .runner import BOT_KINDS, make_bot


@dataclasses.dataclass(frozen=True)
class HumanDecision:
    """One replayable human decision point, keyed to the human's deck for slicing."""

    game_id: str
    human_deck: str
    opponent_deck: str
    decision_id: int
    turn: int
    actor: str
    action: dict          # the human's chosen action, as logged (Action.to_dict shape)
    state: dict           # full GameState.to_dict at the decision point
    config: Config


def _config_from_meta(meta: dict) -> Config:
    """Reconstruct the game's Config from meta provenance, defaulting where absent."""
    cfg = (meta.get("provenance") or {}).get("config") or {}
    valid = {f.name for f in dataclasses.fields(Config)}
    return dataclasses.replace(Config.default(), **{k: v for k, v in cfg.items() if k in valid})


def iter_human_decisions(paths: Sequence[str]) -> Iterator[HumanDecision]:
    """Yield every human decision from completed games in the given jsonl logs."""
    for path in paths:
        meta = None
        completed = False
        decisions: list[dict] = []
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            kind = rec.get("type")
            if kind == "meta":
                meta = rec
            elif kind == "result":
                completed = True
            elif kind == "decision" and rec.get("human"):
                decisions.append(rec)
        if meta is None or not completed:
            continue  # skip aborted / in-progress games
        seat = meta["human_seat"]
        opp = "B" if seat == "A" else "A"
        config = _config_from_meta(meta)
        for rec in decisions:
            yield HumanDecision(
                game_id=meta["game_id"],
                human_deck=meta["decks"][seat],
                opponent_deck=meta["decks"][opp],
                decision_id=rec["decision_id"],
                turn=rec.get("state", {}).get("turn_counter", -1),
                actor=rec["actor"],
                action=rec["action"],
                state=rec["state"],
                config=config,
            )


def _bot_action(kind: str, dec: HumanDecision, legal: list[Action], state: GameState) -> dict:
    """Ask a fresh, deterministically-seeded bot what it would play at this decision."""
    # Fresh instance per decision: search bots (referee/turn) stage multi-action plans on
    # self, so reusing an instance across non-consecutive positions would leak stale state.
    bot = make_bot(kind, seed=dec.decision_id)
    action = bot.choose(state.view_for(dec.actor), legal, state)
    return action.to_dict()


def _greedy_scores(state: GameState, me: str, legal: list[Action],
                   weights: GreedyWeights) -> list[float]:
    """GreedyBot's depth-1 valuation of each legal action, from `me`'s perspective.

    Faithful to GreedyBot.choose's per-action score (evaluate(state-after-action) with the
    wasted-battlecry penalty), minus the lethal-avoidance hard override — we want the eval's
    *opinion* of a move, not the safety veto. This is the "hand-written judgement" the
    blind-spot thesis is about; search only amplifies it, so probing the eval is the point.
    """
    scores = []
    for action in legal:
        nxt = state.clone()
        rules.apply_action(nxt, action)
        s = evaluate(nxt, me, weights)
        if _battlecry_fizzled(state, nxt, me, action):
            s -= weights.wasted_battlecry
        scores.append(s)
    return scores


def _value_rank(scores: list[float], idx: int) -> float:
    """Fraction of legal moves the eval scores STRICTLY better than move `idx`.

    0.0 = the eval's own top pick; →1.0 = the eval thinks it's among the worst available.
    Branching- and scale-immune: this is a within-decision percentile, not a raw gap.
    """
    if len(scores) <= 1:
        return 0.0
    mine = scores[idx]
    better = sum(1 for s in scores if s > mine)
    return better / (len(scores) - 1)


@dataclasses.dataclass
class _Tally:
    n: int = 0
    agree: int = 0

    def add(self, hit: bool) -> None:
        self.n += 1
        self.agree += int(hit)

    @property
    def rate(self) -> float:
        return self.agree / self.n if self.n else float("nan")


def score(
    paths: Sequence[str],
    bot_kinds: Sequence[str],
    *,
    decks: Sequence[str] | None = None,
) -> dict:
    """Replay human decisions; return per-deck top-1 agreement per bot + bot-vs-bot baseline.

    Also reports place-only agreement (draws are often forced and inflate the raw rate) and
    an `unscored` count for decisions whose reconstruction couldn't reproduce the human's
    legal action (a reconstruction-fidelity canary).
    """
    deck_filter = set(decks) if decks else None
    weights = GreedyWeights()
    # per (deck, bot) -> Tally, and place-only variant
    agree: dict = defaultdict(_Tally)
    agree_place: dict = defaultdict(_Tally)
    # bot-vs-bot pairwise agreement on identical positions (consensus baseline)
    pair: dict = defaultdict(_Tally)
    # per deck -> list of value-ranks of the human's move (placements only), by greedy's eval
    value: dict = defaultdict(list)
    unscored = 0
    n_games: set = set()

    for dec in iter_human_decisions(paths):
        if deck_filter and dec.human_deck not in deck_filter:
            continue
        state = GameState.from_dict(dec.state, config=dec.config)
        legal = rules.legal_actions(state)
        legal_dicts = [a.to_dict() for a in legal]
        if dec.action not in legal_dicts:
            unscored += 1  # reconstruction couldn't reproduce the human's move; skip
            continue
        n_games.add(dec.game_id)
        is_place = dec.action.get("kind") == "place"
        # Value-rank: where greedy's evaluator ranks the human's actual move (placements).
        if is_place:
            scores = _greedy_scores(state, dec.actor, legal, weights)
            vr = _value_rank(scores, legal_dicts.index(dec.action))
            value[dec.human_deck].append(vr)
            value["ALL"].append(vr)
        choices: dict[str, dict] = {}
        for kind in bot_kinds:
            choices[kind] = _bot_action(kind, dec, legal, state)
            hit = choices[kind] == dec.action
            agree[(dec.human_deck, kind)].add(hit)
            agree[("ALL", kind)].add(hit)
            if is_place:
                agree_place[(dec.human_deck, kind)].add(hit)
                agree_place[("ALL", kind)].add(hit)
        for a, b in itertools.combinations(bot_kinds, 2):
            pair[("ALL", f"{a}~{b}")].add(choices[a] == choices[b])

    return {
        "bot_kinds": list(bot_kinds),
        "n_games": len(n_games),
        "unscored": unscored,
        "agree": agree,
        "agree_place": agree_place,
        "pair": pair,
        "value": value,
    }


def _print_report(result: dict) -> None:
    bots = result["bot_kinds"]
    agree, agree_place = result["agree"], result["agree_place"]
    decks = sorted({d for (d, _), t in agree.items() if d != "ALL"})
    order = decks + ["ALL"]

    def cell(table, deck, kind):
        t = table.get((deck, kind))
        return f"{t.rate * 100:5.1f}% ({t.agree:>3}/{t.n:<3})" if t and t.n else "    -       "

    print(f"\nHuman-decision agreement — {result['n_games']} games, "
          f"unscored(reconstruction miss): {result['unscored']}")
    print("Read the per-deck CONTRASTS across bots, not absolute levels (top-1 is crude).\n")
    header = f"{'human_deck':20} " + " ".join(f"{k:^15}" for k in bots)
    print(header)
    print("-" * len(header))
    for deck in order:
        row = f"{deck:20} " + " ".join(cell(agree, deck, k) for k in bots)
        print(row)
    print("\n(placements only — the strategic decisions; draws excluded)")
    for deck in order:
        row = f"{deck:20} " + " ".join(cell(agree_place, deck, k) for k in bots)
        print(row)
    if result["pair"]:
        print("\nBot-vs-bot agreement on the SAME positions (near-tie/consensus baseline):")
        for (deck, pairname), t in result["pair"].items():
            print(f"  {pairname:24} {t.rate * 100:5.1f}% ({t.agree}/{t.n})")

    _print_value_report(result["value"])


def _median(xs: list[float]) -> float:
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return float("nan")
    mid = n // 2
    return xs[mid] if n % 2 else (xs[mid - 1] + xs[mid]) / 2


def _print_value_report(value: dict) -> None:
    """Where GreedyBot's EVALUATOR ranks your actual placements (0=its top pick, 1=worst).

    This is the sharp, confound-free test: a real blind spot shows as a HIGH value-rank on a
    deck you WIN with — the eval systematically rates your winning moves near the bottom.
    """
    print("\nValue-rank of YOUR placements under greedy's evaluator "
          "(0.0 = its top pick, 1.0 = worst):")
    print(f"{'human_deck':20} {'median':>8} {'mean':>8} {'%your-move-is-its-top':>22} "
          f"{'%bottom-quartile':>18} {'n':>5}")
    decks = sorted(d for d in value if d != "ALL")
    for deck in decks + ["ALL"]:
        xs = value.get(deck, [])
        if not xs:
            continue
        top = sum(1 for v in xs if v == 0.0) / len(xs)
        bottom = sum(1 for v in xs if v >= 0.75) / len(xs)
        print(f"{deck:20} {_median(xs):8.2f} {sum(xs) / len(xs):8.2f} "
              f"{top * 100:21.1f}% {bottom * 100:17.1f}% {len(xs):5}")


def _write_csv(result: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "human_deck", "bot", "agree", "n", "rate"])
        for label, table in (("all", result["agree"]), ("place_only", result["agree_place"])):
            for (deck, kind), t in sorted(table.items()):
                w.writerow([label, deck, kind, t.agree, t.n, f"{t.rate:.4f}"])


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Score bots against recorded human decisions.")
    parser.add_argument("--games", default="results/human_games/session1/*.jsonl",
                        help="Glob of recorded human-game jsonl logs.")
    parser.add_argument("--bots", default="greedy,turn,referee",
                        help=f"Comma-separated bot kinds from {BOT_KINDS}.")
    parser.add_argument("--decks", default=None,
                        help="Comma-separated human decks to scope to (default: all).")
    parser.add_argument("--out", type=Path, default=Path("results/human_games/scores/agreement.csv"))
    args = parser.parse_args(argv)

    paths = sorted(glob.glob(args.games))
    if not paths:
        parser.error(f"no logs matched {args.games!r}")
    bot_kinds = [k.strip() for k in args.bots.split(",") if k.strip()]
    unknown = [k for k in bot_kinds if k not in BOT_KINDS]
    if unknown:
        parser.error(f"unknown bot kind(s) {unknown}; expected from {BOT_KINDS}")
    decks = [d.strip() for d in args.decks.split(",")] if args.decks else None

    result = score(paths, bot_kinds, decks=decks)
    _print_report(result)
    _write_csv(result, args.out)
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
