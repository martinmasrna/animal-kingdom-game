"""Effective strength - the single chokepoint used wherever strength matters.

Decision E (keywords.md): one number, three layers, evaluated **live** wherever strength
matters (covering, removal thresholds, region holding, conditions like Coyote's "if 5+"):

    effective_strength = base_or_dynamic + global_growth + stored_counters
                         + active_anthems                                      (clamped >= 0)

- base_or_dynamic: the printed int, or a dynamic rule (Goliath = #removed units; Chameleon).
- global_growth: persistent per-player/card growth that applies in every zone (Rattlesnake).
- stored_counters: `UnitInstance.strength_counter` - one-time "give +X" grants (Unnamed Rallier,
  Clarion, Dhole, Dingo, Bush Dog, Shuck). Stored on the instance; persist after the
  granter dies; travel hand->board.
- active_anthems: live "has +X" auras (Raksha, Lobo, Verminus, Vesper, Guard Wasp).
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
    if rule == "removed_units_count":    # Python: +1 for each removed unit
        return len(state.remove_pile)
    if rule == "removed_eggs_count":     # Egg Eater: +N for each removed Egg
        return state.config.egg_eater_growth * sum(
            "Egg" in state.cards[cid].tags for cid in state.remove_pile)
    raise EngineError(f"unknown dynamic strength rule {rule!r}")


def _base_or_dynamic(state: GameState, card, owner: str) -> int:
    if isinstance(card.base_strength, int):
        return card.base_strength
    return _dynamic_strength(state, card.dynamic_strength, owner)


def _global_growth(state: GameState, card_id: str, owner: str) -> int:
    return state.card_strength_counters.get(owner, {}).get(card_id, 0)


def _inked(state: GameState, iid: Optional[int]) -> bool:
    """Octopus ink (statics.inked, inlined here: statics imports this module): the unit's effects are off."""
    until = state.inked.get(iid) if iid is not None and state.inked else None
    return until is not None and state.turn_counter < until


# Auras on the board that give your other animals of a family strength: card id -> (family, config attr of the
# bonus, whether only during your opponent's turn). Each source counts, and none counts for itself.
FAMILY_AURAS = {
    "raksha": ("Canine", "raksha_anthem", False),     # "Your other Canines have +1 strength."
    "mackerel": ("Fish", "mackerel_anthem", False),   # "Your other Fish have +1 strength."
    "moose": ("Hoofed", "moose_anthem", True),        # "Your other Hoofed animals have +1 strength during your opponent's turn."
}


def anthem_bonus(state: GameState, card, owner: str, self_iid: Optional[int]) -> int:
    """The live "has +X" anthem bonus for a unit of `card` controlled by `owner`.

    `self_iid` is the unit's iid if it is on the board, or None for a prospective placement
    (a card still in hand). "Other X" auras exclude the unit itself; "each friendly X" auras
    include it (and add 1 for a prospective placement, since it is not on the board yet).
    An inked unit has no anthem of its own, and an inked source gives none.
    """
    tops = _tops_owned(state, owner)
    prospective = self_iid is None
    cfg = state.config
    their_turn = state.current != owner

    def count(tag: str, *, include_self: bool) -> int:
        if include_self:
            n = sum(1 for u in tops if tag in state.cards[u.card_id].tags)
            return n + 1 if prospective else n
        return sum(1 for u in tops if tag in state.cards[u.card_id].tags and u.iid != self_iid)

    cid = card.id
    bonus = 0
    if not _inked(state, self_iid):
        if cid == "verminus":                   # +1 for each OTHER unit you control (any tag)
            bonus += cfg.anthem_verminus_per * sum(1 for u in tops if u.iid != self_iid)
        elif cid == "vesper":                   # +2 for each OTHER friendly Colony unit
            bonus += cfg.anthem_vesper_per * count("Colony", include_self=False)
        elif cid == "guard_hornet":             # +5 while you control >= threshold Colony units (incl. itself)
            if count("Colony", include_self=True) >= cfg.guard_hornet_colony_threshold:
                bonus += cfg.guard_hornet_bonus
        elif cid == "tuna":                     # +1 for each other Fish you control
            bonus += cfg.tuna_per_fish * count("Fish", include_self=False)
        elif cid == "grizzly_bear":             # +1 for each card in your hand (it has left it when placed)
            bonus += cfg.grizzly_per_card * max(0, len(state.hands[owner]) - (1 if prospective else 0))
        elif cid == "giraffe":                  # +5 during your opponent's turn
            bonus += cfg.giraffe_bonus if their_turn else 0
        elif cid == "boar" and not prospective:  # +3 while grazing
            from .statics import grazing
            unit = next((u for u in tops if u.iid == self_iid), None)
            if unit is not None and grazing(state, unit):
                bonus += cfg.boar_grazing_bonus

    for u in tops:
        aura = FAMILY_AURAS.get(u.card_id)
        if aura is None or u.iid == self_iid or aura[0] not in card.tags or _inked(state, u.iid):
            continue
        if aura[2] and not their_turn:
            continue
        bonus += getattr(cfg, aura[1])
    return bonus


def effective_strength(state: GameState, unit: UnitInstance) -> int:
    """Strength of a unit in play: base/dynamic + its stored counter + live anthems, >= 0."""
    card = state.cards[unit.card_id]
    if _inked(state, unit.iid):             # its own effects are off: a dynamic strength is its printed 0
        base = card.base_strength if isinstance(card.base_strength, int) else 0
        return max(0, base + _global_growth(state, card.id, unit.owner) + unit.strength_counter
                   + anthem_bonus(state, card, unit.owner, unit.iid))
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
