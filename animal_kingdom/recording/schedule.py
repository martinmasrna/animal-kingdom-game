"""CLI for generating explicit human-game cohort manifests."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from ..decks import PREMADE_DECKS
from ..engine.config import Config, load_config_overrides
from ..sim.runner import BOT_KINDS
from .cohort import generate_manifest, write_manifest


def _items(value: str, *, allowed: Sequence[str], label: str) -> tuple[str, ...]:
    if value.strip().lower() == "all":
        return tuple(sorted(allowed))
    values = tuple(part.strip() for part in value.split(",") if part.strip())
    unknown = sorted(set(values) - set(allowed))
    if not values or unknown:
        raise argparse.ArgumentTypeError(
            f"{label} expects comma-separated values from {sorted(allowed)} or 'all'"
        )
    return values


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Generate a human benchmark cohort.")
    parser.add_argument("--id", required=True, dest="cohort_id")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--human-decks", default="all")
    parser.add_argument("--opponent-decks", default="all")
    parser.add_argument("--bots", default="greedy")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument(
        "--exclude-mirrors",
        action="store_true",
        help="Skip deck-vs-itself matchups (lower value for a balance yardstick).",
    )
    parser.add_argument("--seats", choices=("A", "B", "both"), default="both")
    parser.add_argument(
        "--order", choices=("shuffled", "grouped"), default="shuffled",
        help="'shuffled' interleaves matchups (comparable-cohort default); 'grouped' plays "
             "all games of one matchup consecutively before the next.",
    )
    parser.add_argument("--base-seed", type=int, default=0)
    parser.add_argument("--schedule-seed", type=int, default=0)
    parser.add_argument("--map", dest="map_id", default="map_b")
    parser.add_argument(
        "--config",
        default="none",
        help="Config override JSON; use 'none' for defaults.",
    )
    args = parser.parse_args(argv)

    decks = tuple(sorted(PREMADE_DECKS))
    try:
        human_decks = _items(args.human_decks, allowed=decks, label="--human-decks")
        opponent_decks = _items(args.opponent_decks, allowed=decks, label="--opponent-decks")
        bots = _items(args.bots, allowed=BOT_KINDS, label="--bots")
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))
    seats = ("A", "B") if args.seats == "both" else (args.seats,)
    config = load_config_overrides(args.config) or Config.default()
    try:
        manifest = generate_manifest(
            cohort_id=args.cohort_id,
            human_decks=human_decks,
            opponent_decks=opponent_decks,
            opponent_kinds=bots,
            repetitions=args.repetitions,
            seats=seats,
            base_seed=args.base_seed,
            schedule_seed=args.schedule_seed,
            map_id=args.map_id,
            config=config,
            exclude_mirrors=args.exclude_mirrors,
            shuffle=(args.order == "shuffled"),
        )
    except ValueError as exc:
        parser.error(str(exc))
    write_manifest(args.out, manifest)
    print(f"wrote {len(manifest.games)} games to {args.out}")


if __name__ == "__main__":
    main()
