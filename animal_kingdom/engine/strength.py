"""Effective strength - the single chokepoint used wherever strength matters.

M1 only handled integer base strength (and raised on dynamic). M2 adds the three
dynamic cards. Strength is evaluated **live at comparison time** (plan decision): a
dynamic unit's strength reflects the board/discard at the moment it is checked.
"""

from __future__ import annotations

from typing import Optional

from .state import EngineError, GameState, UnitInstance


def count_units_controlled(state: GameState, player: str) -> int:
    """Number of crossroads whose top (visible) unit belongs to `player`."""
    return sum(1 for stack in state.board.values() if stack and stack[-1].owner == player)


def _dynamic_strength(state: GameState, rule: Optional[str], owner: str) -> int:
    if rule == "control_count":          # Nile Crocodile
        return count_units_controlled(state, owner)
    if rule == "discard_count":          # Anaconda
        return len(state.discard)
    if rule == "chameleon":              # Chameleon: ±∞ bypass is handled in statics.can_cover
        return 0  # TODO(rules): placeholder for non-covering strength checks
    raise EngineError(f"unknown dynamic strength rule {rule!r}")


def card_strength(state: GameState, card_id: str, owner: str) -> int:
    """Strength of a card about to be placed (no instance yet), for `owner`."""
    card = state.cards[card_id]
    if isinstance(card.base_strength, int):
        return card.base_strength
    return _dynamic_strength(state, card.dynamic_strength, owner)


def effective_strength(state: GameState, unit: UnitInstance) -> int:
    """Strength of a unit in play."""
    card = state.cards[unit.card_id]
    if isinstance(card.base_strength, int):
        return card.base_strength
    return _dynamic_strength(state, card.dynamic_strength, unit.owner)
