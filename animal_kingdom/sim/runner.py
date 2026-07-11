"""Simulation harness: play headless bot-vs-bot games and collect records (handoff §10.2).

A game is fully determined by (deck A, deck B, seed, bot kinds, config), so every game is
independently reproducible and the round-robin parallelises cleanly: results are identical
whether run with `jobs=1` or many workers. Metrics aggregation lives in `metrics.py`; this
module only *produces* the per-game `GameRecord`s.
"""

from __future__ import annotations

import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, replace
from typing import Callable, Optional

from ..bots.base import Bot
from ..bots.greedy_bot import GreedyBot, GreedyWeights
from ..bots.random_bot import RandomBot
from ..bots.referee_bot import RefereeBot
from ..bots.turn_bot import TurnBot
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
    final_food_a: int = 0
    final_food_b: int = 0
    # Full ordered action log (each action.to_dict()), populated only when play_game is called
    # with log_actions=True. Lets a game be replayed move-by-move with no bot compute (the bots'
    # search is bypassed - the stored actions are applied straight through the rules engine).
    actions: tuple = ()

    def credit(self, seat: str = "A") -> float:
        """Outcome credit for `seat`: 1.0 win, 0.5 draw, 0.0 loss."""
        if self.winner is None:
            return 0.5
        return 1.0 if self.winner == seat else 0.0

    def to_dict(self) -> dict:
        return {"deck_a": self.deck_a, "deck_b": self.deck_b, "seed": self.seed,
                "first_player": self.first_player, "winner": self.winner,
                "reason": self.reason, "turns": self.turns,
                "cards_drawn_a": sorted(self.cards_drawn_a),
                "cards_drawn_b": sorted(self.cards_drawn_b),
                "final_food_a": self.final_food_a,
                "final_food_b": self.final_food_b}


def crossed_progress_decile(done: int, total: int) -> bool:
    """Whether completing game `done` crossed the next 10% matchup milestone (progress pacing)."""
    return total > 0 and (done * 10) // total > ((done - 1) * 10) // total


BOT_KINDS = ("greedy", "lookahead", "random", "referee", "turn", "greedy_belief")

# 3-ply own-line lookahead (see GreedyBot's module docstring). Gauntlet-tested 2024: it does
# correctly find delayed/combo value 1-ply misses (e.g. Grizzly Bear), but nets *worse*
# overall win rate than plain greedy (-23 to -32% depending on depth/pool) against a real
# opponent - the passive filler opponent it searches against makes every simulated line
# look artificially safe, so it favours patient setups a live opponent punishes immediately.
# Kept here (opt-in only, never the default) as a validated negative result / building block
# for a future adversarial version, not as something to actually use for balance sim today.
LOOKAHEAD_DEPTH = 3
LOOKAHEAD_BEAM_WIDTH = 8

# RefereeBot (bots/referee_bot.py): the adversarial version the lookahead comment above
# anticipates - opponent replies are played by a real GreedyBot out of *determinized*
# hands, so lines get punished honestly. Cost is roughly (beam+1) x determinizations
# opponent-turn rollouts per decision. Referee v2 stages that work behind a root screen,
# reuses contingent plans, and caps pathological own-turn expansion; it remains the
# calibration tier rather than the high-throughput balance pilot.
REFEREE_DETERMINIZATIONS = 5
REFEREE_BEAM_WIDTH = 8
REFEREE_ROOT_WIDTH = 5
REFEREE_REPLY_WIDTH = 8
REFEREE_MAX_SEARCH_NODES = 150  # per retained root candidate

# TurnBot (bots/turn_bot.py): the scalable middle tier. It completes its own turn with the
# same determinized information-set search as the referee but stops at the turn boundary
# (no opponent-reply rollout), so it costs a small multiple of greedy rather than ~100x -
# the intended default pilot for large balance sims.
TURN_DETERMINIZATIONS = 3
TURN_BEAM_WIDTH = 8
# Per-root own-turn node budget (bots/turn_bot.py TURN_MAX_SEARCH_NODES). None = exhaustive; 80
# is a byte-identical-in-play speedup that caps the breadth blow-up on the deep decks.
TURN_MAX_SEARCH_NODES = 80

# 'greedy_belief' = GreedyBot + the coverage-exposure belief term (greedy_bot.py). A pure
# 1-ply eval add-on (no search) for A/B-ing whether belief-over-the-hidden-hand helps; the
# weight is untuned (mirrors own_hq_threat's scale) and only affects the 'greedy_belief' kind.
GREEDY_BELIEF_COVERAGE_EXPOSURE = 40.0


