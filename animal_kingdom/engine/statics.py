"""Static rules read while placements are generated and effects resolve: covering, the keywords, regions."""

from __future__ import annotations


from .state import GameState, UnitInstance
from .strength import effective_strength


def has_keyword(state: GameState, unit: UnitInstance, kw: str) -> bool:
    return kw in state.cards[unit.card_id].keywords


def can_cover(state: GameState, placer: UnitInstance, target: UnitInstance) -> bool:
    """May `placer`, played from hand, cover the enemy `target`? Only when it is strictly stronger."""
    return effective_strength(state, placer) > effective_strength(state, target)


def can_be_removed(state: GameState, unit: UnitInstance) -> bool:
    """Armor: no ability removes it (a cover's removal is the rules', not an ability's)."""
    return not has_keyword(state, unit, "Armor")


def can_be_chosen(state: GameState, unit: UnitInstance, by_player: str) -> bool:
    """Stealth: an enemy's ability can't choose it."""
    return by_player == unit.owner or not has_keyword(state, unit, "Stealth")


def regions_of(state: GameState, player: str) -> list:
    """The regions whose every tile `player` holds."""
    return [r for r in state.game_map.regions.values() if all(state.owner_of(c) == player for c in r.corners)]
