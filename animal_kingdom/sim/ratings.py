"""Anchored pilot-strength ratings from paired bot cross-play.

The fitted Bradley--Terry model separates three effects for competitor ``(pilot, deck)``::

    strength(pilot, deck) = pilot + deck + pilot:deck interaction

and adds a signed first-player term to the log-odds of seat A winning. RandomBot is fixed
at zero, deck effects sum to zero, and interaction rows and columns sum to zero. Those
constraints make the pilot term interpretable instead of rating opaque pilot/deck pairs.
Long simulation runs checkpoint complete paired blocks and resume only when their full
provenance matches.

This module is analysis-tier: NumPy and SciPy are optional project dependencies and are
never imported by ``engine/`` or ``bots/``.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from itertools import combinations
from pathlib import Path
from statistics import NormalDist
from typing import Any, Callable, Optional, Sequence

from .. import __version__
from ..bots.greedy_bot import GreedyBot
from ..bots.random_bot import RandomBot
from ..bots.referee_bot import RefereeBot
from ..bots.turn_bot import TurnBot
from ..engine.cards import DECK_SLUGS
from ..engine.config import Config, load_config_overrides
from .runner import (
    BOT_KINDS,
    LOOKAHEAD_BEAM_WIDTH,
    LOOKAHEAD_DEPTH,
    REFEREE_BEAM_WIDTH,
    REFEREE_DETERMINIZATIONS,
    TURN_BEAM_WIDTH,
    TURN_DETERMINIZATIONS,
    GameRecord,
    MatchSpec,
    run_specs,
)

DEFAULT_PILOTS = ("random", "greedy", "turn", "referee")
DEFAULT_ANCHOR = "random"
DEFAULT_CEILING = "referee"
DEFAULT_GAMES_PER_CONFIG = 200
DEFAULT_BOOTSTRAP_RESAMPLES = 400
DEFAULT_BOOTSTRAP_SEED = 0xA11CE
DEFAULT_RIDGE = 0.1
DEFAULT_CONFIG = "animal_kingdom/data/two_action_config.json"
MIN_GAMES_PER_CONFIG = 200
DEFAULT_CHECKPOINT_BLOCKS = 100


class IdentifiabilityError(ValueError):
    """Raised when a dataset cannot separate pilot, deck, interaction, and seat effects."""


@dataclass(frozen=True)
class RatingGame:
    """The model-relevant fields from one simulated game.

    ``pair_id`` identifies the two seat-swapped games sharing a seed.  Bootstrap resampling
    keeps those observations together, preserving the paired design.
    """

    pilot_a: str
    deck_a: str
    pilot_b: str
    deck_b: str
    seed: int
    first_player: str
    winner: Optional[str]
    pair_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RatingGame":
        return cls(
            pilot_a=raw["pilot_a"],
            deck_a=raw["deck_a"],
            pilot_b=raw["pilot_b"],
            deck_b=raw["deck_b"],
            seed=int(raw["seed"]),
            first_player=raw["first_player"],
            winner=raw.get("winner"),
            pair_id=str(raw["pair_id"]),
        )


@dataclass(frozen=True)
class RatingEstimate:
    rating: float
    ci_low: float
    ci_high: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class RatingResult:
    """Point estimates and intervals on the Bradley--Terry log-odds scale."""

    pilots: dict[str, RatingEstimate]
    decks: dict[str, RatingEstimate]
    interactions: dict[str, dict[str, RatingEstimate]]
    seat_advantage: RatingEstimate
    anchor: str
    ceiling_reference: Optional[str]
    games: int
    paired_blocks: int
    decided_games: int
    draws: int
    ridge: float
    interval_method: str
    bootstrap_resamples: int
    bootstrap_seed: int
    design_rank: int
    parameter_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "scale": "Bradley-Terry log-odds",
            "anchor": self.anchor,
            "ceiling_reference": self.ceiling_reference,
            "pilots": {name: value.to_dict() for name, value in self.pilots.items()},
            "decks": {name: value.to_dict() for name, value in self.decks.items()},
            "interactions": {
                pilot: {deck: value.to_dict() for deck, value in cells.items()}
                for pilot, cells in self.interactions.items()
            },
            "seat_advantage": self.seat_advantage.to_dict(),
            "games": self.games,
            "paired_blocks": self.paired_blocks,
            "decided_games": self.decided_games,
            "draws": self.draws,
            "ridge": self.ridge,
            "interval_method": self.interval_method,
            "bootstrap_resamples": self.bootstrap_resamples,
            "bootstrap_seed": self.bootstrap_seed,
            "design_rank": self.design_rank,
            "parameter_count": self.parameter_count,
        }


_ANALYSIS_MODULES = None


def _analysis_imports():
    global _ANALYSIS_MODULES
    if _ANALYSIS_MODULES is not None:
        return _ANALYSIS_MODULES
    try:
        import numpy as np
        from scipy.optimize import minimize
        from scipy.special import expit
    except ImportError as exc:  # pragma: no cover - exercised only in a core-only install
        raise RuntimeError(
            "pilot ratings need the analysis dependencies; install with "
            "`python -m pip install -e '.[analysis]'`"
        ) from exc
    _ANALYSIS_MODULES = (np, minimize, expit)
    return _ANALYSIS_MODULES


class _Parameterization:
    """Constrained two-way effect parameterization.

    Pilot effects omit the fixed anchor.  Deck effects use D-1 free values with the final
    effect equal to minus their sum.  Interactions use a (P-1)x(D-1) free corner; the final
    row and column are derived so every interaction row and column sums to zero.
    """

    def __init__(self, pilots: Sequence[str], decks: Sequence[str], anchor: str):
        self.pilots = tuple(sorted(pilots))
        self.decks = tuple(sorted(decks))
        self.anchor = anchor
        self.pilot_index = {name: i for i, name in enumerate(self.pilots)}
        self.deck_index = {name: i for i, name in enumerate(self.decks)}
        self.free_pilots = tuple(name for name in self.pilots if name != anchor)

        self.pilot_offset = 0
        self.deck_offset = len(self.free_pilots)
        self.interaction_offset = self.deck_offset + len(self.decks) - 1
        self.seat_index = self.interaction_offset + (
            (len(self.pilots) - 1) * (len(self.decks) - 1)
        )
        self.size = self.seat_index + 1

    def pilot_basis(self, pilot: str):
        np, _, _ = _analysis_imports()
        basis = np.zeros(self.size)
        if pilot != self.anchor:
            basis[self.pilot_offset + self.free_pilots.index(pilot)] = 1.0
        return basis

    def deck_basis(self, deck: str):
        np, _, _ = _analysis_imports()
        basis = np.zeros(self.size)
        d = self.deck_index[deck]
        free_d = len(self.decks) - 1
        if d < free_d:
            basis[self.deck_offset + d] = 1.0
        else:
            basis[self.deck_offset:self.deck_offset + free_d] = -1.0
        return basis

    def interaction_basis(self, pilot: str, deck: str):
        np, _, _ = _analysis_imports()
        basis = np.zeros(self.size)
        p = self.pilot_index[pilot]
        d = self.deck_index[deck]
        free_p = len(self.pilots) - 1
        free_d = len(self.decks) - 1

        def set_cell(row: int, col: int, value: float) -> None:
            index = self.interaction_offset + row * free_d + col
            basis[index] += value

        if p < free_p and d < free_d:
            set_cell(p, d, 1.0)
        elif p < free_p:
            for col in range(free_d):
                set_cell(p, col, -1.0)
        elif d < free_d:
            for row in range(free_p):
                set_cell(row, d, -1.0)
        else:
            for row in range(free_p):
                for col in range(free_d):
                    set_cell(row, col, 1.0)
        return basis

    def row(self, game: RatingGame):
        row = (
            self.pilot_basis(game.pilot_a)
            - self.pilot_basis(game.pilot_b)
            + self.deck_basis(game.deck_a)
            - self.deck_basis(game.deck_b)
            + self.interaction_basis(game.pilot_a, game.deck_a)
            - self.interaction_basis(game.pilot_b, game.deck_b)
        )
        row[self.seat_index] = 1.0 if game.first_player == "A" else -1.0
        return row


def _validate_games(games: Sequence[RatingGame], anchor: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if not games:
        raise IdentifiabilityError("cannot fit ratings without games")
    pilots = tuple(sorted({
        name for game in games for name in (game.pilot_a, game.pilot_b)
    }))
    decks = tuple(sorted({
        name for game in games for name in (game.deck_a, game.deck_b)
    }))
    if anchor not in pilots:
        raise IdentifiabilityError(f"anchor pilot {anchor!r} is absent from the dataset")
    if len(pilots) < 2:
        raise IdentifiabilityError("at least two pilots are required")
    if len(decks) < 2:
        raise IdentifiabilityError("at least two decks are required to separate deck effects")
    if not any(game.deck_a == game.deck_b for game in games):
        raise IdentifiabilityError("mirror matches are required to isolate pilot strength")
    if not any(game.deck_a != game.deck_b for game in games):
        raise IdentifiabilityError("cross-deck matches are required to identify deck strength")
    if {game.first_player for game in games} != {"A", "B"}:
        raise IdentifiabilityError(
            "both first-player assignments are required to identify first-player advantage"
        )
    for game in games:
        if game.first_player not in ("A", "B"):
            raise ValueError(f"bad first_player {game.first_player!r}")
        if game.winner not in ("A", "B", None):
            raise ValueError(f"bad winner {game.winner!r}")
        if game.pilot_a == game.pilot_b:
            raise ValueError("rating games must compare distinct pilots")
    return pilots, decks


def _fit_grouped(x, weights, successes, ridge: float, start=None):
    np, minimize, expit = _analysis_imports()
    if ridge < 0:
        raise ValueError("ridge must be non-negative")
    initial = np.zeros(x.shape[1]) if start is None else np.asarray(start, dtype=float)

    def objective(theta):
        logits = x @ theta
        loss = np.sum(weights * np.logaddexp(0.0, logits) - successes * logits)
        return float(loss + 0.5 * ridge * (theta @ theta))

    def gradient(theta):
        residual = weights * expit(x @ theta) - successes
        return x.T @ residual + ridge * theta

    fitted = minimize(
        objective,
        initial,
        jac=gradient,
        method="L-BFGS-B",
        options={"ftol": 1e-12, "gtol": 1e-8, "maxiter": 2_000},
    )
    if not fitted.success:
        raise RuntimeError(f"Bradley-Terry fit failed: {fitted.message}")
    return fitted.x


def _effect_bases(params: _Parameterization):
    labels: list[tuple[str, str, Optional[str]]] = []
    bases = []
    for pilot in params.pilots:
        labels.append(("pilot", pilot, None))
        bases.append(params.pilot_basis(pilot))
    for deck in params.decks:
        labels.append(("deck", deck, None))
        bases.append(params.deck_basis(deck))
    for pilot in params.pilots:
        for deck in params.decks:
            labels.append(("interaction", pilot, deck))
            bases.append(params.interaction_basis(pilot, deck))
    np, _, _ = _analysis_imports()
    seat = np.zeros(params.size)
    seat[params.seat_index] = 1.0
    labels.append(("seat", "first_player", None))
    bases.append(seat)
    return labels, np.vstack(bases)


def fit_ratings(
    games: Sequence[RatingGame],
    *,
    anchor: str = DEFAULT_ANCHOR,
    ceiling_reference: Optional[str] = DEFAULT_CEILING,
    ridge: float = DEFAULT_RIDGE,
    bootstrap_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    confidence: float = 0.95,
) -> RatingResult:
    """Fit the factored Bradley--Terry model and return estimates with confidence intervals.

    Draws contribute half a win to each player.  With ``bootstrap_resamples > 0`` intervals
    are deterministic percentile intervals from resampling paired blocks.  Passing zero uses
    the inverse penalized Fisher information (a Laplace approximation), useful for fast
    exploratory or synthetic fits.
    """
    np, _, expit = _analysis_imports()
    games = list(games)
    pilots, decks = _validate_games(games, anchor)
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    if bootstrap_resamples < 0:
        raise ValueError("bootstrap_resamples must be non-negative")

    params = _Parameterization(pilots, decks, anchor)
    design = np.vstack([params.row(game) for game in games])
    outcomes = np.asarray([
        1.0 if game.winner == "A" else 0.0 if game.winner == "B" else 0.5
        for game in games
    ])
    rank = int(np.linalg.matrix_rank(design))
    if rank != params.size:
        raise IdentifiabilityError(
            "rating design is not identifiable: "
            f"matrix rank {rank} < {params.size} parameters; include every pilot on multiple "
            "decks, mirror matches, cross-deck matches, and both first-player assignments"
        )

    grouped_x, group_index = np.unique(design, axis=0, return_inverse=True)
    group_weights = np.bincount(group_index, minlength=len(grouped_x)).astype(float)
    group_successes = np.bincount(
        group_index, weights=outcomes, minlength=len(grouped_x)
    )
    theta = _fit_grouped(grouped_x, group_weights, group_successes, ridge)

    labels, effect_bases = _effect_bases(params)
    point_values = effect_bases @ theta
    alpha = 1.0 - confidence

    if bootstrap_resamples:
        cluster_index: dict[str, int] = {}
        observation_clusters = []
        for i, game in enumerate(games):
            key = game.pair_id if game.pair_id else f"unpaired:{i}"
            if key not in cluster_index:
                cluster_index[key] = len(cluster_index)
            observation_clusters.append(cluster_index[key])
        observation_clusters = np.asarray(observation_clusters, dtype=int)
        cluster_count = len(cluster_index)
        rng = np.random.default_rng(bootstrap_seed)
        bootstrap_values = np.empty((bootstrap_resamples, len(labels)))
        for sample_index in range(bootstrap_resamples):
            picked = rng.integers(0, cluster_count, size=cluster_count)
            multiplicity = np.bincount(picked, minlength=cluster_count)
            observation_weights = multiplicity[observation_clusters]
            weights = np.bincount(
                group_index, weights=observation_weights, minlength=len(grouped_x)
            )
            successes = np.bincount(
                group_index,
                weights=observation_weights * outcomes,
                minlength=len(grouped_x),
            )
            boot_theta = _fit_grouped(
                grouped_x, weights, successes, ridge, start=theta
            )
            bootstrap_values[sample_index] = effect_bases @ boot_theta
        lows = np.quantile(bootstrap_values, alpha / 2.0, axis=0)
        highs = np.quantile(bootstrap_values, 1.0 - alpha / 2.0, axis=0)
        interval_method = "paired percentile bootstrap"
    else:
        probabilities = expit(grouped_x @ theta)
        fisher = grouped_x.T @ (
            grouped_x * (group_weights * probabilities * (1.0 - probabilities))[:, None]
        )
        fisher += ridge * np.eye(params.size)
        covariance = np.linalg.inv(fisher)
        variances = np.einsum("ij,jk,ik->i", effect_bases, covariance, effect_bases)
        z = NormalDist().inv_cdf(1.0 - alpha / 2.0)
        half_width = z * np.sqrt(np.maximum(variances, 0.0))
        lows = point_values - half_width
        highs = point_values + half_width
        interval_method = "penalized Fisher/Laplace"

    estimates: dict[tuple[str, str, Optional[str]], RatingEstimate] = {}
    for index, label in enumerate(labels):
        estimates[label] = RatingEstimate(
            float(point_values[index]), float(lows[index]), float(highs[index])
        )
    # The anchor is a fixed constant, not an uncertain fitted quantity.
    estimates[("pilot", anchor, None)] = RatingEstimate(0.0, 0.0, 0.0)

    pilot_results = {
        pilot: estimates[("pilot", pilot, None)] for pilot in params.pilots
    }
    deck_results = {
        deck: estimates[("deck", deck, None)] for deck in params.decks
    }
    interaction_results = {
        pilot: {
            deck: estimates[("interaction", pilot, deck)]
            for deck in params.decks
        }
        for pilot in params.pilots
    }
    pair_count = len({game.pair_id for game in games})
    draws = sum(game.winner is None for game in games)
    return RatingResult(
        pilots=pilot_results,
        decks=deck_results,
        interactions=interaction_results,
        seat_advantage=estimates[("seat", "first_player", None)],
        anchor=anchor,
        ceiling_reference=ceiling_reference if ceiling_reference in pilots else None,
        games=len(games),
        paired_blocks=pair_count,
        decided_games=len(games) - draws,
        draws=draws,
        ridge=ridge,
        interval_method=interval_method,
        bootstrap_resamples=bootstrap_resamples,
        bootstrap_seed=bootstrap_seed,
        design_rank=rank,
        parameter_count=params.size,
    )


def build_paired_schedule(
    pilots: Sequence[str],
    decks: Sequence[str],
    games_per_config: int,
    base_seed: int,
    *,
    map_id: str = "map_b",
) -> tuple[list[MatchSpec], list[tuple[str, str, str, str, str]]]:
    """Build full-factorial, paired cross-play specs and their model metadata.

    For every unordered pilot pair and ordered deck pair, ``games_per_config`` seeds are
    played twice with the complete pilot/deck competitors swapped between seats.  The
    returned metadata tuple is ``(pilot_a, deck_a, pilot_b, deck_b, pair_id)`` and aligns
    one-for-one with the specs.
    """
    pilots = tuple(dict.fromkeys(pilots))
    decks = tuple(dict.fromkeys(decks))
    if games_per_config <= 0:
        raise ValueError("games_per_config must be positive")
    if len(pilots) < 2 or len(decks) < 2:
        raise ValueError("the schedule needs at least two pilots and two decks")
    unknown = set(pilots) - set(BOT_KINDS)
    if unknown:
        raise ValueError(f"unknown pilot kind(s): {sorted(unknown)}")

    specs: list[MatchSpec] = []
    metadata: list[tuple[str, str, str, str, str]] = []
    block = 0
    for pilot_a, pilot_b in combinations(pilots, 2):
        for deck_a in decks:
            for deck_b in decks:
                for repetition in range(games_per_config):
                    seed = base_seed + block * games_per_config + repetition
                    pair_id = f"{block}:{repetition}"
                    specs.append(MatchSpec(
                        deck_a, deck_b, seed, pilot_a, pilot_b, map_id
                    ))
                    metadata.append((pilot_a, deck_a, pilot_b, deck_b, pair_id))
                    specs.append(MatchSpec(
                        deck_b, deck_a, seed, pilot_b, pilot_a, map_id
                    ))
                    metadata.append((pilot_b, deck_b, pilot_a, deck_a, pair_id))
                block += 1
    return specs, metadata


def generate_rating_dataset(
    pilots: Sequence[str],
    decks: Sequence[str],
    games_per_config: int,
    base_seed: int,
    *,
    config: Optional[Config] = None,
    map_id: str = "map_b",
    jobs: int = 1,
) -> list[RatingGame]:
    """Run a paired full-factorial pilot/deck experiment using the shared sim runner."""
    specs, metadata = build_paired_schedule(
        pilots, decks, games_per_config, base_seed, map_id=map_id
    )
    records = run_specs(specs, config=config, jobs=jobs)
    return [
        _rating_game(meta, record)
        for meta, record in zip(metadata, records)
    ]


def _rating_game(
    metadata: tuple[str, str, str, str, str],
    record: GameRecord,
) -> RatingGame:
    return RatingGame(
        pilot_a=metadata[0],
        deck_a=metadata[1],
        pilot_b=metadata[2],
        deck_b=metadata[3],
        seed=record.seed,
        first_player=record.first_player,
        winner=record.winner,
        pair_id=metadata[4],
    )


def _source_hashes(*classes: type) -> dict[str, str]:
    hashes = {}
    for cls in classes:
        path = inspect.getsourcefile(cls)
        if path is not None:
            hashes[Path(path).name] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return hashes


def build_provenance(
    *,
    pilots: Sequence[str],
    decks: Sequence[str],
    games_per_config: int,
    base_seed: int,
    map_id: str,
    config: Optional[Config],
    config_id: Optional[str],
) -> dict[str, Any]:
    bot_classes = {
        "random": RandomBot,
        "greedy": GreedyBot,
        "lookahead": GreedyBot,
        "turn": TurnBot,
        "referee": RefereeBot,
    }
    shared_sources = {
        "random": (RandomBot,),
        "greedy": (GreedyBot,),
        "lookahead": (GreedyBot,),
        # TurnBot and RefereeBot inherit their planner from TurnBot's direct base.
        "turn": (TurnBot, TurnBot.__base__, GreedyBot),
        "referee": (RefereeBot, RefereeBot.__base__, GreedyBot),
    }
    bot_versions = {
        pilot: {
            "class": bot_classes[pilot].__name__,
            "source_sha256": _source_hashes(*shared_sources[pilot]),
        }
        for pilot in pilots
        if pilot in bot_classes
    }
    bot_parameters = {
        "lookahead": {
            "depth": LOOKAHEAD_DEPTH,
            "beam_width": LOOKAHEAD_BEAM_WIDTH,
        },
        "turn": {
            "determinizations": TURN_DETERMINIZATIONS,
            "beam_width": TURN_BEAM_WIDTH,
        },
        "referee": {
            "determinizations": REFEREE_DETERMINIZATIONS,
            "beam_width": REFEREE_BEAM_WIDTH,
        },
    }
    pilot_pairs = len(tuple(combinations(pilots, 2)))
    paired_blocks = pilot_pairs * len(decks) * len(decks) * games_per_config
    return {
        "schema_version": 2,
        "animal_kingdom_version": __version__,
        "pilots": list(pilots),
        "decks": list(decks),
        "bot_versions": bot_versions,
        "bot_parameters": {
            key: value for key, value in bot_parameters.items() if key in pilots
        },
        "map": map_id,
        "config_id": config_id,
        "config": asdict(config or Config.default()),
        "seed_schedule": {
            "base_seed": base_seed,
            "paired": True,
            "seat_assignments": 2,
            "description": (
                "contiguous seed block per pilot-pair x ordered deck-pair; each seed "
                "reused with complete pilot/deck competitors swapped between seats"
            ),
        },
        "games_per_pilot_pair_deck_config": games_per_config,
        "paired_blocks": paired_blocks,
        "sample_size": paired_blocks * 2,
        "human_anchor": None,
    }


def write_dataset(
    path: os.PathLike[str] | str,
    games: Sequence[RatingGame],
    provenance: dict[str, Any],
) -> None:
    """Write deterministic JSON Lines: one provenance header followed by raw games."""
    with open(path, "w") as handle:
        handle.write(json.dumps({"type": "meta", "meta": provenance}, sort_keys=True) + "\n")
        for game in games:
            handle.write(json.dumps(
                {"type": "game", **game.to_dict()}, sort_keys=True
            ) + "\n")


def _read_dataset_record(
    raw: dict[str, Any],
    *,
    path: os.PathLike[str] | str,
    line_number: int,
    games: list[RatingGame],
) -> Optional[dict[str, Any]]:
    record_type = raw.get("type")
    if record_type == "meta":
        return dict(raw["meta"])
    if record_type == "game":
        games.append(RatingGame.from_dict(raw))
        return None
    if record_type == "pair":
        pair = [RatingGame.from_dict(game) for game in raw.get("games", ())]
        if len(pair) != 2:
            raise ValueError(f"{path}:{line_number}: paired block must contain two games")
        if pair[0].pair_id != pair[1].pair_id:
            raise ValueError(f"{path}:{line_number}: paired block IDs do not match")
        if raw.get("pair_id") != pair[0].pair_id:
            raise ValueError(f"{path}:{line_number}: paired block header ID does not match")
        games.extend(pair)
        return None
    raise ValueError(f"{path}:{line_number}: unknown dataset record type")


def load_dataset(
    path: os.PathLike[str] | str,
) -> tuple[list[RatingGame], dict[str, Any]]:
    games = []
    provenance: dict[str, Any] = {}
    with open(path) as handle:
        for line_number, line in enumerate(handle, start=1):
            raw = json.loads(line)
            meta = _read_dataset_record(
                raw, path=path, line_number=line_number, games=games
            )
            if meta is not None:
                if provenance:
                    raise ValueError(f"{path}:{line_number}: duplicate provenance header")
                provenance = meta
    return games, provenance


def _load_checkpoint(
    path: os.PathLike[str] | str,
) -> tuple[list[RatingGame], dict[str, Any]]:
    """Load a checkpoint, discarding only a crash-truncated final JSON line."""
    games: list[RatingGame] = []
    provenance: dict[str, Any] = {}
    with open(path, "rb+") as handle:
        line_number = 0
        while True:
            line_start = handle.tell()
            line = handle.readline()
            if not line:
                break
            line_number += 1
            try:
                raw = json.loads(line)
            except (UnicodeDecodeError, json.JSONDecodeError):
                # A flush/fsync makes completed pair lines durable. The only recoverable
                # corruption is therefore an unterminated final line from a killed write.
                if line.endswith(b"\n") or handle.read(1):
                    raise ValueError(
                        f"{path}:{line_number}: corrupt checkpoint record"
                    ) from None
                handle.seek(line_start)
                handle.truncate()
                handle.flush()
                os.fsync(handle.fileno())
                break
            meta = _read_dataset_record(
                raw, path=path, line_number=line_number, games=games
            )
            if meta is not None:
                if provenance:
                    raise ValueError(f"{path}:{line_number}: duplicate provenance header")
                provenance = meta
            # A valid last line may have reached disk before its newline. Normalize it so
            # the next append cannot join two JSON objects.
            if not line.endswith(b"\n"):
                handle.seek(0, os.SEEK_END)
                handle.write(b"\n")
                handle.flush()
                os.fsync(handle.fileno())
                break
    return games, provenance


def _atomic_initialize_checkpoint(
    path: Path,
    provenance: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(temporary, "w") as handle:
            handle.write(
                json.dumps({"type": "meta", "meta": provenance}, sort_keys=True) + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _append_checkpoint_pairs(
    path: Path,
    pairs: Sequence[tuple[RatingGame, RatingGame]],
) -> None:
    with open(path, "a") as handle:
        for left, right in pairs:
            payload = {
                "type": "pair",
                "pair_id": left.pair_id,
                "games": [left.to_dict(), right.to_dict()],
            }
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _game_schedule_key(game: RatingGame) -> tuple[Any, ...]:
    return (
        game.pair_id,
        game.pilot_a,
        game.deck_a,
        game.pilot_b,
        game.deck_b,
        game.seed,
    )


def _expected_schedule_key(
    spec: MatchSpec,
    metadata: tuple[str, str, str, str, str],
) -> tuple[Any, ...]:
    return (
        metadata[4],
        metadata[0],
        metadata[1],
        metadata[2],
        metadata[3],
        spec.seed,
    )


@contextmanager
def _checkpoint_lock(path: Path):
    """Prevent two calibration processes from appending to one checkpoint."""
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+") as lock:
        try:
            import fcntl
        except ImportError:  # pragma: no cover - advisory locks are Unix-only
            yield
            return
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(
                f"another process is already using checkpoint {path}"
            ) from None
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def run_checkpointed_rating_dataset(
    pilots: Sequence[str],
    decks: Sequence[str],
    games_per_config: int,
    base_seed: int,
    *,
    dataset_path: os.PathLike[str] | str,
    provenance: dict[str, Any],
    config: Optional[Config] = None,
    map_id: str = "map_b",
    jobs: int = 1,
    checkpoint_blocks: int = DEFAULT_CHECKPOINT_BLOCKS,
    progress: Optional[Callable[[int, int], None]] = None,
) -> list[RatingGame]:
    """Run or resume a durable paired dataset in canonical schedule order.

    Each checkpoint line contains both seat assignments for one paired seed. Completed
    lines are flushed and fsynced after every batch. Existing games are accepted only when
    their full provenance and schedule entries match this invocation exactly.
    """
    path = Path(dataset_path)
    with _checkpoint_lock(path):
        return _run_checkpointed_rating_dataset(
            pilots,
            decks,
            games_per_config,
            base_seed,
            dataset_path=path,
            provenance=provenance,
            config=config,
            map_id=map_id,
            jobs=jobs,
            checkpoint_blocks=checkpoint_blocks,
            progress=progress,
        )


def _run_checkpointed_rating_dataset(
    pilots: Sequence[str],
    decks: Sequence[str],
    games_per_config: int,
    base_seed: int,
    *,
    dataset_path: os.PathLike[str] | str,
    provenance: dict[str, Any],
    config: Optional[Config],
    map_id: str,
    jobs: int,
    checkpoint_blocks: int,
    progress: Optional[Callable[[int, int], None]],
) -> list[RatingGame]:
    if checkpoint_blocks <= 0:
        raise ValueError("checkpoint_blocks must be positive")
    path = Path(dataset_path)
    specs, metadata = build_paired_schedule(
        pilots, decks, games_per_config, base_seed, map_id=map_id
    )
    expected = {
        _expected_schedule_key(spec, meta): index
        for index, (spec, meta) in enumerate(zip(specs, metadata))
    }
    total_blocks = len(specs) // 2

    if path.exists():
        saved_games, saved_provenance = _load_checkpoint(path)
        if saved_provenance != provenance:
            mismatches = sorted(
                key for key in set(saved_provenance) | set(provenance)
                if saved_provenance.get(key) != provenance.get(key)
            )
            raise ValueError(
                "checkpoint provenance does not match this run"
                + (f" (different: {', '.join(mismatches)})" if mismatches else "")
            )
    else:
        _atomic_initialize_checkpoint(path, provenance)
        saved_games = []

    saved_by_key: dict[tuple[Any, ...], RatingGame] = {}
    saved_per_pair: dict[str, int] = {}
    for game in saved_games:
        key = _game_schedule_key(game)
        if key not in expected:
            raise ValueError(
                f"checkpoint game {game.pair_id!r} is not in the current seed schedule"
            )
        if key in saved_by_key:
            raise ValueError(f"checkpoint contains duplicate game {game.pair_id!r}")
        saved_by_key[key] = game
        saved_per_pair[game.pair_id] = saved_per_pair.get(game.pair_id, 0) + 1
    incomplete = sorted(
        pair_id for pair_id, count in saved_per_pair.items() if count != 2
    )
    if incomplete:
        raise ValueError(
            "checkpoint contains incomplete paired block(s): "
            + ", ".join(incomplete[:5])
        )

    missing_block_starts = [
        index
        for index in range(0, len(specs), 2)
        if _expected_schedule_key(specs[index], metadata[index]) not in saved_by_key
    ]
    completed_blocks = total_blocks - len(missing_block_starts)
    if progress is not None:
        progress(completed_blocks, total_blocks)

    for batch_start in range(0, len(missing_block_starts), checkpoint_blocks):
        starts = missing_block_starts[batch_start:batch_start + checkpoint_blocks]
        batch_specs = [
            specs[index + offset]
            for index in starts
            for offset in (0, 1)
        ]
        records = run_specs(batch_specs, config=config, jobs=jobs)
        completed_pairs = []
        for pair_offset, schedule_index in enumerate(starts):
            left = _rating_game(
                metadata[schedule_index], records[pair_offset * 2]
            )
            right = _rating_game(
                metadata[schedule_index + 1], records[pair_offset * 2 + 1]
            )
            if left.pair_id != right.pair_id or left.first_player != right.first_player:
                raise RuntimeError("paired simulations returned inconsistent seed metadata")
            completed_pairs.append((left, right))
        _append_checkpoint_pairs(path, completed_pairs)
        for pair in completed_pairs:
            for game in pair:
                saved_by_key[_game_schedule_key(game)] = game
        completed_blocks += len(completed_pairs)
        if progress is not None:
            progress(completed_blocks, total_blocks)

    # Checkpoint append order can differ after filling a gap. Canonical schedule order is
    # required so a resumed fit and its bootstrap are byte-identical to an uninterrupted fit.
    return [
        saved_by_key[_expected_schedule_key(spec, meta)]
        for spec, meta in zip(specs, metadata)
    ]


def format_result(result: RatingResult) -> str:
    def table(title: str, rows: Sequence[tuple[str, RatingEstimate]]) -> list[str]:
        lines = [title, f"{'name':<34}{'rating':>10}{'95% CI':>24}"]
        for name, estimate in rows:
            lines.append(
                f"{name:<34}{estimate.rating:>+10.3f}"
                f"  [{estimate.ci_low:>+8.3f}, {estimate.ci_high:>+8.3f}]"
            )
        return lines

    lines = [
        f"Pilot strength (Bradley-Terry log-odds; {result.anchor}=0 fixed; "
        f"observed ceiling: {result.ceiling_reference or 'not in dataset'})",
        "",
    ]
    pilot_rows = sorted(
        result.pilots.items(), key=lambda item: item[1].rating
    )
    lines.extend(table("Pilots", pilot_rows))
    lines.extend(["", *table("Deck strength (byproduct; sum constrained to zero)",
                             sorted(result.decks.items()))])
    lines += [
        "",
        "Pilot x deck interaction (execution difficulty; rows/columns sum to zero)",
        f"{'pilot / deck':<34}{'rating':>10}{'95% CI':>24}",
    ]
    for pilot in sorted(result.interactions):
        for deck in sorted(result.interactions[pilot]):
            estimate = result.interactions[pilot][deck]
            lines.append(
                f"{pilot + ' / ' + deck:<34}{estimate.rating:>+10.3f}"
                f"  [{estimate.ci_low:>+8.3f}, {estimate.ci_high:>+8.3f}]"
            )
    seat = result.seat_advantage
    lines += [
        "",
        "First-player advantage",
        f"  {seat.rating:+.3f}  [{seat.ci_low:+.3f}, {seat.ci_high:+.3f}] log-odds",
        "",
        f"{result.games} games / {result.paired_blocks} paired blocks; "
        f"{result.draws} draws; {result.interval_method}; ridge={result.ridge:g}; "
        f"design rank={result.design_rank}/{result.parameter_count}.",
    ]
    return "\n".join(lines)


def _parse_list(raw: str, *, allowed: Optional[set[str]] = None, flag: str) -> list[str]:
    values = [value.strip().lower() for value in raw.split(",") if value.strip()]
    if not values:
        raise SystemExit(f"{flag} requires at least one value")
    if len(values) != len(set(values)):
        raise SystemExit(f"{flag} contains duplicates")
    if allowed is not None:
        unknown = set(values) - allowed
        if unknown:
            raise SystemExit(f"{flag} has unknown value(s): {sorted(unknown)}")
    return values


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate resumable paired pilot/deck cross-play and fit anchored "
            "factored Bradley-Terry ratings."
        )
    )
    parser.add_argument("--games", type=int, default=DEFAULT_GAMES_PER_CONFIG,
                        help="paired seeds per pilot-pair x ordered deck-pair (minimum 200)")
    parser.add_argument("--seed", type=int, default=0, help="base simulation seed")
    parser.add_argument("--pilots", default=",".join(DEFAULT_PILOTS),
                        help="comma-separated bot kinds")
    parser.add_argument("--decks", default="all",
                        help="comma-separated premade deck slugs (default all)")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1)
    parser.add_argument("--map", dest="map_id", default="map_b")
    parser.add_argument("--config", default=DEFAULT_CONFIG,
                        help="JSON Config overrides; use 'none' for classic defaults")
    parser.add_argument("--out", default="results/pilot_ratings",
                        help="artifact directory")
    parser.add_argument("--dataset", default=None,
                        help="fit an existing dataset.jsonl instead of running simulations")
    parser.add_argument(
        "--checkpoint-blocks",
        type=int,
        default=DEFAULT_CHECKPOINT_BLOCKS,
        help="paired blocks per durable checkpoint batch (default 100)",
    )
    parser.add_argument("--ridge", type=float, default=DEFAULT_RIDGE)
    parser.add_argument("--bootstrap-resamples", type=int,
                        default=DEFAULT_BOOTSTRAP_RESAMPLES)
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()

    if args.dataset:
        games, provenance = load_dataset(args.dataset)
        pilots = sorted({
            pilot for game in games for pilot in (game.pilot_a, game.pilot_b)
        })
        print(f"Loaded {len(games)} games from {args.dataset}.", file=sys.stderr)
    else:
        if args.games < MIN_GAMES_PER_CONFIG:
            raise SystemExit(
                f"--games must be >= {MIN_GAMES_PER_CONFIG} for a rating run "
                "(paired methodology requirement)"
            )
        pilots = _parse_list(args.pilots, allowed=set(BOT_KINDS), flag="--pilots")
        if DEFAULT_ANCHOR not in pilots:
            raise SystemExit(f"--pilots must include the anchor {DEFAULT_ANCHOR!r}")
        decks = (
            sorted(DECK_SLUGS)
            if args.decks.strip().lower() == "all"
            else _parse_list(args.decks, allowed=set(DECK_SLUGS), flag="--decks")
        )
        if len(pilots) < 2 or len(decks) < 2:
            raise SystemExit("rating runs require at least two pilots and two decks")
        config = load_config_overrides(args.config)
        provenance = build_provenance(
            pilots=pilots,
            decks=decks,
            games_per_config=args.games,
            base_seed=args.seed,
            map_id=args.map_id,
            config=config,
            config_id=args.config,
        )
        total = provenance["sample_size"]
        print(
            f"Running {total} games ({provenance['paired_blocks']} paired blocks), "
            f"map={args.map_id}, jobs={args.jobs}, seed={args.seed}...",
            file=sys.stderr,
        )
        dataset_path = out_dir / "dataset.jsonl"
        was_checkpoint = dataset_path.exists()

        def _checkpoint_progress(done: int, block_total: int) -> None:
            elapsed = time.monotonic() - start
            verb = "Resuming" if was_checkpoint and done < block_total else "Checkpoint"
            print(
                f"  {verb}: {done}/{block_total} paired blocks "
                f"({done / block_total:.1%}), {elapsed:.1f}s elapsed",
                file=sys.stderr,
            )

        games = run_checkpointed_rating_dataset(
            pilots, decks, args.games, args.seed,
            dataset_path=dataset_path,
            provenance=provenance,
            config=config,
            map_id=args.map_id,
            jobs=args.jobs,
            checkpoint_blocks=args.checkpoint_blocks,
            progress=_checkpoint_progress,
        )
        print(f"Raw dataset complete at {dataset_path}.", file=sys.stderr)

    print(
        f"Fitting ratings with {args.bootstrap_resamples} paired bootstrap resamples...",
        file=sys.stderr,
    )
    result = fit_ratings(
        games,
        anchor=DEFAULT_ANCHOR,
        ceiling_reference=DEFAULT_CEILING,
        ridge=args.ridge,
        bootstrap_resamples=args.bootstrap_resamples,
        bootstrap_seed=args.bootstrap_seed,
    )
    payload = {"provenance": provenance, "ratings": result.to_dict()}
    ratings_path = out_dir / "ratings.json"
    with open(ratings_path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    print(format_result(result))
    print(
        f"\nArtifacts written to {out_dir}/ in {time.monotonic() - start:.1f}s.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main(sys.argv[1:])
