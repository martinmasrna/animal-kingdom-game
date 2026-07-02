"""The rules: legal-action generation, action application, and terminal detection.

Three functions form the engine's contract (handoff §4):
  - legal_actions(state) -> list[Action]
  - apply_action(state, action) -> GameState   (mutates in place, returns same object)
  - is_terminal(state) -> Optional[Result]

rules.py orchestrates the turn structure and win conditions; the placement mechanic,
card effects, and the effect-stack interpreter live in effects.py (which this imports).
A turn ends only when resolution is complete (effect stack empty & nothing pending) -
the decision-point gate. legal_actions iterates sorted collections so the action order
is identical across processes (seed-based replay).
"""

from __future__ import annotations

from typing import Optional

from . import effects
from .actions import Action, DrawAction, PlaceAction
from .state import EngineError, GameState, Result, other_player
from .strength import effective_strength  # re-exported (used by tests / future eval)

__all__ = [
    "legal_actions", "apply_action", "is_terminal",
    "owner_of", "top_unit", "regions_controlled", "effective_strength",
]


# -------------------------------------------------------- board query re-exports

def owner_of(state: GameState, cr: str) -> Optional[str]:
    return state.owner_of(cr)


def top_unit(state: GameState, cr: str):
    return state.top_unit(cr)


# --------------------------------------------------------------- legal actions

def legal_actions(state: GameState) -> list[Action]:
    """Every legal action for the player to act. Empty list ⇒ exhaustion (see is_terminal)."""
    if state.result is not None:
        return []
    if state.pending is not None:          # mid-resolution: offer the sub-choices
        return effects.legal_pending(state)
    return _top_level_actions(state)


def _top_level_actions(state: GameState) -> list[Action]:
    player = state.current
    actions: list[Action] = []
    if state.decks[player] and len(state.hands[player]) < state.config.hand_limit:
        actions.append(DrawAction())
    actions.extend(effects.legal_placements(state, player))
    return actions


# ------------------------------------------------------------- apply / resolve

def apply_action(state: GameState, action: Action) -> GameState:
    """Apply one action (a top-level move or a pending sub-choice), mutating `state`."""
    if state.result is not None:
        raise EngineError("cannot act: the game is over")

    if state.pending is not None:
        effects.apply_pending(state, action)
    elif isinstance(action, DrawAction):
        state.actions_taken_this_turn += 1
        _do_draw(state, state.current)
    elif isinstance(action, PlaceAction):
        state.actions_taken_this_turn += 1
        effects.do_placement(state, state.current, action.card_id, action.target)
    else:
        raise EngineError(f"unexpected action {action!r}")

    _resolve_and_maybe_end_turn(state)
    return state


def _do_draw(state: GameState, player: str) -> None:
    # Draw up to the per-action count, capped by the hand limit (state.draw caps by deck).
    n = min(state.config.draw_action_count, state.config.hand_limit - len(state.hands[player]))
    effects.draw_cards(state, player, n)    # the wrapper fires ON_DRAW (Eon, Black Swan, ...)


def _resolve_and_maybe_end_turn(state: GameState) -> None:
    """Drain pending effects; end the turn only when resolution is fully complete
    and the player has no turn actions left (config.actions_per_turn)."""
    effects.resolve(state)
    if state.result is not None:
        return  # game decided (HQ capture / food)
    if state.effect_stack or state.pending is not None:
        return  # still resolving (a choice is pending or steps remain)
    if (state.actions_taken_this_turn < state.config.actions_per_turn
            and _top_level_actions(state)):
        return  # actions remain and something is playable: the turn stays open
    _end_turn(state)


def _end_turn(state: GameState) -> None:
    player = state.current
    effects.end_of_turn(state, player)      # on_end_of_turn triggers (Dingo, Worker Wasp, Methuselah)
    effects.resolve(state)                  # choice-free by design, so it drains fully
    if state.result is not None:
        return  # an end-of-turn food gain could already win
    _produce_food(state, player)            # end-of-turn region income
    if state.result is not None:
        return  # food win
    state.turn_counter += 1
    state.units_placed_this_turn = 0
    state.actions_taken_this_turn = 0
    state.turn_flags = {}                    # reset once-per-turn trigger flags
    state.current = other_player(player)
    # Start of the new player's turn: delayed effects + start-of-turn triggers, then resolve.
    effects.start_of_turn(state, state.current)
    effects.resolve(state)


# ------------------------------------------------------------- regions / food

def regions_controlled(state: GameState, player: str):
    """Regions where `player` occupies every corner (overview.md §10)."""
    gm = state.game_map
    return [r for r in gm.regions.values()
            if all(state.owner_of(c) == player for c in r.corners)]


def _produce_food(state: GameState, player: str) -> None:
    total = sum(r.food for r in regions_controlled(state, player))
    if total:
        effects.gain_food(state, player, total)  # sets result on win; applies Queen Bee


# ------------------------------------------------------------------ terminal

def is_terminal(state: GameState) -> Optional[Result]:
    """The game's Result if over, else None. Authoritative (also detects exhaustion)."""
    if state.result is not None:
        return state.result
    if state.turn_counter >= state.config.max_turns:
        return _resolve_by_food(state, "max_turns")
    if not legal_actions(state):
        return _resolve_exhaustion(state)
    return None


def _resolve_exhaustion(state: GameState) -> Result:
    # overview.md §11.3: more food wins; on a tie, the player who cannot act loses.
    fa, fb = state.food["A"], state.food["B"]
    if fa > fb:
        return Result("A", "exhaustion")
    if fb > fa:
        return Result("B", "exhaustion")
    return Result(other_player(state.current), "exhaustion")


def _resolve_by_food(state: GameState, reason: str) -> Result:
    fa, fb = state.food["A"], state.food["B"]
    if fa > fb:
        return Result("A", reason)
    if fb > fa:
        return Result("B", reason)
    return Result(None, reason)  # draw
