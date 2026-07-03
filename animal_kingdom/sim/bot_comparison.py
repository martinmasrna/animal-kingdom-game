"""Paired bot-quality benchmark: is the candidate pilot actually better, per deck?

`sim/gauntlet.py` answers "does this deck's candidate bot beat a pinned pool" as one blended
win rate. That is too coarse for the TurnBot decision (handoff §4): "TurnBot is better" must
hold *for each candidate deck separately*, with evidence rather than noise. This module runs
the paired design:

    baseline:  GreedyBot(D) vs GreedyBot(O)
    candidate: TurnBot(D)   vs GreedyBot(O)

over every premade opponent `O` (including the mirror D vs D, which isolates pilot quality on
identical card pools). Both gauntlets use the *same* pairs order, base seed, and per-game seed
schedule (`runner.run_pairs` derives each game's seed from its position), so the two runs are
matched game-for-game. We join on `(opponent_deck, game_seed)` and work with **paired
per-game deltas** (candidate credit minus baseline credit), which cancels the shared variance
of the opponent/seed and gives a far tighter, honest confidence interval than comparing two
independent win-rate samples.

The interval is a deterministic paired bootstrap: resample the paired deltas (never the two
bot samples independently) with a fixed seed, so repeating a run reproduces the interval
byte-for-byte. `run_all` sweeps all seven decks and writes `summary.json`, `per_deck.csv`,
`per_opponent.csv`, and a terminal table under `results/bot_quality/turnbot/`, plus the
handoff §4.3 acceptance-gate verdicts (the ones measurable from the numbers).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from dataclasses import asdict, dataclass
from typing import Optional, Sequence

from ..engine.cards import DECK_SLUGS
from ..engine.config import Config, load_config_overrides
from . import metrics
from .gauntlet import _credit
from .runner import BOT_KINDS, GameRecord, parse_bot_kind, run_pairs

# Fixed bootstrap seed: repeating a benchmark reproduces the intervals exactly (handoff §4.3
# gate 6). Overridable for sensitivity checks, but never varies across a given run's cells.
DEFAULT_BOOTSTRAP_SEED = 0x7E570B07
DEFAULT_BOOTSTRAP_RESAMPLES = 10_000

# The handoff's pinned acceptance inputs (§4.1).
ACCEPTANCE_SEED = 683470156

MAX_MATCHUP_REGRESSION = 0.05   # gate 3: no opponent cell may drop by more than 5 points


# --------------------------------------------------------------------- paired bootstrap

def paired_bootstrap_ci(
    deltas: Sequence[float],
    *,
    resamples: int,
    seed,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Deterministic percentile bootstrap 95% CI for the mean of paired per-game deltas.

    Resamples the *deltas* themselves (paired), never the two bot samples independently, so
    the shared opponent/seed variance stays cancelled. `seed` is combined with nothing else -
    callers pass a per-cell seed so cell order can't change any interval.
    """
    n = len(deltas)
    if n == 0:
        return (0.0, 0.0)
    # random.Random accepts only scalar seeds; render the per-cell tuple to a stable string
    # so distinct cells (deck / deck+opponent) get independent yet reproducible streams.
    rng = random.Random(seed if isinstance(seed, (int, str)) else repr(seed))
    data = list(deltas)
    means = []
    for _ in range(resamples):
        sample = rng.choices(data, k=n)
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(round((alpha / 2) * (resamples - 1)))]
    hi = means[int(round((1 - alpha / 2) * (resamples - 1)))]
    return (lo, hi)


# ------------------------------------------------------------------------- result type

