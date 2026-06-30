"""The effect engine: placement mechanic, event dispatch, and the effect-stack interpreter.

Design (plan decision 6): effect resolution is **declarative op-step data** on
`state.effect_stack`, drained by `resolve()`. A step that needs a choice surfaces as
`state.pending`; the choice arrives as a normal Action and resumes the paused op. Steps
are plain dicts (serializable / cloneable / replayable) - never closures.

Layering: this module sits below rules.py (rules orchestrates; effects holds the core
mechanic + card behavior). It imports state/statics/strength only - never rules.

Card behavior lives in two registries:
  - EFFECTS[card_id] -> {hook_name: fn}   (triggered effects; push op-steps)
  - OPS[op_name] -> fn(state, step)        (the op interpreter; returns PendingRequest|None)

M2a implements a representative slice; remaining cards are added in M2b.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .actions import SKIP, ChoiceAction, PlaceAction
from .state import GameState, Result, UnitInstance, other_player
from . import statics
from .strength import effective_strength


# ============================================================== pending / requests

@dataclass
class PendingRequest:
    """What an op returns when it needs a choice; converted into state.pending."""
    mode: str                       # "choice" or "place"
    chooser: str
    optional: bool = False
    options: Optional[list] = None        # mode == "choice": serializable option values
    placements: Optional[list] = None     # mode == "place": [{card_id, target}]

    def to_pending(self) -> dict:
        p = {"mode": self.mode, "chooser": self.chooser, "optional": self.optional}
        if self.mode == "choice":
            p["options"] = list(self.options)
        else:
            p["placements"] = list(self.placements)
        return p


def legal_pending(state: GameState) -> list:
    """Actions offered while a choice is pending."""
    p = state.pending
    if p["mode"] == "choice":
        acts = [ChoiceAction(o) for o in p["options"]]
    else:  # "place"
        acts = [PlaceAction(pl["card_id"], tuple(pl["target"])) for pl in p["placements"]]
    if p.get("optional"):
        acts.append(ChoiceAction(SKIP))
    return acts


def apply_pending(state: GameState, action) -> None:
    """Record the chosen option onto the paused step, then continue resolving."""
    p = state.pending
    step = state.effect_stack[-1]  # the paused op (left on the stack by resolve)
    if p["mode"] == "choice":
        step["choice"] = action.choice
    else:  # "place"
        if isinstance(action, ChoiceAction) and action.choice == SKIP:
            step["place_action"] = SKIP
        else:
            step["place_action"] = {"card_id": action.card_id, "target": list(action.target)}
    state.pending = None
    # Resolution is driven by the caller (rules._resolve_and_maybe_end_turn).


# ===================================================================== resolve loop

def resolve(state: GameState) -> None:
    """Drain the effect stack until empty, a choice is needed, or the game is won."""
    while state.pending is None and state.result is None and state.effect_stack:
        step = state.effect_stack.pop()
        req = OPS[step["op"]](state, step)
        if req is not None:           # op needs a choice: put the step back and pause
            state.effect_stack.append(step)
            state.pending = req.to_pending()
            return


# ============================================================ placement + events

def do_placement(state: GameState, player: str, card_id: str, target) -> None:
    """Place a unit from hand. Handles HQ capture and crossroad landing + triggers."""
    state.hands[player].remove(card_id)
    state.units_placed_this_turn += 1
    kind, where = target
    if kind == "hq":
        state.result = Result(player, "hq_capture")
        return
    _land_unit(state, player, card_id, where)


def _land_unit(state: GameState, player: str, card_id: str, cr: str) -> None:
    covered = state.top_unit(cr)
    onto_enemy = covered is not None and covered.owner != player

    # Boa Constrictor: when placed onto an enemy, remove it instead of stacking (not a cover).
    if card_id == "boa_constrictor" and onto_enemy:
        _remove_specific(state, cr, covered, by_player=player)
        covered, onto_enemy = None, False

    unit = UnitInstance(card_id, player, state.new_iid(), placed_on_turn=state.turn_counter)
    state.board.setdefault(cr, []).append(unit)

    # Reactive triggers resolve AFTER the placed unit's battlecry (decision 8). The stack
    # is LIFO, so push reactive first (lower) and the battlecry last (on top).
    _push_reactions(state, unit, cr, covered, onto_enemy)
    _push_hook(state, unit, cr, "on_place")
    if onto_enemy:
        _push_hook(state, unit, cr, "on_place_onto_enemy")


def _push_reactions(state, unit, cr, covered, onto_enemy) -> None:
    # Enemy hippos etc. reacting to a unit placed adjacent.
    for nb in state.game_map.neighbors(cr):
        top = state.top_unit(nb)
        if top and top.owner != unit.owner:
            hook = _hook(state, top.card_id, "on_enemy_placed_adjacent")
            if hook:
                hook(state, top, unit, cr)
    if covered is not None:
        hook = _hook(state, covered.card_id, "on_covered")
        if hook:
            hook(state, covered, unit, cr)
        if "Fragile" in state.cards[covered.card_id].keywords:
            state.effect_stack.append(
                {"op": "remove_iid", "iid": covered.iid, "by_player": unit.owner, "by_effect": False}
            )


def _push_hook(state, unit, cr, hook_name) -> None:
    hook = _hook(state, unit.card_id, hook_name)
    if hook:
        hook(state, unit, cr)


def _hook(state, card_id, hook_name) -> Optional[Callable]:
    return EFFECTS.get(card_id, {}).get(hook_name)


# ================================================================= removal & food

def _dispose(state: GameState, unit: UnitInstance) -> None:
    if unit.card_id == "opossum":                       # returns to hand instead of discard
        state.hands[unit.owner].append(unit.card_id)
    else:
        state.discard.append(unit.card_id)


def _remove_specific(state, cr, unit, *, by_player, by_effect=True) -> bool:
    """Remove a specific unit from a stack (mid-stack ok). Fires removal reactions."""
    stack = state.board.get(cr)
    if not stack or unit not in stack:
        return False
    if by_effect and not statics.can_be_removed(state, unit):
        return False
    if by_effect and not statics.can_be_targeted(state, unit, by_player):
        return False
    stack.remove(unit)
    if not stack:
        del state.board[cr]
    _dispose(state, unit)
    _fire_on_remove(state, unit)
    _fire_on_enemy_removed(state, unit)
    return True


def remove_top(state, cr, *, by_player, by_effect=True) -> bool:
    top = state.top_unit(cr)
    if top is None:
        return False
    return _remove_specific(state, cr, top, by_player=by_player, by_effect=by_effect)


def _find_unit(state, iid):
    for cr, stack in state.board.items():
        for u in stack:
            if u.iid == iid:
                return cr, u
    return None, None


def _fire_on_remove(state, unit) -> None:
    hook = _hook(state, unit.card_id, "on_remove")
    if hook:
        hook(state, unit)


def _fire_on_enemy_removed(state, removed) -> None:
    # Vulture: whenever an enemy unit is removed, its controller draws 1 (once per turn).
    for stack in sorted(state.board.values(), key=lambda s: s[-1].iid if s else -1):
        top = stack[-1] if stack else None
        if top and top.card_id == "vulture" and removed.owner != top.owner:
            flag = f"vulture_drew_{top.owner}"
            if not state.turn_flags.get(flag):
                state.turn_flags[flag] = True
                state.draw(top.owner, 1)


def gain_food(state: GameState, player: str, amount: int) -> None:
    if amount <= 0:
        return
    # Queen Bee rider: +bonus per Queen Bee you control, additive, non-recursive.
    queens = sum(
        1 for stack in state.board.values()
        if stack and stack[-1].owner == player and stack[-1].card_id == "queen_bee"
    )
    state.food[player] += amount + queens * state.config.queen_bee_bonus
    if state.food[player] >= state.game_map.win_food:
        state.result = Result(player, "food")


# ========================================================== legal placement helper

def legal_placements(state: GameState, player: str, allowed_cards: Optional[set] = None) -> list:
    """All legal placements for `player` (used by rules.legal_actions and play_extra).

    `allowed_cards` (a set of card ids) restricts which hand cards may be played.
    Deterministic order (sorted) for reproducible replay.
    """
    gm = state.game_map
    occ = state.connected_occupied(player)
    enemy = other_player(player)
    enemy_hq = any(cr in occ for cr in gm.hq_front(enemy))  # HQ capture: connection only (not Flight)

    out = []
    cards = sorted(set(state.hands[player]))
    if allowed_cards is not None:
        cards = [c for c in cards if c in allowed_cards]
    for card_id in cards:
        flight = statics.ignores_connection(state, card_id)
        extra = statics.extra_placement_crossroads(state, card_id, player)
        for cr in sorted(gm.crossroads):
            if not (flight or cr in extra or state.is_connected(player, cr, occ)):
                continue
            top = state.top_unit(cr)
            if top is None or top.owner == player:
                out.append(PlaceAction(card_id, ("cr", cr)))
            elif statics.can_cover(state, card_id, player, top):
                out.append(PlaceAction(card_id, ("cr", cr)))
        if enemy_hq:
            out.append(PlaceAction(card_id, ("hq", enemy)))
    return out


# ============================================================= delayed scheduler

def schedule(state: GameState, owner: str, owner_turn_delay: int, step: dict) -> None:
    """Queue `step` to fire at the start of `owner`'s turn `owner_turn_delay` turns later."""
    due = state.turn_counter + 2 * owner_turn_delay  # a player's turns are 2 apart
    state.scheduled.append({"due": due, "owner": owner, "step": step})


