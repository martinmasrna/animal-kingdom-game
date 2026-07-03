"""Bot-version comparison harness: is a candidate bot actually better, not just different?

`run_gauntlet` plays one deck's *candidate* bot against a *pinned* pool of the other premade
decks (each piloted by a fixed reference bot) and reports a win-rate summary. Running it
again for a second candidate under the same deck/pool/seed schedule and diffing the two
results (`compare_gauntlets`) is how you tell whether a bot change (deeper lookahead,
retuned weights, ...) actually improved play instead of just moving the numbers around.

The candidate is always seat A, each pool opponent is seat B — this is not a first-player
bias, since `first_player` is coin-flipped independently of seat inside `new_game` (see
`runner.play_game`); one direction per opponent is enough for a fair comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, fields
from typing import Optional, Sequence

from ..bots.greedy_bot import GreedyWeights
from ..engine.cards import DECK_SLUGS
from ..engine.config import Config, load_config_overrides
from .runner import BOT_KINDS, GameRecord, parse_bot_kind, run_pairs


def _credit(rec: GameRecord, seat: str) -> float:
    """1.0 for a win, 0.5 for a draw, 0.0 for a loss, from `seat`'s perspective."""
    if rec.winner is None:
        return 0.5
    return 1.0 if rec.winner == seat else 0.0


@dataclass(frozen=True)
class GauntletResult:
    deck: str
    opponent_pool: tuple[str, ...]
    games_per_opponent: int
    overall_win_rate: float
    per_opponent_win_rate: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "deck": self.deck,
            "opponent_pool": list(self.opponent_pool),
            "games_per_opponent": self.games_per_opponent,
            "overall_win_rate": self.overall_win_rate,
            "per_opponent_win_rate": dict(self.per_opponent_win_rate),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GauntletResult":
        return cls(
            deck=d["deck"],
            opponent_pool=tuple(d["opponent_pool"]),
            games_per_opponent=d["games_per_opponent"],
            overall_win_rate=d["overall_win_rate"],
            per_opponent_win_rate=dict(d["per_opponent_win_rate"]),
        )


def run_gauntlet(
    deck: str,
    n_games: int,
    base_seed: int = 0,
    *,
    candidate_kind: str = "greedy",
    candidate_weights: Optional[GreedyWeights] = None,
    opponent_kind: str = "greedy",
    opponent_weights: Optional[GreedyWeights] = None,
    opponent_pool: Optional[Sequence[str]] = None,
    config: Optional[Config] = None,
    map_id: str = "map_b",
    jobs: int = 1,
) -> GauntletResult:
    """Run `deck`'s candidate bot against every deck in `opponent_pool` (default: all other
    premade decks), `n_games` each, with the opponent side pinned to `opponent_kind`/
    `opponent_weights`. Same (deck, opponent_pool, n_games, base_seed) across two calls makes
    their results directly comparable via `compare_gauntlets`.
    """
    pool = tuple(opponent_pool) if opponent_pool is not None else tuple(
        sorted(s for s in DECK_SLUGS if s != deck))
    pairs = [(deck, opp) for opp in pool]
    records = run_pairs(
        pairs, n_games, base_seed,
        bots=(candidate_kind, opponent_kind),
        weights=(candidate_weights, opponent_weights),
        config=config, map_id=map_id, jobs=jobs,
    )

    per_opponent: dict[str, float] = {}
    for opp in pool:
        opp_records = [r for r in records if r.deck_b == opp]
        per_opponent[opp] = sum(_credit(r, "A") for r in opp_records) / len(opp_records)

    overall = sum(_credit(r, "A") for r in records) / len(records)
    return GauntletResult(deck, pool, n_games, overall, per_opponent)


def compare_gauntlets(old: GauntletResult, new: GauntletResult) -> dict:
    """Diff two gauntlet runs for the same deck against the same opponent pool."""
    if old.deck != new.deck:
        raise ValueError(f"can't compare different decks: {old.deck!r} vs {new.deck!r}")
    if old.opponent_pool != new.opponent_pool:
        raise ValueError("can't compare gauntlets run against different opponent pools")
    return {
        "deck": old.deck,
        "overall_delta": new.overall_win_rate - old.overall_win_rate,
        "per_opponent_delta": {
            opp: new.per_opponent_win_rate[opp] - old.per_opponent_win_rate[opp]
            for opp in old.opponent_pool
        },
    }


# --------------------------------------------------------------------------------- CLI

def _load_weights(path: Optional[str]) -> Optional[GreedyWeights]:
    """Load a JSON dict of `GreedyWeights` field overrides; unspecified fields keep defaults."""
    if path is None:
        return None
    with open(path) as f:
        overrides = json.load(f)
    valid = {f.name for f in fields(GreedyWeights)}
    unknown = set(overrides) - valid
    if unknown:
        raise SystemExit(f"unknown GreedyWeights field(s) in {path}: {sorted(unknown)}")
    return GreedyWeights(**overrides)


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Run a deck's bot against a pinned pool of opponents; "
                    "optionally diff against a previous run.")
    p.add_argument("--deck", required=True, help="the candidate's deck slug")
    p.add_argument("--games", type=int, default=100, help="games per opponent")
    p.add_argument("--seed", type=int, default=0, help="base seed")
    p.add_argument("--candidate-kind", default="greedy",
                   help=f"one of {'|'.join(BOT_KINDS)} (default greedy)")
    p.add_argument("--opponent-kind", default="greedy",
                   help=f"one of {'|'.join(BOT_KINDS)} (default greedy)")
    p.add_argument("--weights", default=None,
                   help="JSON file of GreedyWeights field overrides for the candidate")
    p.add_argument("--opponent-weights", default=None,
                   help="JSON file of GreedyWeights field overrides for the pinned pool bot")
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--config", default=None,
                   help="JSON file of Config field overrides (rule/balance dials); "
                        "'none' clears a wrapper-injected preset")
    p.add_argument("--map", dest="map_id", default="map_b")
    p.add_argument("--out", default=None, help="write the GauntletResult JSON here")
    p.add_argument("--compare-to", default=None,
                   help="a previously-saved GauntletResult JSON; print the delta instead")
    args = p.parse_args(argv)

    result = run_gauntlet(
        args.deck, args.games, args.seed,
        candidate_kind=parse_bot_kind(args.candidate_kind, "--candidate-kind"),
        candidate_weights=_load_weights(args.weights),
        opponent_kind=parse_bot_kind(args.opponent_kind, "--opponent-kind"),
        opponent_weights=_load_weights(args.opponent_weights),
        config=load_config_overrides(args.config),
        map_id=args.map_id, jobs=args.jobs,
    )

    if args.out:
        with open(args.out, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"Wrote gauntlet result to {args.out}")

    print(f"\n{args.deck}: overall win rate {result.overall_win_rate:.1%} "
          f"over {len(result.opponent_pool)} opponents x {result.games_per_opponent} games")
    for opp, rate in sorted(result.per_opponent_win_rate.items()):
        print(f"  vs {opp:<20} {rate:.1%}")

    if args.compare_to:
        with open(args.compare_to) as f:
            old = GauntletResult.from_dict(json.load(f))
        diff = compare_gauntlets(old, result)
        print(f"\nDelta vs {args.compare_to}: overall {diff['overall_delta']:+.1%}")
        for opp, delta in sorted(diff["per_opponent_delta"].items()):
            print(f"  vs {opp:<20} {delta:+.1%}")


if __name__ == "__main__":
    main(sys.argv[1:])