@dataclass(frozen=True)
class BotComparisonResult:
    # identifiers / provenance
    deck: str
    opponent_pool: tuple[str, ...]
    games_per_opponent: int
    base_seed: int
    seed_range: tuple[int, int]
    baseline_kind: str
    candidate_kind: str
    opponent_kind: str
    map_id: str
    config_id: Optional[str]
    bootstrap_resamples: int
    bootstrap_seed: int
    n_games_total: int

    # headline paired stats
    baseline_win_rate: float
    candidate_win_rate: float
    paired_delta: float
    delta_ci95: tuple[float, float]

    # per opponent (opp -> {baseline_win_rate, candidate_win_rate, paired_delta, delta_ci95, games})
    per_opponent: dict

    # descriptive splits
    candidate_record: dict          # {"wins", "losses", "draws"}
    baseline_record: dict
    candidate_win_conditions: dict
    baseline_win_conditions: dict
    avg_game_length: dict           # {"baseline", "candidate"}
    final_food: dict                # {"baseline": {...}, "candidate": {...}}
    runtime: dict                   # {"baseline_s","candidate_s","total_s","baseline_gps","candidate_gps","slowdown"}

    def mirror_win_rate(self) -> Optional[float]:
        cell = self.per_opponent.get(self.deck)
        return cell["candidate_win_rate"] if cell else None

    def worst_matchup(self) -> tuple[Optional[str], float]:
        """(opponent, paired_delta) for the opponent whose candidate delta is most negative."""
        if not self.per_opponent:
            return (None, 0.0)
        opp = min(self.per_opponent, key=lambda o: self.per_opponent[o]["paired_delta"])
        return (opp, self.per_opponent[opp]["paired_delta"])

    def to_dict(self) -> dict:
        d = asdict(self)
        d["opponent_pool"] = list(self.opponent_pool)
        d["seed_range"] = list(self.seed_range)
        d["delta_ci95"] = list(self.delta_ci95)
        for cell in d["per_opponent"].values():
            cell["delta_ci95"] = list(cell["delta_ci95"])
        d["mirror_win_rate"] = self.mirror_win_rate()
        worst_opp, worst_delta = self.worst_matchup()
        d["worst_matchup"] = {"opponent": worst_opp, "paired_delta": worst_delta}
        return d


# ------------------------------------------------------------------------- one deck

def _record_split(records: Sequence[GameRecord]) -> dict:
    """Seat-A win/loss/draw counts (seat A is always the candidate/baseline deck here)."""
    wins = sum(1 for r in records if r.winner == "A")
    losses = sum(1 for r in records if r.winner == "B")
    draws = sum(1 for r in records if r.winner is None)
    return {"wins": wins, "losses": losses, "draws": draws}