def start_of_turn(state: GameState, player: str) -> None:
    """Fire due scheduled effects and on_start_of_turn hooks for `player` (then caller resolves)."""
    due = [s for s in state.scheduled if s["owner"] == player and s["due"] <= state.turn_counter]
    state.scheduled = [s for s in state.scheduled if s not in due]
    for s in sorted(due, key=lambda x: x["due"], reverse=True):  # earliest ends on top of stack
        state.effect_stack.append(s["step"])
    for cr, stack in sorted(state.board.items()):
        top = stack[-1]
        if top.owner == player:
            hook = _hook(state, top.card_id, "on_start_of_turn")
            if hook:
                hook(state, top, cr)


# ===================================================================== op registry

def _op_gain_food(state, step):
    gain_food(state, step["player"], step["amount"])
    return None


def _op_draw(state, step):
    state.draw(step["player"], step["n"])
    return None


def _op_remove_choice(state, step):
    """Remove the top unit at a chosen crossroad among `options`."""
    options = step["options"]
    if not options:
        return None
    if "choice" not in step:
        if len(options) == 1:
            step["choice"] = options[0]
        else:
            return PendingRequest("choice", step["chooser"], optional=step.get("optional", False),
                                  options=options)
    chosen = step["choice"]
    if chosen == SKIP:
        return None
    remove_top(state, chosen, by_player=step["by_player"])
    return None


