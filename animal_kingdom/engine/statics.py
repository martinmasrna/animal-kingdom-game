"""Static modifiers - evaluated *during* legal-action generation and resolution, NOT via
the event bus (handoff §7.1). These change legality/targeting, not game events.

Covered here: covering-rule overrides, connection bypass, removal immunity, and
untargetability. Each is keyed off card id / keyword and composes into a small set of
predicates the rules and effects call.
"""

from __future__ import annotations

from collections import deque

from .state import GameState, UnitInstance
from .strength import effective_strength, placement_strength


def _controls(state: GameState, player: str, card_id: str) -> bool:
    """True if `player` controls (tops a stack with) a unit of `card_id`."""
    return any(
        stack and stack[-1].owner == player and stack[-1].card_id == card_id
        for stack in state.board.values()
    )


def can_cover(state: GameState, placer: UnitInstance, target: UnitInstance, *, roaming: bool = False) -> bool:
    """May `placer` cover the enemy `target` unit? `placer` is a hand instance being placed, or (`roaming`) a board
    unit moving onto it, whose strength is its live one on the board.

    Only called for covering an ENEMY top unit (own-stacking needs no strength check).
    Base rule is strictly-greater strength; the modifiers below override it.
    """
    placer_card = state.cards[placer.card_id]
    owner = placer.owner

    # Chameleon covers units of any strength (its own side needs no strength anyway).
    if placer_card.id == "chameleon":
        return True

    placer_str = effective_strength(state, placer) if roaming else placement_strength(state, placer)
    target_str = effective_strength(state, target)

    if roaming and roam_covers_equal(state, placer) and placer_str >= target_str:
        return True

    # Snow Leopard anthem: your Cats may cover equal-or-lower while you control one.
    # Never the granting Snow Leopard itself (it is placed from hand); a second one benefits from the first.
    anthem = any(stack and stack[-1].owner == owner and stack[-1].card_id == "snow_leopard" and stack[-1] is not placer
                 for stack in state.board.values())
    if "Cat" in placer_card.tags and anthem:
        if placer_str >= target_str:
            return True

    return placer_str > target_str  # default: strictly greater


# ------------------------------------------------------------------------- Roam

# Card ids whose roams may cover an enemy of equal strength ("can roam onto enemies of equal strength"). A card
# that grants this to others belongs in roam_covers_equal below instead.
ROAM_COVERS_EQUAL: set[str] = set()


def can_roam(state: GameState, unit: UnitInstance) -> bool:
    """Whether `unit` has Roam (printed today; a card that grants it to others hooks in here)."""
    return "Roam" in state.cards[unit.card_id].keywords


# Card ids that, while on top of their crossroad, give their controller one free roam each turn ("once per turn, one of
# your animals may roam without spending an action").
FREE_ROAM_CARDS: set[str] = set()


def free_roams(state: GameState, player: str) -> int:
    """Free roams `player`'s board gives them each turn (spent before an action; effects.free_roams_left)."""
    if not FREE_ROAM_CARDS:
        return 0
    return sum(1 for st in state.board.values()
               if st and st[-1].owner == player and st[-1].card_id in FREE_ROAM_CARDS)


def roam_covers_equal(state: GameState, unit: UnitInstance) -> bool:
    """Whether `unit`'s roams may cover an enemy of equal strength (no card does this yet)."""
    return unit.card_id in ROAM_COVERS_EQUAL


# ------------------------------------------------------------------------ Reach

def reach_crossroads(state: GameState, player: str, n: int, occ: set) -> set[str]:
    """Crossroads within `n` steps of a launch point, counting along paths and jumping over whatever stands on them
    (Reach N, keywords.md). The launch points are `player`'s den (its front crossroads are one step away, as for an
    ordinary placement: Reach 1) and the connected crossroads `occ` they occupy. Never a den: a Reach unit captures
    only along an unbroken chain, which ordinary placement already covers."""
    gm = state.game_map
    dist = {cr: 0 for cr in occ}
    for cr in gm.hq_front(player):
        dist.setdefault(cr, 1)
    frontier = sorted(dist, key=dist.get)
    queue = deque(frontier)
    while queue:
        cr = queue.popleft()
        d = dist[cr]
        if d >= n:
            continue
        for nb in gm.neighbors(cr):
            if nb not in dist or dist[nb] > d + 1:
                dist[nb] = d + 1
                queue.append(nb)
    return {cr for cr, d in dist.items() if d <= n}


