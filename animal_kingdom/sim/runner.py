"""Simulation harness: play headless bot-vs-bot games and collect records (handoff §10.2).

A game is fully determined by (deck A, deck B, seed, bot kinds, config), so every game is
independently reproducible and the round-robin parallelises cleanly: results are identical
whether run with `jobs=1` or many workers. Metrics aggregation lives in `metrics.py`; this
module only *produces* the per-game `GameRecord`s.
"""

from __future__ import annotations

import random
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Callable, Optional

from ..bots.base import Bot
from ..bots.greedy_bot import GreedyBot
from ..bots.random_bot import RandomBot
from ..decks import load_premade_deck
from ..engine import rules
from ..engine.config import Config
from ..engine.state import new_game


@dataclass(frozen=True)
class GameRecord:
    """One game's outcome, plus which cards each seat actually drew (presence-only:
    a card counts as drawn if it was in hand at any point, not exact copy counts)."""

    deck_a: str
    deck_b: str
    seed: int
    first_player: str        # "A" / "B" (coin-flipped from the seed)
    winner: Optional[str]    # "A" / "B" / None (draw)
    reason: str              # "hq_capture" | "food" | "exhaustion" | "max_turns"
    turns: int
    cards_drawn_a: frozenset[str] = frozenset()
    cards_drawn_b: frozenset[str] = frozenset()

    def to_dict(self) -> dict:
        return {"deck_a": self.deck_a, "deck_b": self.deck_b, "seed": self.seed,
                "first_player": self.first_player, "winner": self.winner,
                "reason": self.reason, "turns": self.turns,
                "cards_drawn_a": sorted(self.cards_drawn_a),
                "cards_drawn_b": sorted(self.cards_drawn_b)}


def make_bot(kind: str, seed: int) -> Bot:
    """Construct a bot from a kind string ('greedy' | 'random') with a derived seed."""
    kind = kind.strip().lower()
    if kind == "greedy":
        return GreedyBot(seed=seed)
    if kind == "random":
        return RandomBot(seed=seed)
    raise ValueError(f"unknown bot kind {kind!r} (expected 'greedy' or 'random')")


def play_game(
    deck_a: str,
    deck_b: str,
    seed: int,
    *,
    bot_a: Bot,
    bot_b: Bot,
    config: Optional[Config] = None,
    map_id: str = "map_a",
) -> GameRecord:
    """Play one headless game and return its record. Mirrors the cli.play loop."""
    state = new_game(load_premade_deck(deck_a), load_premade_deck(deck_b), seed,
                     map_id=map_id, config=config)
    bots = {"A": bot_a, "B": bot_b}

    drawn: dict[str, set[str]] = {"A": set(), "B": set()}

    def _snapshot_hands() -> None:
        for seat in ("A", "B"):
            drawn[seat].update(u.card_id for u in state.hands[seat])

    _snapshot_hands()  # opening hand
    result = rules.is_terminal(state)
    while result is None:
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        action = bots[actor].choose(state.view_for(actor), legal, state)
        rules.apply_action(state, action)
        _snapshot_hands()  # catches draws, bounces, tutors - anything that touches hands
        result = rules.is_terminal(state)

    return GameRecord(deck_a, deck_b, seed, state.first_player,
                      result.winner, result.reason, state.turn_counter,
                      frozenset(drawn["A"]), frozenset(drawn["B"]))


# --------------------------------------------------------------- match specs

@dataclass(frozen=True)
class MatchSpec:
    """A picklable description of one game, so the round-robin can run in worker processes.
    Bot seeds are derived from the game seed (distinct per seat) for reproducibility."""

    deck_a: str
    deck_b: str
    seed: int
    bot_a: str = "greedy"
    bot_b: str = "greedy"
    map_id: str = "map_a"


def _run_spec(spec: MatchSpec, config: Optional[Config] = None) -> GameRecord:
    bot_a = make_bot(spec.bot_a, seed=spec.seed * 2 + 1)
    bot_b = make_bot(spec.bot_b, seed=spec.seed * 2 + 2)
    return play_game(spec.deck_a, spec.deck_b, spec.seed,
                     bot_a=bot_a, bot_b=bot_b, config=config, map_id=spec.map_id)


def run_matchup(
    deck_a: str,
    deck_b: str,
    n_games: int,
    base_seed: int = 0,
    *,
    bots: tuple[str, str] = ("greedy", "greedy"),
    config: Optional[Config] = None,
    map_id: str = "map_a",
) -> list[GameRecord]:
    """`n_games` of deck_a vs deck_b with distinct seeds (first player varies via the flip)."""
    specs = [MatchSpec(deck_a, deck_b, base_seed + i, bots[0], bots[1], map_id)
             for i in range(n_games)]
    return [_run_spec(s, config) for s in specs]


def run_round_robin(
    slugs: list[str],
    n_games: int,
    base_seed: int = 0,
    *,
    bots: tuple[str, str] = ("greedy", "greedy"),
    config: Optional[Config] = None,
    map_id: str = "map_a",
    jobs: int = 1,
    progress: Optional[Callable[[str, str, int, int], None]] = None,
) -> list[GameRecord]:
    """Every ordered deck pair (full matrix incl. mirrors), `n_games` each.

    `jobs > 1` fans games out over a process pool; because each game is seed-determined the
    aggregate is identical regardless of `jobs`. A distinct seed per (pair, game) keeps every
    game independent. Matchups are run and reported one at a time (still spread across all
    `jobs` workers within each matchup) so `progress`, if given, is called after every
    completed matchup as `progress(deck_a, deck_b, matchups_done, matchups_total)`.
    """
    pairs = [(a, b) for a in slugs for b in slugs]
    records: list[GameRecord] = []

    def _matchup_specs(pair_index: int, a: str, b: str) -> list[MatchSpec]:
        pair_seed = base_seed + pair_index * n_games
        return [MatchSpec(a, b, pair_seed + i, bots[0], bots[1], map_id) for i in range(n_games)]

    def _run_all(ex: Optional[ProcessPoolExecutor]) -> None:
        for pair_index, (a, b) in enumerate(pairs):
            specs = _matchup_specs(pair_index, a, b)
            batch = ([_run_spec(s, config) for s in specs] if ex is None
                    else list(ex.map(_run_spec, specs, [config] * len(specs))))
            records.extend(batch)
            if progress is not None:
                progress(a, b, pair_index + 1, len(pairs))

    if jobs <= 1:
        _run_all(None)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            _run_all(ex)
    return records
