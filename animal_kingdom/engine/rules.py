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

from . import effects, statics
from .actions import Action, DrawAction, PassAction, PlaceAction, RoamAction
from .state import EngineError, GameState, Result, other_player
from .strength import effective_strength  # re-exported (used by tests / future eval)

__all__ = [
    "legal_actions", "apply_action", "is_terminal", "can_pass",
    "owner_of", "top_unit", "regions_controlled", "region_income", "effective_strength",
]


# -------------------------------------------------------- board query re-exports

def owner_of(state: GameState, cr: str) -> Optional[str]:
    return state.owner_of(cr)


def top_unit(state: GameState, cr: str):
    return state.top_unit(cr)


# --------------------------------------------------------------- legal actions

def legal_actions(state: GameState) -> list[Action]:
    """Every legal action for the player to act. Empty only once the game is over: a turn that
    opens with nothing to do passes at once (_end_turn)."""
    if state.result is not None:
        return []
    if state.pending is not None:          # mid-resolution: offer the sub-choices
        return effects.legal_pending(state)
    return _top_level_actions(state)


def can_pass(state: GameState) -> bool:
    """Ending the turn early, even before any action, is allowed while nothing is resolving.
    It is kept out of legal_actions: bots never pass."""
    return state.result is None and state.pending is None and not state.effect_stack


def _top_level_actions(state: GameState) -> list[Action]:
    player = state.current
    left = _actions_left(state)
    if left <= 0:                                  # the turn stays open only for a free roam (Roam)
        return list(effects.legal_roams(state, player, free_only=True)) if effects.free_roams_left(state, player) else []
    actions: list[Action] = []
    if state.decks[player]:
        actions.append(DrawAction())
    actions.extend(effects.legal_placements(state, player, titan_ok=left >= TITAN_ACTIONS))
    actions.extend(effects.legal_roams(state, player))
    return actions


TITAN_ACTIONS = 2   # Titan (keywords.md): playing it costs two actions instead of one


def _actions_left(state: GameState) -> int:
    limit = (state.config.actions_per_turn
             + state.turn_flags.get(f"bonus_actions_{state.current}", 0))  # Beaver
    return limit - state.actions_taken_this_turn


# ------------------------------------------------------------- apply / resolve

def early_mulligan(state: GameState, player: str) -> Optional[int]:
    """Where `player`'s mulligan waits under the one being chosen now, if it does: both players mulligan at once
    (overview.md §4.4), though the stack resolves one step at a time. Its index on the effect stack, else None."""
    if not state.pending or state.pending.get("kind") != "mulligan" or state.pending.get("chooser") == player:
        return None
    return next((i for i, st in enumerate(state.effect_stack[:-1]) if st["op"] == "mulligan" and st["player"] == player), None)


def mulligan_request(state: GameState, player: str) -> dict:
    return {"mode": "choice", "chooser": player, "optional": True, "kind": "mulligan",
            "options": [u.iid for u in state.hands[player]]}


def apply_early_mulligan(state: GameState, player: str, action: Action) -> None:
    """Apply `player`'s mulligan choice while the other player is still choosing theirs: their step comes to the top,
    takes the choice (a returned card is replaced at once), and goes back under the other's if it isn't done. A step
    that finishes leaves the other's request pending as before."""
    i = early_mulligan(state, player)
    if i is None:
        raise EngineError("not your decision")
    stack, waiting = state.effect_stack, state.pending
    step = stack.pop(i); stack.append(step)
    state.pending = mulligan_request(state, player)
    try:
        apply_action(state, action)
    except Exception:
        stack.remove(step); stack.insert(i, step); state.pending = waiting
        raise
    if state.pending and state.pending.get("chooser") == player and stack and stack[-1] is step:   # more to choose: back underneath
        stack.pop(); stack.insert(i, step)
        state.pending = waiting


def apply_logged(state: GameState, adict: dict) -> None:
    """Apply one action as a game log records it: one marked "by" a player is their mulligan choice made while the other
    player was choosing theirs (apply_early_mulligan); the rest go through apply_action."""
    from .actions import action_from_dict
    by, action = adict.get("by"), action_from_dict(adict)
    if by and early_mulligan(state, by) is not None:
        apply_early_mulligan(state, by, action)
    else:
        apply_action(state, action)


