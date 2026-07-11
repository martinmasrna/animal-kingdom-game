"""Effective strength - the single chokepoint used wherever strength matters.

Decision E (keywords.md): one number, three layers, evaluated **live** wherever strength
matters (covering, removal thresholds, region holding, conditions like Coyote's "if 5+"):

    effective_strength = base_or_dynamic + global_growth + stored_counters
                         + active_anthems                                      (clamped >= 0)

- base_or_dynamic: the printed int, or a dynamic rule (Goliath = #removed units; Chameleon).
- global_growth: persistent per-player/card growth that applies in every zone (Rattlesnake).
- stored_counters: `UnitInstance.strength_counter` - one-time "give +X" grants (Dhole,
  Clarion, Red Wolf, Dingo, Bush Dog, Shuck). Stored on the instance; persist after the
  granter dies; travel hand->board.
- active_anthems: live "has +X" auras (Raksha, Lobo, Verminus, Vesper, Guard Hornet).
  Recomputed from the board every time; vanish when their condition lapses.

For covering legality a card is still in hand (no board iid yet), so anthems are computed
"as a prospective placement" (`card_strength`); the instance's counter is added on top.
"""

from __future__ import annotations

from typing import Optional

from .state import EngineError, GameState, UnitInstance


def count_units_controlled(state: GameState, player: str) -> int:
    """Number of crossroads whose top (visible) unit belongs to `player`."""
    return sum(1 for stack in state.board.values() if stack and stack[-1].owner == player)


def _tops_owned(state: GameState, owner: str) -> list[UnitInstance]:
    """The top (controlling) units `owner` holds across the board."""
    return [stack[-1] for stack in state.board.values() if stack and stack[-1].owner == owner]


def _dynamic_strength(state: GameState, rule: Optional[str], owner: str) -> int:
    if rule == "removed_units_count":    # Goliath: equal to the number of removed units
        return len(state.remove_pile)
    if rule == "chameleon":              # Chameleon: covering bypass handled in statics.can_cover
        return 0
    raise EngineError(f"unknown dynamic strength rule {rule!r}")


def _base_or_dynamic(state: GameState, card, owner: str) -> int:
    if isinstance(card.base_strength, int):
        return card.base_strength
    return _dynamic_strength(state, card.dynamic_strength, owner)


def _global_growth(state: GameState, card_id: str, owner: str) -> int:
    return state.card_strength_counters.get(owner, {}).get(card_id, 0)


def anthem_bonus(state: GameState, card, owner: str, self_iid: Optional[int]) -> int:
    """The live "has +X" anthem bonus for a unit of `card` controlled by `owner`.

    `self_iid` is the unit's iid if it is on the board, or None for a prospective placement
    (a card still in hand). "Other X" auras exclude the unit itself; "each friendly X" auras
    include it (and add 1 for a prospective placement, since it is not on the board yet).
    """
    tops = _tops_owned(state, owner)
    prospective = self_iid is None
    cfg = state.config

    def count(tag: str, *, include_self: bool) -> int:
        if include_self:
            n = sum(1 for u in tops if tag in state.cards[u.card_id].tags)
            return n + 1 if prospective else n
        return sum(1 for u in tops if tag in state.cards[u.card_id].tags and u.iid != self_iid)

    cid = card.id
    bonus = 0
    if cid == "lobo":                       # +2 for each OTHER Canine you control
        bonus += cfg.anthem_lobo_per * count("Canine", include_self=False)
    elif cid == "verminus":                 # +1 for each OTHER unit you control (any tag; not Landmarks)
        others = sum(1 for u in tops if u.iid != self_iid and state.cards[u.card_id].is_unit)
        bonus += cfg.anthem_verminus_per * others
    elif cid == "vesper":                   # +2 for each OTHER friendly Colony unit
        bonus += cfg.anthem_vesper_per * count("Colony", include_self=False)
    elif cid == "guard_hornet":             # +5 while you control >= threshold Colony units (incl. itself)
        if count("Colony", include_self=True) >= cfg.guard_hornet_colony_threshold:
            bonus += cfg.guard_hornet_bonus

    # Raksha aura: your *other* Canines have +2 while you control a Raksha.
    if "Canine" in card.tags and cid != "raksha" and any(u.card_id == "raksha" for u in tops):
        bonus += cfg.raksha_anthem
    return bonus


def effective_strength(state: GameState, unit: UnitInstance) -> int:
    """Strength of a unit in play: base/dynamic + its stored counter + live anthems, >= 0."""
    card = state.cards[unit.card_id]
    val = (_base_or_dynamic(state, card, unit.owner)
           + _global_growth(state, card.id, unit.owner)
           + unit.strength_counter
           + anthem_bonus(state, card, unit.owner, unit.iid))
    return max(0, val)


def card_strength(state: GameState, card_id: str, owner: str) -> int:
    """Strength of a unit of `card_id` for `owner`, anthems as a prospective placement and
    ignoring any per-instance counter (callers that have an instance add its counter)."""
    card = state.cards[card_id]
    val = (_base_or_dynamic(state, card, owner)
           + _global_growth(state, card.id, owner)
           + anthem_bonus(state, card, owner, None))
    return max(0, val)


def placement_strength(state: GameState, inst: UnitInstance) -> int:
    """Effective strength of a hand instance if it were placed now (for covering legality)."""
    return max(0, card_strength(state, inst.card_id, inst.owner) + inst.strength_counter)