def run_bot_comparison(
    deck: str,
    opponent_pool: Sequence[str],
    n_games: int,
    base_seed: int,
    *,
    baseline_kind: str = "greedy",
    candidate_kind: str = "turn",
    opponent_kind: str = "greedy",
    config: Optional[Config] = None,
    map_id: str = "map_b",
    jobs: int = 1,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    config_id: Optional[str] = None,
) -> BotComparisonResult:
    """Run the paired baseline/candidate gauntlets for `deck` and return joined stats.

    `deck` pilots seat A in both runs; every `opponent_pool` deck (incl. the mirror) pilots
    seat B with `opponent_kind`. Both runs share the identical pairs order / `base_seed` /
    `n_games`, so `runner.run_pairs` hands them the same per-game seeds and the outcomes join
    game-for-game on `(opponent_deck, game_seed)`.
    """
    pool = tuple(opponent_pool)
    pairs = [(deck, opp) for opp in pool]

    t0 = time.monotonic()
    baseline_records = run_pairs(pairs, n_games, base_seed,
                                 bots=(baseline_kind, opponent_kind),
                                 config=config, map_id=map_id, jobs=jobs)
    t1 = time.monotonic()
    candidate_records = run_pairs(pairs, n_games, base_seed,
                                  bots=(candidate_kind, opponent_kind),
                                  config=config, map_id=map_id, jobs=jobs)
    t2 = time.monotonic()

    # Join on (opponent_deck, game_seed); deck_a is `deck` in every record of both runs.
    base_by_key = {(r.deck_b, r.seed): r for r in baseline_records}
    per_opp_deltas: dict[str, list[float]] = {opp: [] for opp in pool}
    per_opp_base: dict[str, list[float]] = {opp: [] for opp in pool}
    per_opp_cand: dict[str, list[float]] = {opp: [] for opp in pool}
    all_deltas: list[float] = []
    for r in candidate_records:
        base = base_by_key[(r.deck_b, r.seed)]
        cand_credit = _credit(r, "A")
        base_credit = _credit(base, "A")
        delta = cand_credit - base_credit
        all_deltas.append(delta)
        per_opp_deltas[r.deck_b].append(delta)
        per_opp_base[r.deck_b].append(base_credit)
        per_opp_cand[r.deck_b].append(cand_credit)

    per_opponent: dict[str, dict] = {}
    for opp in pool:
        deltas = per_opp_deltas[opp]
        per_opponent[opp] = {
            "games": len(deltas),
            "baseline_win_rate": sum(per_opp_base[opp]) / len(deltas) if deltas else None,
            "candidate_win_rate": sum(per_opp_cand[opp]) / len(deltas) if deltas else None,
            "paired_delta": sum(deltas) / len(deltas) if deltas else 0.0,
            "delta_ci95": paired_bootstrap_ci(
                deltas, resamples=bootstrap_resamples,
                seed=(bootstrap_seed, deck, opp)),
        }

    baseline_wr = sum(_credit(r, "A") for r in baseline_records) / len(baseline_records)
    candidate_wr = sum(_credit(r, "A") for r in candidate_records) / len(candidate_records)

    baseline_food = metrics.final_food_summary(baseline_records)
    candidate_food = metrics.final_food_summary(candidate_records)
    baseline_len = metrics.avg_game_length(baseline_records)["overall"]
    candidate_len = metrics.avg_game_length(candidate_records)["overall"]

    baseline_s = t1 - t0
    candidate_s = t2 - t1
    n_total = len(candidate_records)
    runtime = {
        "baseline_s": baseline_s,
        "candidate_s": candidate_s,
        "total_s": t2 - t0,
        "baseline_gps": n_total / baseline_s if baseline_s else None,
        "candidate_gps": n_total / candidate_s if candidate_s else None,
        "slowdown": candidate_s / baseline_s if baseline_s else None,
    }

    seed_range = (base_seed, base_seed + len(pairs) * n_games - 1)

    return BotComparisonResult(
        deck=deck,
        opponent_pool=pool,
        games_per_opponent=n_games,
        base_seed=base_seed,
        seed_range=seed_range,
        baseline_kind=baseline_kind,
        candidate_kind=candidate_kind,
        opponent_kind=opponent_kind,
        map_id=map_id,
        config_id=config_id,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        n_games_total=n_total,
        baseline_win_rate=baseline_wr,
        candidate_win_rate=candidate_wr,
        paired_delta=sum(all_deltas) / len(all_deltas) if all_deltas else 0.0,
        delta_ci95=paired_bootstrap_ci(
            all_deltas, resamples=bootstrap_resamples, seed=(bootstrap_seed, deck)),
        per_opponent=per_opponent,
        candidate_record=_record_split(candidate_records),
        baseline_record=_record_split(baseline_records),
        candidate_win_conditions=metrics.win_condition_split(candidate_records),
        baseline_win_conditions=metrics.win_condition_split(baseline_records),
        avg_game_length={"baseline": baseline_len, "candidate": candidate_len},
        final_food={"baseline": baseline_food, "candidate": candidate_food},
        runtime=runtime,
    )


# ------------------------------------------------------------------ acceptance gates