def _op_remove_iid(state, step):
    cr, unit = _find_unit(state, step["iid"])
    if unit is not None:
        _remove_specific(state, cr, unit, by_player=step.get("by_player", unit.owner),
                         by_effect=step.get("by_effect", True))
    return None


def _op_play_extra(state, step):
    """Play one more unit from hand (optionally filtered), as part of resolution."""
    if step.get("played"):
        return None
    if "place_action" in step:
        pa = step["place_action"]
        if pa != SKIP:
            do_placement(state, step["chooser"], pa["card_id"], tuple(pa["target"]))
        step["played"] = True
        return None
    allowed = None
    if step.get("constraint") == "cat":
        allowed = {cid for cid in state.hands[step["chooser"]] if "Cat" in state.cards[cid].tags}
    placements = legal_placements(state, step["chooser"], allowed)
    if not placements:
        return None
    return PendingRequest("place", step["chooser"], optional=step.get("optional", False),
                          placements=[{"card_id": p.card_id, "target": list(p.target)} for p in placements])


def _op_bear_hibernate(state, step):
    owner = step["owner"]
    lost = state.food[owner]
    state.food[owner] = 0
    payout = lost * state.config.hibernating_bear_multiplier
    schedule(state, owner, state.config.hibernating_bear_delay,
             {"op": "gain_food", "player": owner, "amount": payout})
    return None


