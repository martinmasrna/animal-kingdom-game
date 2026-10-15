"""The bots' mulligan: keep the opening hand, or send back the card whose replacement plays best.

The mulligan returns one card at a time (overview.md §4.4), so this answers one step: keep, or send back one card. Each
option is tried in sampled worlds (my deck's order is hidden from me too, so `determinize` re-deals it and the engine
draws the replacement from there); in each, my first turns and the opponent's are played out by the greedy policy (the
opponent from a hand re-dealt from its decklist, so removal has something to hit), and the position is scored by the
evaluation. The option with the best average wins, keeping on a tie, so a
hand is only changed for a clear gain. What it measures is what the hand can do on the board: four Muskrats with no
Squirrel to start them score badly, a Squirrel beside them well. Generic and honest: no card ids, and nothing hidden is
read (the opponent's cards are re-dealt in every world).
"""

from __future__ import annotations

import random
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import SKIP, Action, ChoiceAction
from ..engine.state import GameState
from .determinize import determinize

MULLIGAN_SAMPLES = 6     # worlds per option
MULLIGAN_TURNS = 2       # my turns played out in each world
MULLIGAN_MARGIN = 1.0    # how much better than keeping an option must score to be taken


def mulligan_choice(state: GameState, me: str, legal: Sequence[Action], rng: random.Random, weights,
                    samples: int = MULLIGAN_SAMPLES, turns: int = MULLIGAN_TURNS) -> Action:
    """Keep (SKIP) or the hand card to send back, at one step of `me`'s mulligan."""
    from .greedy_bot import GreedyBot   # local: greedy_bot imports this module's caller

    keep = next(a for a in legal if isinstance(a, ChoiceAction) and a.choice == SKIP)
    by_card: dict[str, Action] = {}
    for u in state.hands[me]:
        a = ChoiceAction(u.iid)
        if a in legal and u.card_id not in by_card:
            by_card[u.card_id] = a          # copies of a card are the same option
    if not by_card:
        return keep
    policy = GreedyBot(weights=weights, seed=rng.getrandbits(32))
    seeds = [rng.getrandbits(64) for _ in range(samples)]   # the same worlds for every option: a paired comparison

    def score(option: Optional[Action]) -> float:
        total = 0.0
        for seed in seeds:
            world = determinize(state, me, random.Random(seed))
            if option is not None:          # a clone keeps the hand's instance ids
                rules.apply_action(world, option, validate=False)
            total += _play_out(world, me, policy, turns)
        return total / len(seeds)

    base = score(None)
    best, best_score = keep, base + MULLIGAN_MARGIN
    for action in by_card.values():
        s = score(action)
        if s > best_score:
            best, best_score = action, s
    return best


def _play_out(world: GameState, me: str, policy, turns: int) -> float:
    """Finish both mulligans keeping, then play `turns` of my turns (and the opponent's between) with `policy`; score."""
    from .greedy_bot import evaluate
    guard = 0
    while world.result is None and guard < 200:
        guard += 1
        actor = world.player_to_act()
        if world.pending is not None and world.pending.get("kind") == "mulligan":
            rules.apply_action(world, ChoiceAction(SKIP), validate=False)
            continue
        legal = rules.legal_actions(world)
        if not legal:
            break
        before = world.turn_counter
        action = policy.choose(world.view_for(actor), legal, world)
        rules.apply_action(world, action, validate=False)
        if actor == me and world.turn_counter != before and world.pending is None:
            turns -= 1
            if turns <= 0:
                break
    return evaluate(world, me, policy.weights)
