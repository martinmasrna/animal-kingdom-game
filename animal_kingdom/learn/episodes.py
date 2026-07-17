"""Self-play episode generation for TD training.

`EpisodeSpec` is a picklable, seed-determined recipe for one training game - it carries the
*current* weight snapshot directly (a plain tuple, not a file path: the weights change every
training iteration, unlike the static named artifacts `bots.learned_eval.load_eval` resolves
for deployed bots), so a batch of specs is a pure function of `(TrainConfig, iteration)` and
`play_episode` is a plain module-level function safe to hand to `ProcessPoolExecutor` (Windows
spawn-safe: no closures, no unpicklable state).

`Trajectory` is one learner seat's recorded decision points from a finished episode: the
"afterstate" feature vectors (the states search actually scores - right after that seat's own
placement/draw, before the opponent replies) plus the eventual terminal outcome from that
seat's perspective. `ExplorationBot` is the training-only policy that generates them: a real
`GreedyBot` (so its choices reflect the weights actually being trained) wrapped with
epsilon-greedy exploration and afterstate recording.

Deck sampling draws from the "36 unordered pairs" pool: the 7 premade decks plus the
`sim.benchmark_set` calibration rig (`baseline`, a single-copy 30-card yardstick deck) - 8
decks, C(8,2)+8 = 36 unordered pairs including mirrors. `ensure_baseline_registered` must run
in every process that will call `play_episode` with the `"baseline"` deck (workers included -
see its docstring).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from ..bots.base import Bot
from ..bots.greedy_bot import GreedyBot
from ..bots import features
from ..decks import load_premade_deck
from ..engine import rules
from ..engine.actions import Action
from ..engine.config import Config
from ..engine.state import GameState, StateView, new_game, other_player
from ..sim.benchmark_set import DECKLIST as _BASELINE_DECKLIST
from ..sim.deck_optimizer import register_synthetic

BASELINE_SLUG = "baseline"


def ensure_baseline_registered() -> None:
    """Register the `sim.benchmark_set` calibration rig under `"baseline"` so
    `load_premade_deck("baseline")` works in *this* process.

    Idempotent (safe to call every time): `register_synthetic` re-publishes the same fixed
    decklist and re-writes the `$AK_EXTRA_DECKS` env var each call, so calling it once in the
    training driver before spawning the worker pool is enough for the env var to propagate to
    spawned workers (see `decks.py`'s `_load_env_extra_decks`); calling it again from a worker
    (e.g. this module's own import, as a safety net) is a harmless no-op recomputation.
    """
    register_synthetic(BASELINE_SLUG, _BASELINE_DECKLIST)


def deck_pool() -> tuple[str, ...]:
    """The 8 decks episodes sample from: the 7 premades + the calibration rig."""
    from ..engine.cards import DECK_SLUGS

    return tuple(sorted(DECK_SLUGS)) + (BASELINE_SLUG,)


def all_deck_pairs() -> tuple[tuple[str, str], ...]:
    """Every unordered pair (including mirrors) of `deck_pool()` - 36 for the 8-deck pool."""
    pool = deck_pool()
    return tuple(
        (pool[i], pool[j])
        for i in range(len(pool))
        for j in range(i, len(pool))
    )


@dataclass(frozen=True)
class EpisodeSpec:
    """A picklable, fully seed-determined recipe for one self-play training game."""

    deck_a: str
    deck_b: str
    seed: int
    feature_set: str
    weights: tuple[float, ...]        # the frozen w_k snapshot (features.feature_names() order)
    bias: float = 0.0
    map_id: str = "map_b"
    epsilon: float = 0.05
    # Which seat (if any) plays a plain hand-eval GreedyBot instead of the evaluator-under-
    # training - the anti-collapse anchor mix. None => both seats are learners (self-play).
    anchor_seat: Optional[str] = None


@dataclass
class Trajectory:
    """One learner seat's recorded experience from a finished episode."""

    seat: str
    deck: str
    opponent_deck: str
    seed: int
    phis: list           # list[list[float]]: feature_names(feature_set)-ordered vectors, in
                          # play order, one per non-terminal afterstate this seat produced
    outcome: float        # z in {0.0, 0.5, 1.0} from `seat`'s perspective


class ExplorationBot(Bot):
    """Training-only wrapper: with probability `epsilon`, picks a uniformly random legal
    action instead of the wrapped policy's choice, so self-play doesn't collapse onto one
    deterministic line turn after turn. Every decision's resulting afterstate is recorded
    into `trajectory` regardless of whether it was the greedy or the random branch - both are
    real experience under the *current* weights, which is what TD should learn from.

    Wraps a real `GreedyBot(evaluator=...)` for its greedy branch (rather than reimplementing
    scoring) so its choices - and thus the recorded trajectory - reflect the exact weights
    being trained, including the lethal-avoidance/fizzle-penalty policy logic GreedyBot
    already carries.
    """

    def __init__(self, evaluator, feature_set: str, rng: random.Random, epsilon: float = 0.05):
        self._policy = GreedyBot(seed=None, rng=rng, evaluator=evaluator)
        self.feature_set = feature_set
        self.rng = rng
        self.epsilon = epsilon
        self.trajectory: list = []

    def choose(
        self,
        view: StateView,
        legal,
        state: Optional[GameState] = None,
    ) -> Action:
        legal = list(legal)
        if state is not None and self.epsilon and len(legal) > 1 and self.rng.random() < self.epsilon:
            action = self.rng.choice(legal)
        else:
            action = self._policy.choose(view, legal, state)
        if state is not None:
            nxt = state.clone()
            rules.apply_action(nxt, action)
            if nxt.result is None:
                self.trajectory.append(features.extract(nxt, view.player, self.feature_set))
        return action


def _outcome_for(result, seat: str) -> float:
    if result.winner is None:
        return 0.5
    return 1.0 if result.winner == seat else 0.0


def play_episode(spec: EpisodeSpec) -> list[Trajectory]:
    """Play one full self-play game per `spec` and return the learner seat(s)' trajectories.

    Module-level (not a closure/method) and `spec` is a plain picklable dataclass, so this is
    safe to pass directly to `ProcessPoolExecutor.map` (Windows spawn-safe). Re-registers the
    baseline rig defensively (idempotent - see `ensure_baseline_registered`) so a worker that
    somehow never inherited `$AK_EXTRA_DECKS` still works.
    """
    ensure_baseline_registered()
    from ..bots.learned_eval import LinearEval

    evaluator = LinearEval(feature_set=spec.feature_set, weights=spec.weights, bias=spec.bias)
    config = Config.default()
    state = new_game(load_premade_deck(spec.deck_a), load_premade_deck(spec.deck_b), spec.seed,
                     map_id=spec.map_id, config=config)

    learners: dict[str, ExplorationBot] = {}
    bots: dict[str, Bot] = {}
    for seat, seed_offset in (("A", 1), ("B", 2)):
        seat_seed = spec.seed * 2 + seed_offset
        if spec.anchor_seat == seat:
            bots[seat] = GreedyBot(seed=seat_seed)   # plain hand eval - no learning, no exploration
        else:
            eb = ExplorationBot(evaluator=evaluator, feature_set=spec.feature_set,
                                rng=random.Random(seat_seed), epsilon=spec.epsilon)
            bots[seat] = eb
            learners[seat] = eb

    result = rules.is_terminal(state)
    while result is None:
        actor = state.player_to_act()
        legal = rules.legal_actions(state)
        action = bots[actor].choose(state.view_for(actor), legal, state)
        rules.apply_action(state, action)
        result = rules.is_terminal(state)

    decks = {"A": spec.deck_a, "B": spec.deck_b}
    return [
        Trajectory(
            seat=seat, deck=decks[seat], opponent_deck=decks[other_player(seat)],
            seed=spec.seed, phis=eb.trajectory, outcome=_outcome_for(result, seat),
        )
        for seat, eb in learners.items()
    ]
