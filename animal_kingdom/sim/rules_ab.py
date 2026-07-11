"""A/B simulation harness for rule/config changes.

The first use case is the draw-action experiment: control = shipped ruleset
(`draw_action_count=1`), treatment = draw 2 cards per Draw action. Both arms run the same
full deck round-robin schedule with the same seed blocks, so deltas are attributable to the
config change rather than a different matchup schedule.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from typing import Optional, Sequence

from ..engine.cards import DECK_SLUGS
from ..engine.config import Config
from . import metrics
from .runner import BOT_KINDS, GameRecord, parse_bot_pair, run_pairs


@dataclass(frozen=True)
class Arm:
    name: str
    config: Config


@dataclass(frozen=True)
class DeckDelta:
    deck: str
    control_win_rate: Optional[float]
    treatment_win_rate: Optional[float]
    delta: Optional[float]


def _non_mirror_pairs(slugs: Sequence[str]) -> list[tuple[str, str]]:
    ordered = sorted(slugs)
    return [(a, b) for i, a in enumerate(ordered) for b in ordered[i + 1:]]


def _deck_field_rates(records: Sequence[GameRecord]) -> dict[str, float]:
    wins: dict[str, float] = {}
    games: dict[str, int] = {}
    for record in records:
        if record.deck_a == record.deck_b:
            continue
        for seat, deck in (("A", record.deck_a), ("B", record.deck_b)):
            games[deck] = games.get(deck, 0) + 1
            if record.winner is None:
                credit = 0.5
            else:
                credit = 1.0 if record.winner == seat else 0.0
            wins[deck] = wins.get(deck, 0.0) + credit
    return {deck: wins[deck] / games[deck] for deck in games}


def deck_deltas(
    control_records: Sequence[GameRecord],
    treatment_records: Sequence[GameRecord],
) -> list[DeckDelta]:
    control = _deck_field_rates(control_records)
    treatment = _deck_field_rates(treatment_records)
    decks = sorted(set(control) | set(treatment))
    rows = []
    for deck in decks:
        c = control.get(deck)
        t = treatment.get(deck)
        rows.append(DeckDelta(deck, c, t, None if c is None or t is None else t - c))
    rows.sort(key=lambda row: (row.delta is None, -(row.delta or 0.0), row.deck))
    return rows


def matchup_deltas(
    control_records: Sequence[GameRecord],
    treatment_records: Sequence[GameRecord],
) -> list[dict]:
    control = metrics.matchup_matrix(control_records)
    treatment = metrics.matchup_matrix(treatment_records)
    decks = sorted(set(control["decks"]) | set(treatment["decks"]))
    rows = []
    for a in decks:
        for b in decks:
            if a == b:
                continue
            c = control["win_rate"].get(a, {}).get(b)
            t = treatment["win_rate"].get(a, {}).get(b)
            rows.append({
                "deck_a": a,
                "deck_b": b,
                "control_win_rate": c,
                "treatment_win_rate": t,
                "delta": None if c is None or t is None else t - c,
            })
    rows.sort(key=lambda row: (row["delta"] is None, -(row["delta"] or 0.0),
                               row["deck_a"], row["deck_b"]))
    return rows


def _pct(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _signed_pct(value: Optional[float]) -> str:
    return "n/a" if value is None else f"{value:+.1%}"


def _crossed_progress_decile(done: int, total: int) -> bool:
    return total > 0 and (done * 10) // total > ((done - 1) * 10) // total


def _matchup_batch_summary(records: Sequence[GameRecord]) -> tuple[float, float, float]:
    total = len(records)
    if total == 0:
        return 0.0, 0.0, 0.0
    draws = sum(record.winner is None for record in records)
    a_credit = sum(record.winner == "A" for record in records) + draws / 2
    avg_turns = sum(record.turns for record in records) / total
    return a_credit / total, draws / total, avg_turns


def _write_deck_delta_csv(path: str, rows: Sequence[DeckDelta]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["deck", "control_win_rate", "treatment_win_rate", "delta"])
        for row in rows:
            writer.writerow([
                row.deck,
                "" if row.control_win_rate is None else f"{row.control_win_rate:.4f}",
                "" if row.treatment_win_rate is None else f"{row.treatment_win_rate:.4f}",
                "" if row.delta is None else f"{row.delta:.4f}",
            ])


def _write_matchup_delta_csv(path: str, rows: Sequence[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, [
            "deck_a",
            "deck_b",
            "control_win_rate",
            "treatment_win_rate",
            "delta",
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                key: (
                    "" if value is None else f"{value:.4f}"
                ) if key.endswith("rate") or key == "delta"
                else value
                for key, value in row.items()
            })


def _arm_config_payload(arm: Arm) -> dict:
    return {"name": arm.name, "config": asdict(arm.config)}


def _summary_payload(
    *,
    control: Arm,
    treatment: Arm,
    control_records: Sequence[GameRecord],
    treatment_records: Sequence[GameRecord],
    deck_delta_rows: Sequence[DeckDelta],
    matchup_delta_rows: Sequence[dict],
    games_per_matchup: int,
    seed: int,
    bots: tuple[str, str],
    map_id: str,
) -> dict:
    control_first = metrics.first_player_win_rate(control_records)["rate"]
    treatment_first = metrics.first_player_win_rate(treatment_records)["rate"]
    control_length = metrics.avg_game_length(control_records)["overall"]
    treatment_length = metrics.avg_game_length(treatment_records)["overall"]
    return {
        "control": _arm_config_payload(control),
        "treatment": _arm_config_payload(treatment),
        "games_per_matchup": games_per_matchup,
        "seed": seed,
        "bots": list(bots),
        "map": map_id,
        "games_per_arm": {
            "control": len(control_records),
            "treatment": len(treatment_records),
        },
        "first_player_win_rate": {
            "control": control_first,
            "treatment": treatment_first,
            "delta": (
                None if control_first is None or treatment_first is None
                else treatment_first - control_first
            ),
        },
        "avg_game_length": {
            "control": control_length,
            "treatment": treatment_length,
            "delta": (
                None if control_length is None or treatment_length is None
                else treatment_length - control_length
            ),
        },
        "win_condition_split": {
            "control": metrics.win_condition_split(control_records),
            "treatment": metrics.win_condition_split(treatment_records),
        },
        "deck_deltas": [asdict(row) for row in deck_delta_rows],
        "matchup_deltas": matchup_delta_rows,
    }


def run_ab(
    games_per_matchup: int,
    *,
    seed: int = 0,
    bots: tuple[str, str] = ("greedy", "greedy"),
    map_id: str = "map_b",
    jobs: int = 1,
    control: Arm | None = None,
    treatment: Arm | None = None,
    slugs: Sequence[str] = DECK_SLUGS,
) -> tuple[list[GameRecord], list[GameRecord]]:
    if games_per_matchup <= 0:
        raise ValueError("games_per_matchup must be positive")
    control = control or Arm("control_draw1", Config.default())
    treatment = treatment or Arm(
        "treatment_draw2",
        Config.default().sweep(draw_action_count=2),
    )
    pairs = _non_mirror_pairs(slugs)
    control_records = run_pairs(
        pairs,
        games_per_matchup,
        seed,
        bots=bots,
        config=control.config,
        map_id=map_id,
        jobs=jobs,
    )
    treatment_records = run_pairs(
        pairs,
        games_per_matchup,
        seed,
        bots=bots,
        config=treatment.config,
        map_id=map_id,
        jobs=jobs,
    )
    return control_records, treatment_records


def write_ab_artifacts(
    out_dir: str,
    *,
    control: Arm,
    treatment: Arm,
    control_records: Sequence[GameRecord],
    treatment_records: Sequence[GameRecord],
    games_per_matchup: int,
    seed: int,
    bots: tuple[str, str],
    map_id: str,
) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    metrics.write_all(control_records, os.path.join(out_dir, control.name))
    metrics.write_all(treatment_records, os.path.join(out_dir, treatment.name))
    deck_delta_rows = deck_deltas(control_records, treatment_records)
    matchup_delta_rows = matchup_deltas(control_records, treatment_records)
    _write_deck_delta_csv(os.path.join(out_dir, "deck_delta.csv"), deck_delta_rows)
    _write_matchup_delta_csv(os.path.join(out_dir, "matchup_delta.csv"), matchup_delta_rows)
    summary = _summary_payload(
        control=control,
        treatment=treatment,
        control_records=control_records,
        treatment_records=treatment_records,
        deck_delta_rows=deck_delta_rows,
        matchup_delta_rows=matchup_delta_rows,
        games_per_matchup=games_per_matchup,
        seed=seed,
        bots=bots,
        map_id=map_id,
    )
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def format_ab_summary(summary: dict, *, max_decks: int = 10) -> str:
    first = summary["first_player_win_rate"]
    length = summary["avg_game_length"]
    treatment_label = f"draw{summary['treatment']['config']['draw_action_count']}"
    lines = [
        "### Rule A/B summary",
        (
            f"control={summary['control']['name']} "
            f"(draw_action_count={summary['control']['config']['draw_action_count']}), "
            f"treatment={summary['treatment']['name']} "
            f"(draw_action_count={summary['treatment']['config']['draw_action_count']})"
        ),
        (
            f"games/arm={summary['games_per_arm']['control']}, "
            f"bots={','.join(summary['bots'])}, seed={summary['seed']}, map={summary['map']}"
        ),
        "",
        (
            "First-player WR: "
            f"{_pct(first['control'])} -> {_pct(first['treatment'])} "
            f"({_signed_pct(first['delta'])})"
        ),
        (
            "Avg length: "
            f"{length['control']:.1f} -> {length['treatment']:.1f} turns "
            f"({length['delta']:+.1f})"
        ),
        "",
        "Top deck field-WR deltas:",
        "```",
        f"{'deck':<22}{'control':>10}{treatment_label:>10}{'delta':>10}",
    ]
    for row in summary["deck_deltas"][:max_decks]:
        lines.append(
            f"{row['deck']:<22}"
            f"{_pct(row['control_win_rate']):>10}"
            f"{_pct(row['treatment_win_rate']):>10}"
            f"{_signed_pct(row['delta']):>10}"
        )
    lines.append("```")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Run a paired full-matrix rules A/B simulation.")
    parser.add_argument("games", type=int, help="games per non-mirror matchup per arm")
    parser.add_argument("--seed", type=int, default=0, help="base seed")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--bots", default="greedy,greedy",
                        help=f"two of {'|'.join(BOT_KINDS)} (default greedy,greedy)")
    parser.add_argument("--map", dest="map_id", default="map_b")
    parser.add_argument("--out", default="results/rules_ab/draw2",
                        help="output directory for both arms and comparison files")
    parser.add_argument("--treatment-draw-count", type=int, default=2,
                        help="draw_action_count for treatment arm (default 2)")
    args = parser.parse_args(argv)

    if args.games <= 0:
        parser.error("games must be positive")
    bots = parse_bot_pair(args.bots)
    control = Arm("control_draw1", Config.default())
    treatment = Arm(
        f"treatment_draw{args.treatment_draw_count}",
        Config.default().sweep(draw_action_count=args.treatment_draw_count),
    )
    pairs = _non_mirror_pairs(DECK_SLUGS)
    total_per_arm = len(pairs) * args.games * 2
    print(
        f"Running paired rules A/B over {len(pairs)} matchups "
        f"({total_per_arm} games/arm, bots={bots[0]},{bots[1]}, jobs={args.jobs})...",
        file=sys.stderr,
        flush=True,
    )
    start = time.monotonic()

    def _run_logged_arm(arm: Arm, arm_index: int) -> list[GameRecord]:
        games_done_total = 0
        print(
            f"\n[{arm_index}/2] Starting {arm.name} "
            f"(draw_action_count={arm.config.draw_action_count})",
            file=sys.stderr,
            flush=True,
        )

        def _game_progress(a: str, b: str, done: int, matchup_games: int) -> None:
            if not _crossed_progress_decile(done, matchup_games):
                return
            elapsed = time.monotonic() - start
            games_done = games_done_total + done
            print(
                f"      [{arm.name} {done / matchup_games:>4.0%}] {a} vs {b} | "
                f"{done}/{matchup_games} games in matchup | "
                f"{games_done}/{total_per_arm} arm games | {elapsed:.1f}s",
                file=sys.stderr,
                flush=True,
            )

        def _matchup_progress(
            a: str,
            b: str,
            done: int,
            matchup_total: int,
            batch: list[GameRecord],
        ) -> None:
            nonlocal games_done_total
            games_done_total += len(batch)
            a_rate, draw_rate, avg_turns = _matchup_batch_summary(batch)
            elapsed = time.monotonic() - start
            print(
                f"  [{arm.name}] matchup {done}/{matchup_total} complete: {a} vs {b} | "
                f"WR A={a_rate:.1%}, draws={draw_rate:.1%}, avg_turns={avg_turns:.1f} | "
                f"{games_done_total}/{total_per_arm} arm games | {elapsed:.1f}s",
                file=sys.stderr,
                flush=True,
            )

        records = run_pairs(
            pairs,
            args.games,
            args.seed,
            bots=bots,
            config=arm.config,
            map_id=args.map_id,
            jobs=args.jobs,
            game_progress=_game_progress,
            matchup_progress=_matchup_progress,
        )
        print(
            f"[{arm_index}/2] Finished {arm.name}: {len(records)} games",
            file=sys.stderr,
            flush=True,
        )
        return records

    control_records = _run_logged_arm(control, 1)
    treatment_records = _run_logged_arm(treatment, 2)
    summary = write_ab_artifacts(
        args.out,
        control=control,
        treatment=treatment,
        control_records=control_records,
        treatment_records=treatment_records,
        games_per_matchup=args.games,
        seed=args.seed,
        bots=bots,
        map_id=args.map_id,
    )
    print(f"Simulation done in {time.monotonic() - start:.1f}s.", file=sys.stderr)
    print(f"Wrote A/B artifacts to {args.out}", file=sys.stderr)
    print(format_ab_summary(summary))


if __name__ == "__main__":
    main(sys.argv[1:])
