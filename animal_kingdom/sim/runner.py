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
from typing import Optional

from ..bots.base import Bot
from ..bots.greedy_bot import GreedyBot
from ..bots.random_bot import RandomBot
from ..decks import load_premade_deck
from ..engine import rules
from ..engine.config import Config
from ..engine.state import new_game


@dataclass(frozen=True)
class GameRecord:
    """One game's outcome. Per-card presence is re-derived from the deck slugs at
    aggregation time, so the record stays small and JSON-serializable."""

    deck_a: str
    deck_b: str
    seed: int
    first_player: str        # "A" / "B" (coin-flipped from the seed)
    winner: Optional[str]    # "A" / "B" / None (draw)
    reason: str              # "hq_capture" | "food" | "exhaustion" | "max_turns"
    turns: int

    def to_dict(self) -> dict:
        return {"deck_a": self.deck_a, "deck_b": self.deck_b, "seed": self.seed,
                "first_player": self.first_player, "winner": self.winner,
                "reason": self.reason, "turns": self.turns}


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

    result = rules.is_terminal(state)
    while result is None:
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        action = bots[actor].choose(state.view_for(actor), legal, state)
        rules.apply_action(state, action)
        result = rules.is_terminal(state)

    return GameRecord(deck_a, deck_b, seed, state.first_player,
                      result.winner, result.reason, state.turn_counter)


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
) -> list[GameRecord]:
    """Every ordered deck pair (full matrix incl. mirrors), `n_games` each.

    `jobs > 1` fans games out over a process pool; because each game is seed-determined the
    aggregate is identical regardless of `jobs`. A distinct seed per (pair, game) keeps every
    game independent.
    """
    specs: list[MatchSpec] = []
    for ai, a in enumerate(slugs):
        for bi, b in enumerate(slugs):
            pair_seed = base_seed + (ai * len(slugs) + bi) * n_games
            for i in range(n_games):
                specs.append(MatchSpec(a, b, pair_seed + i, bots[0], bots[1], map_id))

    if jobs <= 1:
        return [_run_spec(s, config) for s in specs]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(_run_spec, specs, [config] * len(specs)))
