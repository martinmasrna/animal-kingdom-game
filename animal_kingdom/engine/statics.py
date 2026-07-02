"""Static modifiers - evaluated *during* legal-action generation and resolution, NOT via
the event bus (handoff §7.1). These change legality/targeting, not game events.

Covered here: covering-rule overrides, connection bypass, removal immunity, and
untargetability. Each is keyed off card id / keyword and composes into a small set of
predicates the rules and effects call.
"""

from __future__ import annotations

from .state import GameState, UnitInstance
from .strength import effective_strength, placement_strength


def _controls(state: GameState, player: str, card_id: str) -> bool:
    """True if `player` controls (tops a stack with) a unit of `card_id`."""
    return any(
        stack and stack[-1].owner == player and stack[-1].card_id == card_id
        for stack in state.board.values()
    )


def can_cover(state: GameState, placer: UnitInstance, target: UnitInstance) -> bool:
    """May the hand instance `placer` be placed onto the enemy `target` unit?

    Only called for covering an ENEMY top unit (own-stacking needs no strength check).
    Base rule is strictly-greater strength; the modifiers below override it.
    """
    placer_card = state.cards[placer.card_id]
    target_card = state.cards[target.card_id]
    owner = placer.owner

    # Chameleon bypasses the comparison both ways (may cover anything; may be covered by anything).
    if placer_card.dynamic_strength == "chameleon" or target_card.dynamic_strength == "chameleon":
        return True

    # Porcupine cannot be covered by an enemy at all.
    if target_card.id == "porcupine":
        return False

    placer_str = placement_strength(state, placer)
    target_str = effective_strength(state, target)

    # Snow Leopard anthem: your *other* Cats may cover equal-or-lower while you control one.
    if "Cat" in placer_card.tags and placer_card.id != "snow_leopard" and _controls(state, owner, "snow_leopard"):
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
    """Immovable (keyword-review decision A2, 2026-07-02): *physics*. The unit cannot be
    removed, moved (bounced), or eaten by ANY ability - the enemy's or its own
    controller's (covering is placement, not an ability, and stays legal). Consulted by
    every effect-removal/bounce/eat path regardless of who chose it.

    Carriers: Giant Tortoise, Scrooge, Methuselah, Bulwark, Elephant.
    """
    return "Immovable" not in state.cards[unit.card_id].keywords


def can_be_chosen(state: GameState, unit: UnitInstance, by_player: str) -> bool:
    """Stealth (keyword-review decisions A2/B/E, 2026-07-02): the unit cannot be *chosen*
    by an enemy ability - consulted ONLY when building option lists an enemy chooser picks
    from (and the Apex eat, a chosen single-out). Mass, random, and automatic effects
    (Pestis/Rhinoceros/Bulwark/Sirocco, Grizzly Bear, Hippopotamus, King Theron,
    Pufferfish) do NOT consult this and hit Stealth units normally.

    Carrier: Black Panther.
    """
    card = state.cards[unit.card_id]
    if "Stealth" in card.keywords and by_player != unit.owner:
        return False
    return True