def evaluate_gates(results: dict[str, BotComparisonResult]) -> dict:
    """The handoff §4.3 acceptance gates that are measurable from the numbers.

    Gates 5 (no deck slugs in production code) and 6 (byte-equal reruns) are verified out of
    band - by inspection and by re-running - and reported separately; here we compute the
    per-deck quantitative gates plus throughput.
    """
    per_deck = {}
    for deck, r in results.items():
        lo, hi = r.delta_ci95
        _, worst_delta = r.worst_matchup()
        mirror = r.mirror_win_rate()
        per_deck[deck] = {
            "delta_positive": r.paired_delta > 0,
            "ci_above_zero": lo > 0,
            "no_matchup_collapse": worst_delta >= -MAX_MATCHUP_REGRESSION,
            "mirror_above_50": (mirror is not None and mirror > 0.5),
            "slowdown_within_10x": (r.runtime["slowdown"] is None
                                    or r.runtime["slowdown"] <= 10.0),
        }
    every_deck_improves = all(d["delta_positive"] for d in per_deck.values())
    evidence_not_noise = all(d["ci_above_zero"] for d in per_deck.values())
    no_hidden_collapse = all(d["no_matchup_collapse"] for d in per_deck.values())
    mirror_sanity = all(d["mirror_above_50"] for d in per_deck.values())
    throughput = all(d["slowdown_within_10x"] for d in per_deck.values())
    return {
        "per_deck": per_deck,
        "summary": {
            "every_deck_improves": every_deck_improves,
            "evidence_not_noise": evidence_not_noise,
            "no_hidden_collapse": no_hidden_collapse,
            "mirror_sanity": mirror_sanity,
            "throughput_within_10x": throughput,
            "all_measurable_gates_pass": all([
                every_deck_improves, evidence_not_noise,
                no_hidden_collapse, mirror_sanity, throughput,
            ]),
        },
        "manual_gates": {
            "generalist_no_deck_slugs": "verify by inspection of bots/turn_*.py",
            "determinism_byte_equal": "verify by re-running with the same seed",
        },
    }


# ------------------------------------------------------------------------- artifacts

def _write_per_deck_csv(path: str, results: dict[str, BotComparisonResult]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["deck", "baseline_wr", "candidate_wr", "paired_delta",
                    "ci_low", "ci_high", "mirror_wr", "worst_opponent",
                    "worst_opponent_delta", "slowdown"])
        for deck in sorted(results):
            r = results[deck]
            lo, hi = r.delta_ci95
            worst_opp, worst_delta = r.worst_matchup()
            w.writerow([
                deck, f"{r.baseline_win_rate:.4f}", f"{r.candidate_win_rate:.4f}",
                f"{r.paired_delta:+.4f}", f"{lo:+.4f}", f"{hi:+.4f}",
                "" if r.mirror_win_rate() is None else f"{r.mirror_win_rate():.4f}",
                worst_opp or "", f"{worst_delta:+.4f}",
                "" if r.runtime["slowdown"] is None else f"{r.runtime['slowdown']:.2f}",
            ])


def _write_per_opponent_csv(path: str, results: dict[str, BotComparisonResult]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["deck", "opponent", "games", "baseline_wr", "candidate_wr",
                    "paired_delta", "ci_low", "ci_high"])
        for deck in sorted(results):
            r = results[deck]
            for opp in sorted(r.per_opponent):
                cell = r.per_opponent[opp]
                lo, hi = cell["delta_ci95"]
                w.writerow([
                    deck, opp, cell["games"],
                    "" if cell["baseline_win_rate"] is None else f"{cell['baseline_win_rate']:.4f}",
                    "" if cell["candidate_win_rate"] is None else f"{cell['candidate_win_rate']:.4f}",
                    f"{cell['paired_delta']:+.4f}", f"{lo:+.4f}", f"{hi:+.4f}",
                ])


