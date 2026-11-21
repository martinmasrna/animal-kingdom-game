"""Strength: one number, wherever it matters (covering, a raid's food). A card's printed strength, or a
Shade's live count, plus what effects have added to it (the Hunters' -N); never below 0."""

from __future__ import annotations

from .state import EngineError, GameState, UnitInstance, other_player

# A Shade's count: "+1 strength for each card in your hand, ally, enemy, region you control". The Djinn's discounts count
# the same things (effects.mana_cost).
COUNTS = {"hand_count": "hand", "ally_count": "ally", "enemy_count": "enemy", "region_count": "region"}


def count(state: GameState, player: str, what: str) -> int:
    """`player`'s count of `what`: cards in their hand, their or their opponent's animals on the board (top units), or
    the regions they control."""
    if what == "hand":
        return len(state.hands[player])
    if what in ("ally", "enemy"):
        side = player if what == "ally" else other_player(player)
        return sum(1 for stack in state.board.values() if stack and stack[-1].owner == side)
    if what == "region":   # the regions whose every tile `player` holds (statics.regions_of, which imports this module)
        return sum(1 for r in state.game_map.regions.values() if all(state.owner_of(c) == player for c in r.corners))
    raise EngineError(f"unknown count {what!r}")


def card_strength(state: GameState, card_id: str, owner: str) -> int:
    """The strength a unit of `card_id` has for `owner` now: on the board, or as it would be played from hand."""
    card = state.cards[card_id]
    if isinstance(card.base_strength, int):
        return card.base_strength
    what = COUNTS.get(card.dynamic_strength or "")
    if what is None:
        raise EngineError(f"unknown dynamic strength rule {card.dynamic_strength!r}")
    return max(0, state.config.shade_growth * count(state, owner, what))


def effective_strength(state: GameState, unit: UnitInstance) -> int:
    return max(0, card_strength(state, unit.card_id, unit.owner) + unit.strength_mod)