def make_bot(kind: str, seed: int, weights: Optional[GreedyWeights] = None,
             extra: Optional[dict] = None) -> Bot:
    """Construct a bot from a kind string (see `BOT_KINDS`) with a derived seed.

    `weights` overrides a greedy/lookahead bot's eval weights (default `GreedyWeights()` if
    omitted); it's ignored for 'random'. `extra` overrides the kind's default constructor
    kwargs (e.g. `{"deck_reveal_choice_width": 0}`, `{"determinizations": 2}`), so one A/B
    can compare configs of the same kind without a bespoke bot kind - the seam the paired
    benchmark uses to stay in its fixed-opponent design.
    """
    kind = kind.strip().lower()
    extra = dict(extra or {})
    if kind == "greedy":
        return GreedyBot(weights=weights, seed=seed, **extra)
    if kind == "greedy_belief":
        base = weights or GreedyWeights()
        belief = replace(base, coverage_exposure=GREEDY_BELIEF_COVERAGE_EXPOSURE)
        return GreedyBot(weights=belief, seed=seed, **extra)
    if kind == "lookahead":
        kw = dict(depth=LOOKAHEAD_DEPTH, beam_width=LOOKAHEAD_BEAM_WIDTH)
        kw.update(extra)
        return GreedyBot(weights=weights, seed=seed, **kw)
    if kind == "random":
        return RandomBot(seed=seed)
    if kind == "referee":
        kw = dict(determinizations=REFEREE_DETERMINIZATIONS, beam_width=REFEREE_BEAM_WIDTH,
                  root_width=REFEREE_ROOT_WIDTH, reply_width=REFEREE_REPLY_WIDTH,
                  max_search_nodes=REFEREE_MAX_SEARCH_NODES)
        kw.update(extra)
        return RefereeBot(weights=weights, seed=seed, **kw)
    if kind == "turn":
        kw = dict(determinizations=TURN_DETERMINIZATIONS, beam_width=TURN_BEAM_WIDTH,
                  max_search_nodes=TURN_MAX_SEARCH_NODES)
        kw.update(extra)
        return TurnBot(weights=weights, seed=seed, **kw)
    raise ValueError(f"unknown bot kind {kind!r} (expected one of {BOT_KINDS})")


def parse_bot_kind(kind: str, flag: str) -> str:
    """Validate one CLI bot-kind argument against BOT_KINDS, or exit with a usage error."""
    kind = kind.strip().lower()
    if kind not in BOT_KINDS:
        raise SystemExit(f"{flag} expects one of {'|'.join(BOT_KINDS)}, got {kind!r}")
    return kind


def _coerce_kwarg(value: str):
    """Coerce a CLI kwarg string to int -> float -> bool -> str."""
    for cast in (int, float):
        try:
            return cast(value)
        except ValueError:
            pass
    low = value.lower()
    return low == "true" if low in ("true", "false") else value


def parse_bot_spec(spec: str, flag: str) -> tuple[str, tuple]:
    """Parse a `kind[:k=v,k=v]` bot spec into `(kind, ((k, v), ...))` for `make_bot`'s `extra`.

    Lets one A/B compare configs of the *same* kind through the paired benchmark without a
    bespoke bot kind, e.g. `turn:deck_reveal_choice_width=0` or
    `referee:reply_width=8,max_search_nodes=150`. Values coerce int -> float -> bool -> str.
    """
    head, _, tail = spec.partition(":")
    kind = parse_bot_kind(head, flag)
    kwargs = []
    for item in filter(None, tail.split(",")):
        if "=" not in item:
            raise SystemExit(f"{flag}: bad kwarg {item!r} (expected key=value)")
        key, value = item.split("=", 1)
        kwargs.append((key.strip(), _coerce_kwarg(value.strip())))
    return kind, tuple(kwargs)


def parse_bot_pair(spec: str) -> tuple[str, str]:
    """Validate a `--bots a,b` CLI argument (two of BOT_KINDS), or exit with a usage error."""
    parts = spec.split(",")
    if len(parts) != 2 or any(p.strip().lower() not in BOT_KINDS for p in parts):
        raise SystemExit(f"--bots expects two of {'|'.join(BOT_KINDS)}, e.g. greedy,greedy")
    return parts[0].strip().lower(), parts[1].strip().lower()