def format_table(results: dict[str, BotComparisonResult], gates: dict) -> str:
    lines = [
        "",
        f"{'deck':<20}{'greedy':>8}{'turn':>8}{'delta':>9}"
        f"{'95% CI':>18}{'mirror':>8}{'worst opp':>22}{'slow':>7}  gates",
    ]
    for deck in sorted(results):
        r = results[deck]
        lo, hi = r.delta_ci95
        worst_opp, worst_delta = r.worst_matchup()
        mirror = r.mirror_win_rate()
        g = gates["per_deck"][deck]
        flags = "".join([
            "D" if g["delta_positive"] else "d",
            "C" if g["ci_above_zero"] else "c",
            "R" if g["no_matchup_collapse"] else "r",
            "M" if g["mirror_above_50"] else "m",
            "T" if g["slowdown_within_10x"] else "t",
        ])
        slow = r.runtime["slowdown"]
        lines.append(
            f"{deck:<20}{r.baseline_win_rate:>7.1%} {r.candidate_win_rate:>7.1%} "
            f"{r.paired_delta:>+8.1%} [{lo:>+6.1%},{hi:>+6.1%}] "
            f"{'n/a' if mirror is None else f'{mirror:>6.1%}':>7} "
            f"{(worst_opp or '-') + f' {worst_delta:+.0%}':>21} "
            f"{'n/a' if slow is None else f'{slow:.1f}x':>6}  {flags}"
        )
    s = gates["summary"]
    lines += [
        "",
        "gate flags (upper = pass): D delta>0  C CI>0  R no >5pt drop  "
        "M mirror>50%  T slowdown<=10x",
        f"all measurable gates pass: {s['all_measurable_gates_pass']}  "
        f"(every_deck_improves={s['every_deck_improves']}, "
        f"evidence_not_noise={s['evidence_not_noise']}, "
        f"no_hidden_collapse={s['no_hidden_collapse']}, "
        f"mirror_sanity={s['mirror_sanity']}, throughput={s['throughput_within_10x']})",
        "manual gates: generalist (no deck slugs) + determinism (byte-equal rerun) "
        "verified out of band.",
    ]
    return "\n".join(lines)


def run_all(
    n_games: int,
    base_seed: int,
    *,
    baseline_kind: str = "greedy",
    candidate_kind: str = "turn",
    opponent_kind: str = "greedy",
    config: Optional[Config] = None,
    map_id: str = "map_b",
    jobs: int = 1,
    config_id: Optional[str] = None,
    out_dir: str = "results/bot_quality/turnbot",
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    progress=None,
) -> dict[str, BotComparisonResult]:
    """Run the paired benchmark for all seven premade decks and write the artifact bundle."""
    decks = sorted(DECK_SLUGS)
    pool = decks  # every premade opponent, including the mirror (handoff §4.1)
    results: dict[str, BotComparisonResult] = {}
    for i, deck in enumerate(decks):
        results[deck] = run_bot_comparison(
            deck, pool, n_games, base_seed,
            baseline_kind=baseline_kind, candidate_kind=candidate_kind,
            opponent_kind=opponent_kind, config=config, map_id=map_id, jobs=jobs,
            bootstrap_resamples=bootstrap_resamples, bootstrap_seed=bootstrap_seed,
            config_id=config_id)
        if progress is not None:
            progress(deck, i + 1, len(decks))

    gates = evaluate_gates(results)
    os.makedirs(out_dir, exist_ok=True)
    summary = {
        "meta": {
            "games_per_opponent": n_games,
            "base_seed": base_seed,
            "decks": decks,
            "opponent_pool": pool,
            "baseline_kind": baseline_kind,
            "candidate_kind": candidate_kind,
            "opponent_kind": opponent_kind,
            "map_id": map_id,
            "config": config_id,
            "bootstrap_resamples": bootstrap_resamples,
            "bootstrap_seed": bootstrap_seed,
        },
        "per_deck": {deck: r.to_dict() for deck, r in results.items()},
        "gates": gates,
        "caveat": metrics.GREEDY_CAVEAT,
    }
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    _write_per_deck_csv(os.path.join(out_dir, "per_deck.csv"), results)
    _write_per_opponent_csv(os.path.join(out_dir, "per_opponent.csv"), results)
    return results


# ------------------------------------------------------------------------------- CLI