def _op_egg_hatch(state, step):
    cr, egg = _find_unit(state, step["iid"])
    if egg is None:
        return None  # egg already gone (e.g. covered while Fragile) - no payoff
    _remove_specific(state, cr, egg, by_player=egg.owner, by_effect=False)
    state.draw(egg.owner, step["draw"])
    return None


OPS: dict[str, Callable] = {
    "gain_food": _op_gain_food,
    "draw": _op_draw,
    "remove_choice": _op_remove_choice,
    "remove_iid": _op_remove_iid,
    "play_extra": _op_play_extra,
    "bear_hibernate": _op_bear_hibernate,
    "egg_hatch": _op_egg_hatch,
}


# ================================================== card behavior (M2a slice)

def _adjacent_enemy_targets(state, unit, cr, max_strength):
    """Crossroads adjacent to `cr` whose enemy top unit is removable and <= max_strength."""
    out = []
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if (top and top.owner != unit.owner
                and effective_strength(state, top) <= max_strength
                and statics.can_be_targeted(state, top, unit.owner)
                and statics.can_be_removed(state, top)):
            out.append(nb)
    return out


def _squirrel_place(state, unit, cr):
    state.effect_stack.append({"op": "gain_food", "player": unit.owner, "amount": state.config.f_high})


def _chipmunk_place(state, unit, cr):
    state.effect_stack.append({"op": "gain_food", "player": unit.owner, "amount": state.config.f_med})


def _gray_wolf_place(state, unit, cr):
    targets = _adjacent_enemy_targets(state, unit, cr, 3)
    if targets:
        state.effect_stack.append(
            {"op": "remove_choice", "chooser": unit.owner, "by_player": unit.owner, "options": targets}
        )


def _wild_dogs_place(state, unit, cr):
    state.effect_stack.append({"op": "play_extra", "chooser": unit.owner, "constraint": "any"})


def _pufferfish_covered(state, covered, coverer, cr):
    if coverer.owner == covered.owner:
        return  # only triggers vs an enemy coverer
    # Remove the coverer, then the pufferfish (both pushed; coverer resolves first).
    state.effect_stack.append(
        {"op": "remove_iid", "iid": covered.iid, "by_player": covered.owner, "by_effect": False})
    state.effect_stack.append(
        {"op": "remove_iid", "iid": coverer.iid, "by_player": covered.owner, "by_effect": True})


def _egg_place(state, unit, cr):
    schedule(state, unit.owner, state.config.egg_delay,
             {"op": "egg_hatch", "iid": unit.iid, "draw": state.config.egg_draw})


def _bear_place(state, unit, cr):
    state.effect_stack.append({"op": "bear_hibernate", "owner": unit.owner})


EFFECTS: dict[str, dict[str, Callable]] = {
    "squirrel": {"on_place": _squirrel_place},
    "chipmunk": {"on_place": _chipmunk_place},
    "gray_wolf": {"on_place": _gray_wolf_place},
    "wild_dogs": {"on_place": _wild_dogs_place},
    "pufferfish": {"on_covered": _pufferfish_covered},
    "egg": {"on_place": _egg_place},
    "hibernating_bear": {"on_place": _bear_place},
    # Golden Eagle (Flight), Honey Badger (cover-rule), Nile Crocodile (dynamic) are statics.
    # Vulture's on_enemy_removed is fired globally in _fire_on_enemy_removed.
}
