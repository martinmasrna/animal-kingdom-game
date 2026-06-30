"""Static modifiers - evaluated *during* legal-action generation and resolution, NOT via
the event bus (handoff §7.1). These change legality/targeting, not game events.

Covered here: covering-rule overrides, connection bypass, removal immunity, and
untargetability. Each is keyed off card id / keyword and composes into a small set of
predicates the rules and effects call.
"""

from __future__ import annotations

from .state import GameState, UnitInstance
from .strength import card_strength, count_units_controlled, effective_strength


def _controls(state: GameState, player: str, card_id: str) -> bool:
    """True if `player` controls (tops a stack with) a unit of `card_id`."""
    return any(
        stack and stack[-1].owner == player and stack[-1].card_id == card_id
        for stack in state.board.values()
    )


def can_cover(state: GameState, placer_card_id: str, owner: str, target: UnitInstance) -> bool:
    """May `owner` place `placer_card_id` onto the enemy `target` unit?

    Only called for covering an ENEMY top unit (own-stacking needs no strength check).
    Base rule is strictly-greater strength; the modifiers below override it.
    """
    placer = state.cards[placer_card_id]
    target_card = state.cards[target.card_id]

    # Chameleon bypasses the comparison both ways (±∞).
    if placer.dynamic_strength == "chameleon" or target_card.dynamic_strength == "chameleon":
        return True

    # Giant Tortoise cannot be covered by an enemy at all.
    if target_card.id == "giant_tortoise":
        return False

    placer_str = card_strength(state, placer_card_id, owner)
    target_str = effective_strength(state, target)

    # Honey Badger: equal-or-lower instead of strictly-lower.
    if placer.id == "honey_badger":
        return placer_str >= target_str

    # Spotted Hyena: any strength if you control >= threshold other units.
    if placer.id == "spotted_hyena" and count_units_controlled(state, owner) >= state.config.spotted_hyena_threshold:
        return True

    # Snow Leopard anthem: your *other* Cats may cover equal-or-lower while you control one.
    if "Cat" in placer.tags and placer.id != "snow_leopard" and _controls(state, owner, "snow_leopard"):
        if placer_str >= target_str:
            return True

    return placer_str > target_str  # default: strictly greater


def ignores_connection(state: GameState, card_id: str) -> bool:
    """Flight: the unit may be placed without a connection to its HQ."""
    return "Flight" in state.cards[card_id].keywords


def extra_placement_crossroads(state: GameState, card_id: str, owner: str) -> set[str]:
    """Crossroads a card may target ignoring connection, beyond the normal rules.

    Cougar: may be placed adjacent to any Cat you control, ignoring connection.
    """
    if card_id != "cougar":
        return set()
    gm = state.game_map
    out: set[str] = set()
    for cr, stack in state.board.items():
        top = stack[-1] if stack else None
        if top and top.owner == owner and "Cat" in state.cards[top.card_id].tags:
            out |= set(gm.neighbors(cr))
    return out


def can_be_removed(state: GameState, unit: UnitInstance) -> bool:
    """Whether a unit may be removed by a special effect (covering is separate)."""
    card = state.cards[unit.card_id]
    if "Immovable" in card.keywords:                 # Matriarch Elephant, Hibernating Bear
        return False
    if card.id == "armadillo":                       # safe until the owner's next turn
        if state.turn_counter < unit.placed_on_turn + 2:
            return False
    return True


def can_be_targeted(state: GameState, unit: UnitInstance, by_player: str) -> bool:
    """Black Panther cannot be targeted by enemy special effects."""
    card = state.cards[unit.card_id]
    if card.id == "black_panther" and by_player != unit.owner:
        return False
    return True