def play_game(
    deck_a: str,
    deck_b: str,
    seed: int,
    *,
    bot_a: Bot,
    bot_b: Bot,
    config: Optional[Config] = None,
    map_id: str = "map_b",
    log_actions: bool = False,
    first_player: Optional[str] = None,
) -> GameRecord:
    """Play one headless game and return its record. Mirrors the cli.play loop.

    With `log_actions=True` the returned record carries the full ordered action log, so the
    game can be replayed move-by-move later without re-invoking the bots (see sim/replay.py).
    `first_player`, if given, forces who moves first instead of the seed's coin flip (see
    `engine.state.new_game`) - used to deliberately split a matchup's games evenly by mover
    rather than leaving it to chance.
    """
    state = new_game(load_premade_deck(deck_a), load_premade_deck(deck_b), seed,
                     map_id=map_id, config=config, first_player=first_player)
    bots = {"A": bot_a, "B": bot_b}

    drawn: dict[str, set[str]] = {"A": set(), "B": set()}
    trace: list[dict] = []

    def _snapshot_hands() -> None:
        for seat in ("A", "B"):
            drawn[seat].update(u.card_id for u in state.hands[seat])

    _snapshot_hands()  # opening hand
    result = rules.is_terminal(state)
    while result is None:
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        action = bots[actor].choose(state.view_for(actor), legal, state)
        if log_actions:
            trace.append(action.to_dict())
        rules.apply_action(state, action)
        _snapshot_hands()  # catches draws, bounces, tutors - anything that touches hands
        result = rules.is_terminal(state)

    return GameRecord(deck_a, deck_b, seed, state.first_player,
                      result.winner, result.reason, state.turn_counter,
                      frozenset(drawn["A"]), frozenset(drawn["B"]),
                      state.food["A"], state.food["B"], tuple(trace))


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
    map_id: str = "map_b"
    weights_a: Optional[GreedyWeights] = None
    weights_b: Optional[GreedyWeights] = None
    # Per-seat constructor-kwarg overrides as picklable (key, value) tuples (e.g.
    # (("deck_reveal_choice_width", 0),)); empty => the kind's default config.
    kwargs_a: tuple = ()
    kwargs_b: tuple = ()
    log_actions: bool = False
    # Forces who moves first (see `play_game`); None leaves it to the seed's coin flip.
    first_player: Optional[str] = None


def _run_spec(spec: MatchSpec, config: Optional[Config] = None) -> GameRecord:
    bot_a = make_bot(spec.bot_a, seed=spec.seed * 2 + 1, weights=spec.weights_a,
                     extra=dict(spec.kwargs_a))
    bot_b = make_bot(spec.bot_b, seed=spec.seed * 2 + 2, weights=spec.weights_b,
                     extra=dict(spec.kwargs_b))
    return play_game(spec.deck_a, spec.deck_b, spec.seed,
                     bot_a=bot_a, bot_b=bot_b, config=config, map_id=spec.map_id,
                     log_actions=spec.log_actions, first_player=spec.first_player)


def run_specs(
    specs: list[MatchSpec],
    *,
    config: Optional[Config] = None,
    jobs: int = 1,
) -> list[GameRecord]:
    """Run an arbitrary deterministic schedule, preserving its input order.

    Most callers should use :func:`run_pairs`. Analysis designs that vary pilots and decks
    game-by-game (notably the factored pilot-rating experiment) use this lower-level entry
    point rather than reimplementing process-pool or bot construction plumbing.
    """
    if jobs <= 1:
        return [_run_spec(spec, config) for spec in specs]
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(_run_spec, specs, [config] * len(specs)))


def run_spec_pair(
    specs: tuple[MatchSpec, MatchSpec],
    config: Optional[Config] = None,
) -> tuple[GameRecord, GameRecord]:
    """Run both seat assignments for one paired seed in a single worker."""
    return (_run_spec(specs[0], config), _run_spec(specs[1], config))


def run_matchup(
    deck_a: str,
    deck_b: str,
    n_games: int,
    base_seed: int = 0,
    *,
    bots: tuple[str, str] = ("greedy", "greedy"),
    weights: tuple[Optional[GreedyWeights], Optional[GreedyWeights]] = (None, None),
    config: Optional[Config] = None,
    map_id: str = "map_b",
) -> list[GameRecord]:
    """`n_games` of deck_a vs deck_b with distinct seeds (first player varies via the flip)."""
    specs = [MatchSpec(deck_a, deck_b, base_seed + i, bots[0], bots[1], map_id,
                       weights[0], weights[1])
             for i in range(n_games)]
    return [_run_spec(s, config) for s in specs]


