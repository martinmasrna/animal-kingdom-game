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
- active_anthems: live "has +X" auras (Mackerel, Moose, Guard Wasp).
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
    return iid is not None and iid in state.inked


# Auras on the board that give your other animals of a family strength: card id -> (family, config attr of the
# bonus, whether only during your opponent's turn). Each source counts, and none counts for itself.
FAMILY_AURAS = {
    "mackerel": ("Fish", "mackerel_anthem", False),   # "Your other Fish have +1 strength."
    "cape_buffalo": ("Hoofed", "buffalo_anthem", True),   # "Your other Hoofed animals have +1 strength during your opponent's turn."
}
AURA_FAMILIES = frozenset(fam for fam, _, _ in FAMILY_AURAS.values())
# The cards whose own text is a live "+X" (the branches of anthem_bonus). Any other card, of a family no aura reaches,
# has no anthem at all: anthem_bonus answers 0 for it before walking the board. The search asks for every unit's strength
# in every position it imagines, so that walk, once per unit, was the hottest line of the engine (2026-10-20).
ANTHEM_CARDS = frozenset({"guard_wasp", "tuna", "hamster", "peacock", "giraffe", "crocodile", "capybara"})


_SMALL_DECKS: dict = {}


def small_starting_deck(state: GameState, owner: str, but: str) -> bool:
    """No animal of strength `capybara_small_max` + 1 or more in `owner`'s starting deck apart from `but` (printed
    strength; a dynamic one counts as its printed 0). The starting deck never changes, so the answer is kept."""
    deck = state.starting_decks.get(owner, ())
    key = (deck, but)
    if key not in _SMALL_DECKS:
        cap = state.config.capybara_small_max
        _SMALL_DECKS[key] = all(cid == but or not isinstance(s := state.cards[cid].base_strength, int) or s <= cap
                                for cid in deck)
    return _SMALL_DECKS[key]


def aura_sources(state: GameState) -> list:
    """The board's family-aura sources as (unit, aura) pairs: what anthem_bonus looks for. An evaluation of a whole board
    gathers them once and hands them to effective_strength for every unit, instead of walking the board per unit."""
    return [(u, aura) for stack in state.board.values() if stack and (aura := FAMILY_AURAS.get((u := stack[-1]).card_id)) is not None]


def anthem_bonus(state: GameState, card, owner: str, self_iid: Optional[int], sources: Optional[list] = None) -> int:
    """The live "has +X" anthem bonus for a unit of `card` controlled by `owner`. `sources`: aura_sources(state), if the
    caller has them.

    `self_iid` is the unit's iid if it is on the board, or None for a prospective placement
    (a card still in hand). "Other X" auras exclude the unit itself; "you control N X" counts
    include it once it is on the board, but a card in hand is not yet controlled, so it covers
    with the count the board gives it now.
    An inked unit has no anthem of its own, and an inked source gives none.
    """
    cfg = state.config
    their_turn = state.current != owner
    if card.id not in ANTHEM_CARDS:
        if card.tags.isdisjoint(AURA_FAMILIES):
            return 0
        bonus = 0                           # only an aura can reach it: look for sources, never gather the board
        for u, aura in (aura_sources(state) if sources is None else sources):
            if u.owner != owner or u.iid == self_iid or aura[0] not in card.tags or _inked(state, u.iid) or (aura[2] and not their_turn):
                continue
            bonus += getattr(cfg, aura[1])
        return bonus
    tops = _tops_owned(state, owner)

    def count(tag: str, *, include_self: bool) -> int:
        if include_self:
            return sum(1 for u in tops if tag in state.cards[u.card_id].tags)
        return sum(1 for u in tops if tag in state.cards[u.card_id].tags and u.iid != self_iid)

    cid = card.id
    bonus = 0
    if not _inked(state, self_iid):
        if cid == "guard_wasp":             # +5 while you control >= threshold Colony units (itself once on the board)
            if count("Colony", include_self=True) >= cfg.guard_hornet_colony_threshold:
                bonus += cfg.guard_hornet_bonus
        elif cid == "tuna":                     # +1 for each other Fish you control
            bonus += cfg.tuna_per_fish * count("Fish", include_self=False)
        elif cid == "hamster":                  # +1 for each 10 food you have
            bonus += cfg.hamster_per_step * (state.food[owner] // cfg.hamster_food_step)
        elif cid == "peacock":                  # +1 for each card in your hand: itself while there, one less once it lands
            bonus += cfg.hand_per_card * len(state.hands[owner])
        elif cid == "giraffe":                  # +5 during your opponent's turn
            bonus += cfg.giraffe_bonus if their_turn else 0
        elif cid == "crocodile":                # -3 during your opponent's turn
            bonus -= cfg.crocodile_penalty if their_turn else 0
        elif cid == "capybara":                 # +7 if your starting deck holds no other animal of 4 or more
            if state.starting_decks.get(owner) and small_starting_deck(state, owner, cid):
                bonus += cfg.capybara_bonus

    for u in tops:
        aura = FAMILY_AURAS.get(u.card_id)
        if aura is None or u.iid == self_iid or aura[0] not in card.tags or _inked(state, u.iid):
            continue
        if aura[2] and not their_turn:
            continue
        bonus += getattr(cfg, aura[1])
    return bonus


def effective_strength(state: GameState, unit: UnitInstance, sources: Optional[list] = None) -> int:
    """Strength of a unit in play: base/dynamic + its stored counter + live anthems, >= 0. `sources`: aura_sources(state),
    when the caller scores the whole board."""
    card = state.cards[unit.card_id]
    if _inked(state, unit.iid):             # its own effects are off: a dynamic strength is its printed 0
        base = card.base_strength if isinstance(card.base_strength, int) else 0
        return max(0, base + _global_growth(state, card.id, unit.owner) + unit.strength_counter
                   + anthem_bonus(state, card, unit.owner, unit.iid, sources))
    val = (_base_or_dynamic(state, card, unit.owner)
           + _global_growth(state, card.id, unit.owner)
           + unit.strength_counter
           + anthem_bonus(state, card, unit.owner, unit.iid, sources))
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