def apply_action(state: GameState, action: Action, *, validate: bool = True) -> GameState:
    """Apply one action (a top-level move or a pending sub-choice), mutating `state`.

    Raises EngineError unless `action` is in `legal_actions(state)`. Bot search, which only
    ever applies actions it just drew from `legal_actions`, passes `validate=False` to skip
    regenerating them."""
    if state.result is not None:
        raise EngineError("cannot act: the game is over")
    if isinstance(action, PassAction):
        if not can_pass(state):
            raise EngineError("cannot end the turn mid-resolution")
        _end_turn(state)
        return state
    if validate and action not in legal_actions(state):
        raise EngineError(f"illegal action {action!r}")

    if state.pending is not None:
        effects.apply_pending(state, action)
    elif isinstance(action, DrawAction):
        state.actions_taken_this_turn += 1
        _do_draw(state, state.current)
    elif isinstance(action, PlaceAction):
        titan = "Titan" in state.cards[action.card_id].keywords
        state.actions_taken_this_turn += TITAN_ACTIONS if titan else 1
        effects.do_placement(state, state.current, action.card_id, action.target)
    elif isinstance(action, RoamAction):
        stack = state.board.get(action.origin)
        effects.pay_for_roam(state, state.current, stack[-1] if stack else None)
        effects.do_roam(state, state.current, action.origin, action.target)
    else:
        raise EngineError(f"unexpected action {action!r}")

    _resolve_and_maybe_end_turn(state)
    return state


def _do_draw(state: GameState, player: str) -> None:
    # Cards past the hand limit burn (effects._fire_draw); state.draw caps by deck.
    effects.draw_cards(state, player, state.config.draw_action_count)    # the wrapper fires ON_DRAW (Eon, Black Swan, ...)


def _resolve_and_maybe_end_turn(state: GameState) -> None:
    """Drain pending effects; end the turn only when resolution is fully complete
    and the player has no turn actions left (config.actions_per_turn)."""
    effects.resolve(state)
    if state.result is not None:
        return  # game decided (HQ capture / food)
    if state.effect_stack or state.pending is not None:
        return  # still resolving (a choice is pending or steps remain)
    if _top_level_actions(state):
        return  # actions (or a free roam) remain and something is playable: the turn stays open
    _end_turn(state)


def _end_turn(state: GameState) -> None:
    player = state.current
    state.emit("turn_end", player=player)
    effects.end_of_turn(state, player)      # on_end_of_turn triggers (Dingo, Worker Wasp, Methuselah)
    effects.resolve(state)                  # choice-free by design, so it drains fully
    if state.result is not None:
        return  # an end-of-turn food gain could already win
    _produce_food(state, player)            # end-of-turn region income
    if state.result is not None:
        return  # food win
    # Both players ending a turn without acting, back to back, ends the game (more food wins;
    # on a tie, the player whose pass ended it loses). A player with no move passes too.
    acted = state.actions_taken_this_turn or state.turn_flags.get(f"roams_{player}")   # a free roam is acting too
    state.idle_turns = 0 if acted else state.idle_turns + 1
    if state.idle_turns >= 2:
        state.result = _resolve_passes(state)
        return
    state.turn_counter += 1
    state.units_placed_this_turn = 0
    state.actions_taken_this_turn = 0
    state.turn_flags = {}                    # reset once-per-turn trigger flags
    if state.inked:                          # ink that has worn off
        state.inked = {i: t for i, t in state.inked.items() if t > state.turn_counter}
    state.current = other_player(player)
    state.emit("turn_start", player=state.current, turn=state.turn_counter)
    # Start of the new player's turn: delayed effects + start-of-turn triggers, then resolve.
    effects.start_of_turn(state, state.current)
    effects.resolve(state)
    # A player who can neither draw nor place nor roam passes; the game goes on.
    if state.result is None and state.pending is None and not state.effect_stack \
            and not _top_level_actions(state):
        _end_turn(state)


# ------------------------------------------------------------- regions / food

def regions_controlled(state: GameState, player: str):
    """Regions where `player` occupies every corner (overview.md §10)."""
    return statics.regions_of(state, player)


def region_income(state: GameState, player: str) -> int:
    """Food `player`'s regions produce at the end of their turn: each its printed food, moved by the legendary
    Wildebeest and Boar (never below nothing); 0 while they control the Unnamed Giant ("Your regions produce no food")."""
    if statics.regions_starved(state, player):
        return 0
    mod = statics.region_food_modifier(state, player)
    return sum(max(0, r.food + mod) for r in regions_controlled(state, player))


def _produce_food(state: GameState, player: str) -> None:
    total = region_income(state, player)
    if total:
        effects.gain_food(state, player, total, income=True)  # sets result on win; applies Queen Bee


# ------------------------------------------------------------------ terminal

def is_terminal(state: GameState) -> Optional[Result]:
    """The game's Result if over, else None. Authoritative (also detects the turn limit)."""
    if state.result is not None:
        return state.result
    if state.turn_counter >= state.config.max_turns:
        return _resolve_by_food(state, "max_turns")
    return None


def _resolve_passes(state: GameState) -> Result:
    # more food wins; on a tie, the player who passed last loses.
    food_a, food_b = state.food["A"], state.food["B"]
    if food_a > food_b:
        return Result("A", "passes")
    if food_b > food_a:
        return Result("B", "passes")
    return Result(other_player(state.current), "passes")


def _resolve_by_food(state: GameState, reason: str) -> Result:
    food_a, food_b = state.food["A"], state.food["B"]
    if food_a > food_b:
        return Result("A", reason)
    if food_b > food_a:
        return Result("B", reason)
    return Result(None, reason)  # draw