def run_pairs(
    pairs: list[tuple[str, str]],
    n_games: int,
    base_seed: int = 0,
    *,
    bots: tuple[str, str] = ("greedy", "greedy"),
    weights: tuple[Optional[GreedyWeights], Optional[GreedyWeights]] = (None, None),
    bot_kwargs: tuple[tuple, tuple] = ((), ()),
    config: Optional[Config] = None,
    map_id: str = "map_b",
    jobs: int = 1,
    log_actions: bool = False,
    progress: Optional[Callable[[str, str, int, int], None]] = None,
    game_progress: Optional[Callable[[str, str, int, int], None]] = None,
    matchup_progress: Optional[
        Callable[[str, str, int, int, list[GameRecord]], None]
    ] = None,
) -> list[GameRecord]:
    """Every (a, b) pair in `pairs`, same bot kinds/weights throughout, unordered (each pair
    appears once - do not also pass its reverse).

    A mirror pair (`a == b`) runs `n_games` games with the seed's natural coin flip deciding
    first player (forcing a mover is meaningless when both decks are identical). A non-mirror
    pair runs `2 * n_games` games: `n_games` with `a` forced to move first, then `n_games` with
    `b` forced to move first - a deliberate, controlled split of the mover axis instead of
    leaving it to chance, so `a`'s and `b`'s win rates against each other come from one pooled
    sample rather than two disconnected ones.

    `jobs > 1` fans games out over a process pool; because each game is seed-determined the
    aggregate is identical regardless of `jobs`. Seed blocks are assigned per pair in order
    (mirror pairs consume `n_games` seeds, non-mirror pairs consume `2 * n_games`), so every
    game across the whole schedule gets a distinct seed. Pairs are run one at a time (still
    spread across all `jobs` workers within each pair); `progress`, if given, is called after
    every completed pair as `progress(a, b, pairs_done, pairs_total)`. `game_progress`, if
    given, is called after every individual game finishes *within* the current pair, as
    `game_progress(a, b, games_done, pair_games)` - finer-grained than `progress` for watching a
    single slow (e.g. referee-piloted) matchup tick over. `matchup_progress`, if given, is
    called after each pair with the completed pair's records as its fifth argument. Games can
    complete out of order under `jobs > 1`, but the returned records preserve the original
    (pair, seed) order.
    """
    records: list[GameRecord] = []

    def _pair_specs(pair_seed: int, a: str, b: str) -> list[MatchSpec]:
        if a == b:
            return [MatchSpec(a, b, pair_seed + i, bots[0], bots[1], map_id,
                              weights[0], weights[1], bot_kwargs[0], bot_kwargs[1],
                              log_actions=log_actions)
                    for i in range(n_games)]
        specs = []
        for half, mover in enumerate(("A", "B")):
            offset = pair_seed + half * n_games
            specs += [MatchSpec(a, b, offset + i, bots[0], bots[1], map_id,
                                weights[0], weights[1], bot_kwargs[0], bot_kwargs[1],
                                log_actions=log_actions, first_player=mover)
                      for i in range(n_games)]
        return specs

    def _run_batch(ex: Optional[ProcessPoolExecutor], a: str, b: str,
                   specs: list[MatchSpec]) -> list[GameRecord]:
        if game_progress is None:
            return ([_run_spec(s, config) for s in specs] if ex is None
                    else list(ex.map(_run_spec, specs, [config] * len(specs))))
        if ex is None:
            results = []
            for i, s in enumerate(specs):
                results.append(_run_spec(s, config))
                game_progress(a, b, i + 1, len(specs))
            return results
        results: list[Optional[GameRecord]] = [None] * len(specs)
        futures = {ex.submit(_run_spec, s, config): i for i, s in enumerate(specs)}
        done = 0
        for fut in as_completed(futures):
            results[futures[fut]] = fut.result()
            done += 1
            game_progress(a, b, done, len(specs))
        return results

    def _run_all(ex: Optional[ProcessPoolExecutor]) -> None:
        seed_cursor = base_seed
        for pair_index, (a, b) in enumerate(pairs):
            specs = _pair_specs(seed_cursor, a, b)
            seed_cursor += len(specs)
            batch = _run_batch(ex, a, b, specs)
            records.extend(batch)
            if matchup_progress is not None:
                matchup_progress(a, b, pair_index + 1, len(pairs), batch)
            if progress is not None:
                progress(a, b, pair_index + 1, len(pairs))

    if jobs <= 1:
        _run_all(None)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as ex:
            _run_all(ex)
    return records


def run_round_robin(
    slugs: list[str],
    n_games: int,
    base_seed: int = 0,
    *,
    bots: tuple[str, str] = ("greedy", "greedy"),
    config: Optional[Config] = None,
    map_id: str = "map_b",
    jobs: int = 1,
    progress: Optional[Callable[[str, str, int, int], None]] = None,
    game_progress: Optional[Callable[[str, str, int, int], None]] = None,
    matchup_progress: Optional[
        Callable[[str, str, int, int, list[GameRecord]], None]
    ] = None,
) -> list[GameRecord]:
    """Every unordered non-mirror deck pair, `2 * n_games` each (see `run_pairs`) - mirrors are
    excluded (a deck-vs-itself win rate is a poor, matchup-dependent proxy for turn-order
    advantage and isn't worth the extra games)."""
    pairs = [(a, b) for i, a in enumerate(slugs) for b in slugs[i + 1:]]
    return run_pairs(pairs, n_games, base_seed, bots=bots, config=config,
                     map_id=map_id, jobs=jobs, progress=progress,
                     game_progress=game_progress, matchup_progress=matchup_progress)