def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Paired seven-deck bot-quality benchmark (baseline vs candidate pilot).")
    p.add_argument("--games", type=int, default=200,
                   help="games per opponent (smoke 20 / acceptance 200 / resolve 500|1000)")
    p.add_argument("--seed", type=int, default=ACCEPTANCE_SEED, help="base seed")
    p.add_argument("--candidate-kind", default="turn",
                   help=f"one of {'|'.join(BOT_KINDS)} (default turn)")
    p.add_argument("--baseline-kind", default="greedy",
                   help=f"one of {'|'.join(BOT_KINDS)} (default greedy)")
    p.add_argument("--opponent-kind", default="greedy",
                   help=f"one of {'|'.join(BOT_KINDS)} (default greedy)")
    p.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes")
    p.add_argument("--map", dest="map_id", default="map_b")
    p.add_argument("--config", default=None,
                   help="JSON file of Config field overrides; 'none' clears a wrapper preset")
    p.add_argument("--deck", default=None,
                   help="only benchmark this one candidate deck (default: all seven)")
    p.add_argument("--out", default="results/bot_quality/turnbot",
                   help="artifact output directory")
    p.add_argument("--bootstrap-resamples", type=int, default=DEFAULT_BOOTSTRAP_RESAMPLES)
    p.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    args = p.parse_args(argv)

    config = load_config_overrides(args.config)
    candidate_kind = parse_bot_kind(args.candidate_kind, "--candidate-kind")
    baseline_kind = parse_bot_kind(args.baseline_kind, "--baseline-kind")
    opponent_kind = parse_bot_kind(args.opponent_kind, "--opponent-kind")

    decks = sorted(DECK_SLUGS)
    if args.deck is not None:
        target = args.deck.strip().lower()
        if target not in DECK_SLUGS:
            raise SystemExit(f"--deck {target!r} not in {sorted(DECK_SLUGS)}")
        decks = [target]

    total = len(decks)
    start = time.monotonic()
    print(f"Paired benchmark: {baseline_kind} vs {candidate_kind} on {total} deck(s), "
          f"{args.games} games/opponent x 7 opponents, map={args.map_id}, "
          f"jobs={args.jobs}, seed={args.seed}...", file=sys.stderr)

    def _progress(deck: str, done: int, deck_total: int) -> None:
        elapsed = time.monotonic() - start
        print(f"  [{done}/{deck_total}] {elapsed:6.1f}s  {deck} done", file=sys.stderr)

    # run_all always sweeps DECK_SLUGS; for a single --deck we still want the full opponent
    # pool (incl. mirror), so reuse run_bot_comparison directly there.
    if len(decks) == len(DECK_SLUGS):
        results = run_all(
            args.games, args.seed,
            baseline_kind=baseline_kind, candidate_kind=candidate_kind,
            opponent_kind=opponent_kind, config=config, map_id=args.map_id, jobs=args.jobs,
            config_id=args.config, out_dir=args.out,
            bootstrap_resamples=args.bootstrap_resamples,
            bootstrap_seed=args.bootstrap_seed, progress=_progress)
    else:
        pool = sorted(DECK_SLUGS)
        results = {}
        for i, deck in enumerate(decks):
            results[deck] = run_bot_comparison(
                deck, pool, args.games, args.seed,
                baseline_kind=baseline_kind, candidate_kind=candidate_kind,
                opponent_kind=opponent_kind, config=config, map_id=args.map_id,
                jobs=args.jobs, bootstrap_resamples=args.bootstrap_resamples,
                bootstrap_seed=args.bootstrap_seed, config_id=args.config)
            _progress(deck, i + 1, len(decks))

    gates = evaluate_gates(results)
    print(f"\nDone in {time.monotonic() - start:.1f}s.", file=sys.stderr)
    print(format_table(results, gates))
    if len(decks) == len(DECK_SLUGS):
        print(f"\nArtifacts written to {args.out}/ "
              "(summary.json, per_deck.csv, per_opponent.csv)")


if __name__ == "__main__":
    main(sys.argv[1:])
