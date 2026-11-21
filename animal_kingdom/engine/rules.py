"""The rules: legal actions, applying an action, the turn, food and the end of the game.

Three functions are the engine's contract: legal_actions(state), apply_action(state, action), is_terminal(state). The
placement mechanic, the cards' effects and the effect stack live in effects.py.

A turn: on a player's Nth own turn they have min(N, mana_cap) mana. They play cards from hand, each for its cost, and
their leader's power for its price, until they end the turn (never ended for them). At its end every region they hold
pays its food. 30 food wins; a player whose food drops to 0 loses.
"""

from __future__ import annotations

from typing import Optional

from . import effects, statics
from .actions import Action, LeaderAction, PassAction, PlaceAction, action_from_dict
from .state import EngineError, GameState, Result, other_player


# --------------------------------------------------------------- legal actions

def legal_actions(state: GameState) -> list[Action]:
    """Every legal action for the player to act; ending the turn only when nothing else is. Empty once the game is over."""
    if state.result is not None:
        return []
    if state.pending is not None:
        return effects.legal_pending(state)
    return _plays(state, state.current) or [PassAction()]


def can_pass(state: GameState) -> bool:
    """Ending the turn is legal whenever nothing is resolving."""
    return state.result is None and state.pending is None and not state.effect_stack


def _plays(state: GameState, player: str) -> list[Action]:
    """Every play from hand the mana left pays for, and the leader's power while it pays for that."""
    left = mana_left(state, player)
    actions: list[Action] = [p for p in effects.legal_placements(state, player)
                             if effects.mana_cost(state, p.card_id) <= left]
    if left >= effects.power_cost(state, player) and effects.leader_usable(state, player):
        actions.append(LeaderAction())
    return actions


def own_turn_number(state: GameState, player: str) -> int:
    """Which of `player`'s own turns is the current one if it is theirs, else their next: 1 for their first."""
    return (state.turn_counter + (0 if player == state.current else 1)) // 2 + 1


def mana_total(state: GameState, player: str) -> int:
    """`player`'s mana this turn if it is theirs, else at the start of their next."""
    return min(own_turn_number(state, player), state.config.mana_cap)


def mana_left(state: GameState, player: str) -> int:
    """The mana `player` has left: this turn's unspent mana, or all of their next turn's while it isn't theirs."""
    total = mana_total(state, player)
    return total - state.mana_spent if player == state.current else total


# ------------------------------------------------------------- the mulligan, both at once

def early_mulligan(state: GameState, player: str) -> Optional[int]:
    """Where `player`'s mulligan waits under the one being chosen now, if it does: both players mulligan at once, though
    the stack resolves one step at a time. Its index on the effect stack, else None."""
    if not state.pending or state.pending.get("kind") != "mulligan" or state.pending.get("chooser") == player:
        return None
    return next((i for i, st in enumerate(state.effect_stack[:-1]) if st["op"] == "mulligan" and st["player"] == player), None)


def apply_early_mulligan(state: GameState, player: str, action: Action) -> None:
    """Apply `player`'s mulligan choice while the other player is still choosing theirs: their step comes to the top,
    takes the choice, and goes back under the other's if it isn't done."""
    i = early_mulligan(state, player)
    if i is None:
        raise EngineError("not your decision")
    stack, waiting = state.effect_stack, state.pending
    step = stack.pop(i)
    stack.append(step)
    state.pending = {"mode": "choice", "chooser": player, "optional": True, "kind": "mulligan",
                     "options": [u.iid for u in state.hands[player]]}
    try:
        apply_action(state, action)
    except Exception:
        stack.remove(step)
        stack.insert(i, step)
        state.pending = waiting
        raise
    if state.pending and state.pending.get("chooser") == player and stack and stack[-1] is step:   # more to choose: back under
        stack.pop()
        stack.insert(i, step)
        state.pending = waiting


def apply_logged(state: GameState, adict: dict) -> None:
    """Apply one action as a game log records it: one marked "by" a player is their mulligan choice made while the other
    was choosing theirs."""
    by, action = adict.get("by"), action_from_dict(adict)
    if by and early_mulligan(state, by) is not None:
        apply_early_mulligan(state, by, action)
    else:
        apply_action(state, action)


# ------------------------------------------------------------- apply

def apply_action(state: GameState, action: Action, *, validate: bool = True) -> GameState:
    """Apply one action (a play, the leader's power, ending the turn, or a pending choice), mutating `state`. Raises
    EngineError unless it is legal; a bot applying an action it just drew from legal_actions passes validate=False."""
    if state.result is not None:
        raise EngineError("cannot act: the game is over")
    if isinstance(action, PassAction):
        if not can_pass(state):
            raise EngineError("cannot end the turn mid-resolution")
        _end_turn(state)
        return state
    if validate and action not in legal_actions(state):
        raise EngineError(f"illegal action {action!r}")
    state.applied_this_turn += 1
    if state.pending is not None:
        effects.apply_pending(state, action)
    elif isinstance(action, PlaceAction):
        state.mana_spent += effects.mana_cost(state, action.card_id)
        effects.do_placement(state, state.current, action.card_id, action.target)
    elif isinstance(action, LeaderAction):
        state.mana_spent += effects.power_cost(state, state.current)
        effects.do_leader(state, state.current)
    else:
        raise EngineError(f"unexpected action {action!r}")
    effects.resolve(state)
    # The turn's caps: past either the turn ends at once, whatever is still resolving (a loop of effects).
    over_effects = state.effect_steps_this_turn > state.config.max_effect_steps_per_turn
    if (over_effects or state.applied_this_turn >= state.config.max_actions_per_turn) and state.result is None:
        if not over_effects:
            effects.record_cap(state, "actions", effects.stack_cards(state))
        state.pending = None
        state.effect_stack.clear()
        _end_turn(state)
    return state


def _end_turn(state: GameState) -> None:
    player = state.current
    state.emit("turn_end", player=player)
    _produce_food(state, player)
    if state.result is not None:
        return
    state.turn_counter += 1
    state.mana_spent = 0
    state.applied_this_turn = 0
    state.played_this_turn = 0
    state.power_used = False
    state.effect_steps_this_turn = 0
    state.current = other_player(player)
    state.emit("turn_start", player=state.current, turn=state.turn_counter)
    effects.draw_cards(state, state.current, state.config.turn_draw_count)   # the turn's free card
    effects.start_of_turn(state, state.current)
    effects.resolve(state)


# ------------------------------------------------------------- regions / food

def regions_controlled(state: GameState, player: str):
    return statics.regions_of(state, player)


def region_income(state: GameState, player: str) -> int:
    """The food `player`'s regions pay at the end of their turn."""
    return sum(r.food for r in regions_controlled(state, player))


def _produce_food(state: GameState, player: str) -> None:
    effects.gain_food(state, player, region_income(state, player), income=True)


# ------------------------------------------------------------------ the end

def is_terminal(state: GameState) -> Optional[Result]:
    """The game's Result if it is over, else None (the turn limit ends it on food)."""
    if state.result is not None:
        return state.result
    if state.turn_counter >= state.config.max_turns:
        a, b = state.food["A"], state.food["B"]
        return Result("A" if a > b else "B" if b > a else None, "max_turns")
    return None
