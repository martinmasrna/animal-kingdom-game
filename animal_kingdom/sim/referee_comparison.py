"""Fixed-position convergence benchmark for legacy versus staged Referee search.

This is deliberately a decision benchmark, not a strength verdict. It answers whether a
faster search configuration chooses the same actions as the full legacy algorithm across
reproducible public positions, and measures CPU time plus reply/node budgets. Behavior-
changing candidates still require paired game validation under the balance-eval method.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

from ..bots.random_bot import RandomBot
from ..bots.referee_bot import RefereeBot
from ..decks import load_premade_deck
from ..engine import rules
from ..engine.cards import DECK_SLUGS
from ..engine.config import Config, load_config_overrides
from ..engine.state import GameState, new_game
from .bot_comparison import DEFAULT_BOOTSTRAP_SEED, paired_bootstrap_ci
from .ratings import build_provenance
from .runner import make_bot, play_game


@dataclass(frozen=True)
class DecisionPosition:
    label: str
    state: GameState


@dataclass(frozen=True)
class RefereeMatchSpec:
    deck: str
    seed: int
    candidate_seat: str
    map_id: str


def _run_referee_match(
    spec: RefereeMatchSpec,
    config: Optional[Config],
) -> tuple[int, str, float, int]:
    candidate_seed = spec.seed * 2 + (1 if spec.candidate_seat == "A" else 2)
    legacy_seed = spec.seed * 2 + (2 if spec.candidate_seat == "A" else 1)
    candidate = make_bot("referee", candidate_seed)
    legacy = RefereeBot(
        seed=legacy_seed,
        staged=False,
        max_search_nodes=None,
    )
    bot_a, bot_b = (
        (candidate, legacy)
        if spec.candidate_seat == "A"
        else (legacy, candidate)
    )
    record = play_game(
        spec.deck,
        spec.deck,
        spec.seed,
        bot_a=bot_a,
        bot_b=bot_b,
        config=config,
        map_id=spec.map_id,
    )
    credit = (
        0.5 if record.winner is None
        else float(record.winner == spec.candidate_seat)
    )
    return spec.seed, spec.candidate_seat, credit, record.turns


def run_mirror_strength_comparison(
    deck: str,
    *,
    paired_seeds: int,
    base_seed: int,
    config: Optional[Config],
    map_id: str,
    jobs: int,
    bootstrap_resamples: int = 2_000,
    progress: Optional[Callable[[int, int], None]] = None,
) -> dict:
    """Paired-seat mirror cross-play: staged candidate versus full legacy Referee."""
    specs = [
        RefereeMatchSpec(deck, base_seed + offset, seat, map_id)
        for offset in range(paired_seeds)
        for seat in ("A", "B")
    ]
    start = time.monotonic()
    if jobs <= 1:
        outcomes = []
        for spec in specs:
            outcomes.append(_run_referee_match(spec, config))
            if progress is not None:
                progress(len(outcomes), len(specs))
    else:
        outcomes_by_index = {}
        with ProcessPoolExecutor(max_workers=jobs) as executor:
            futures = {
                executor.submit(_run_referee_match, spec, config): index
                for index, spec in enumerate(specs)
            }
            for done, future in enumerate(as_completed(futures), start=1):
                outcomes_by_index[futures[future]] = future.result()
                if progress is not None:
                    progress(done, len(specs))
        outcomes = [
            outcomes_by_index[index] for index in range(len(specs))
        ]
    elapsed = time.monotonic() - start
    pair_credits = []
    for index in range(0, len(outcomes), 2):
        pair = outcomes[index:index + 2]
        if pair[0][0] != pair[1][0] or {pair[0][1], pair[1][1]} != {"A", "B"}:
            raise RuntimeError("paired Referee outcomes lost schedule alignment")
        pair_credits.append((pair[0][2] + pair[1][2]) / 2.0)
    ci = paired_bootstrap_ci(
        pair_credits,
        resamples=bootstrap_resamples,
        seed=(DEFAULT_BOOTSTRAP_SEED, deck, base_seed),
    )
    ratings_provenance = build_provenance(
        pilots=("referee",),
        decks=(deck,),
        games_per_config=paired_seeds,
        base_seed=base_seed,
        map_id=map_id,
        config=config,
        config_id=None,
    )
    return {
        "schema_version": 1,
        "deck": deck,
        "games": len(outcomes),
        "paired_seeds": paired_seeds,
        "base_seed": base_seed,
        "map": map_id,
        "candidate_win_rate": sum(pair_credits) / len(pair_credits),
        "ci95": ci,
        "elapsed_s": elapsed,
        "games_per_second": len(outcomes) / elapsed if elapsed else None,
        "avg_turns": sum(row[3] for row in outcomes) / len(outcomes),
        "provenance": {
            key: ratings_provenance[key]
            for key in (
                "animal_kingdom_version",
                "bot_versions",
                "engine_sha256",
                "data_sha256",
                "config",
            )
        },
        "candidate_parameters": ratings_provenance["bot_parameters"]["referee"],
        "legacy_parameters": {
            "determinizations": 5,
            "beam_width": 8,
            "staged": False,
            "max_search_nodes": None,
        },
        "outcomes": [
            {
                "seed": seed,
                "candidate_seat": seat,
                "candidate_credit": credit,
                "turns": turns,
            }
            for seed, seat, credit, turns in outcomes
        ],
    }


def collect_positions(
    *,
    decks: Sequence[str] = tuple(sorted(DECK_SLUGS)),
    turns: Sequence[int] = (0, 3, 7),
    base_seed: int = 700,
    config: Optional[Config] = None,
    map_id: str = "map_b",
) -> list[DecisionPosition]:
    """Collect evaluator-independent positions from deterministic RandomBot trajectories."""
    decks = tuple(decks)
    offset = max(1, len(decks) // 2)
    positions = []
    for index, deck_a in enumerate(decks):
        deck_b = decks[(index + offset) % len(decks)]
        seed = base_seed + index
        state = new_game(
            load_premade_deck(deck_a),
            load_premade_deck(deck_b),
            seed,
            map_id=map_id,
            config=config,
        )
        bots = {
            "A": RandomBot(seed=seed * 2 + 1),
            "B": RandomBot(seed=seed * 2 + 2),
        }
        wanted = set(turns)
        captured = set()
        while rules.is_terminal(state) is None and captured != wanted:
            actor = state.player_to_act()
            legal = rules.legal_actions(state)
            turn = state.turn_counter
            if (
                state.pending is None
                and turn in wanted
                and turn not in captured
                and len(legal) > 1
            ):
                positions.append(DecisionPosition(
                    f"{deck_a}/{deck_b}/turn={turn}/actor={actor}",
                    state.clone(),
                ))
                captured.add(turn)
            action = bots[actor].choose(state.view_for(actor), legal, state)
            rules.apply_action(state, action)
    return positions


def compare_modes(
    positions: Sequence[DecisionPosition],
    *,
    bot_seed: int = 900,
) -> dict:
    rows = []
    legacy_seconds = candidate_seconds = 0.0
    agreements = 0
    for index, position in enumerate(positions):
        state = position.state
        actor = state.player_to_act()
        legal = rules.legal_actions(state)

        legacy = RefereeBot(
            seed=bot_seed + index,
            staged=False,
            max_search_nodes=None,
        )
        start = time.process_time()
        legacy_action = legacy.choose(state.view_for(actor), legal, state)
        legacy_time = time.process_time() - start

        candidate = RefereeBot(seed=bot_seed + index)
        start = time.process_time()
        candidate_action = candidate.choose(state.view_for(actor), legal, state)
        candidate_time = time.process_time() - start

        agrees = candidate_action == legacy_action
        agreements += int(agrees)
        legacy_seconds += legacy_time
        candidate_seconds += candidate_time
        rows.append({
            "position": position.label,
            "agrees": agrees,
            "legacy_action": repr(legacy_action),
            "candidate_action": repr(candidate_action),
            "legacy_cpu_s": legacy_time,
            "candidate_cpu_s": candidate_time,
            "speedup": legacy_time / candidate_time if candidate_time else None,
            "candidate_stats": dict(candidate.last_search_stats),
        })
    return {
        "positions": len(rows),
        "agreements": agreements,
        "agreement_rate": agreements / len(rows) if rows else None,
        "legacy_cpu_s": legacy_seconds,
        "candidate_cpu_s": candidate_seconds,
        "speedup": (
            legacy_seconds / candidate_seconds if candidate_seconds else None
        ),
        "rows": rows,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Compare staged Referee decisions with the full legacy search."
    )
    parser.add_argument("--seed", type=int, default=700)
    parser.add_argument("--bot-seed", type=int, default=900)
    parser.add_argument("--turns", default="0,3,7")
    parser.add_argument("--map", dest="map_id", default="map_b")
    parser.add_argument(
        "--config",
        default="animal_kingdom/data/two_action_config.json",
    )
    parser.add_argument(
        "--mirror-deck",
        choices=sorted(DECK_SLUGS),
        help="run staged-vs-legacy paired mirror games instead of position agreement",
    )
    parser.add_argument(
        "--games",
        type=int,
        default=200,
        help="mirror games; must be even because both seats share each seed",
    )
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument(
        "--out",
        type=Path,
        help="write the mirror summary and raw per-game outcomes as JSON",
    )
    args = parser.parse_args(argv)

    config = load_config_overrides(args.config)
    if args.mirror_deck:
        if args.games <= 0 or args.games % 2:
            raise SystemExit("--games must be a positive even number")
        result = run_mirror_strength_comparison(
            args.mirror_deck,
            paired_seeds=args.games // 2,
            base_seed=args.seed,
            config=config,
            map_id=args.map_id,
            jobs=args.jobs,
            progress=lambda done, total: (
                print(
                    f"  {done}/{total} games complete",
                    file=sys.stderr,
                )
                if done == total or done % 10 == 0 else None
            ),
        )
        if args.out is not None:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        lo, hi = result["ci95"]
        print(
            f"{result['deck']}: staged Referee {result['candidate_win_rate']:.1%} "
            f"[{lo:.1%}, {hi:.1%}] over {result['games']} paired-seat mirror games; "
            f"{result['elapsed_s']:.1f}s, {result['games_per_second']:.2f} games/s, "
            f"{result['avg_turns']:.1f} avg turns"
        )
        return

    turns = tuple(int(value) for value in args.turns.split(","))
    positions = collect_positions(
        turns=turns,
        base_seed=args.seed,
        config=config,
        map_id=args.map_id,
    )
    result = compare_modes(positions, bot_seed=args.bot_seed)
    for row in result["rows"]:
        marker = "=" if row["agrees"] else "!"
        print(
            f"{marker} {row['position']:<62} "
            f"{row['legacy_cpu_s']:>7.3f}s -> {row['candidate_cpu_s']:>7.3f}s  "
            f"{row['speedup']:>5.2f}x"
        )
        if not row["agrees"]:
            print(f"    legacy:    {row['legacy_action']}")
            print(f"    candidate: {row['candidate_action']}")
    print(
        f"\nAgreement: {result['agreements']}/{result['positions']} "
        f"({result['agreement_rate']:.1%})\n"
        f"CPU: {result['legacy_cpu_s']:.3f}s -> {result['candidate_cpu_s']:.3f}s "
        f"({result['speedup']:.2f}x)"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