def ignores_connection(state: GameState, card_id: str) -> bool:
    """Flight: the unit may be placed without a connection to its HQ."""
    return "Flight" in state.cards[card_id].keywords


def _neighbors_of_friendly_tag(state: GameState, owner: str, tag: str) -> set[str]:
    """Crossroads adjacent to any crossroad `owner` tops with a `tag` unit."""
    gm = state.game_map
    out: set[str] = set()
    for cr, stack in state.board.items():
        top = stack[-1] if stack else None
        if top and top.owner == owner and tag in state.cards[top.card_id].tags:
            out |= set(gm.neighbors(cr))
    return out


def extra_placement_crossroads(state: GameState, card_id: str, owner: str) -> set[str]:
    """Crossroads a card may target ignoring connection, beyond the normal rules.

    Cougar: may be placed adjacent to any Cat you control, ignoring connection.
    Coyote (id `outrider`): while you control one, your *other* Canines may be placed adjacent to any
    Canine you control, ignoring connection.
    """
    card = state.cards[card_id]
    out: set[str] = set()
    if card_id == "cougar":
        out |= _neighbors_of_friendly_tag(state, owner, "Cat")
    if "Canine" in card.tags and card_id != "outrider" and _controls(state, owner, "outrider"):
        out |= _neighbors_of_friendly_tag(state, owner, "Canine")
    return out


def can_be_removed(state: GameState, unit: UnitInstance) -> bool:
    """Armor (keyword-review decision A2, 2026-07-02): *physics*. The unit cannot be
    removed, moved (bounced), or eaten by ANY ability - the enemy's or its own
    controller's (covering is placement, not an ability, and stays legal). Consulted by
    every effect-removal/bounce/eat path regardless of who chose it.

    Carriers: Methuselah, Armadillo, Cairn.
    """
    return "Armor" not in state.cards[unit.card_id].keywords


def _adjacent_to_friendly_armadillo(state: GameState, unit: UnitInstance) -> bool:
    """True if `unit` is a board top with a friendly Armadillo topping an adjacent crossroad.
    Armadillo's aura grants Stealth to the units it shelters (food_otk overhaul 2026-07-05)."""
    cr = next((c for c, st in state.board.items() if st and st[-1].iid == unit.iid), None)
    if cr is None:
        return False
    return any((top := state.top_unit(nb)) and top.owner == unit.owner
               and top.card_id == "armadillo"
               for nb in state.game_map.neighbors(cr))


def can_be_chosen(state: GameState, unit: UnitInstance, by_player: str) -> bool:
    """Stealth (keyword-review decisions A2/B/E, 2026-07-02): the unit cannot be *chosen*
    by an enemy ability - consulted ONLY when building option lists an enemy chooser picks
    from. Mass, random, and automatic effects (and an Apex Predator's eat)
    (Pestis/Rhinoceros/Brutus/Sirocco, Grizzly Bear, Hippopotamus, King Theron,
    Pufferfish) do NOT consult this and hit Stealth units normally.

    Carriers: Black Panther (keyword); Armadillo grants it to adjacent friendly units (aura).
    """
    card = state.cards[unit.card_id]
    if by_player != unit.owner:
        if "Stealth" in card.keywords or _adjacent_to_friendly_armadillo(state, unit):
            return False
    return True


def regions_starved(state, player: str) -> bool:
    """The Unnamed Giant: while `player` controls it (on top of its crossroad), their regions
    produce no food."""
    return any(st and st[-1].owner == player and st[-1].card_id == "unnamed_giant"
               for st in state.board.values())
