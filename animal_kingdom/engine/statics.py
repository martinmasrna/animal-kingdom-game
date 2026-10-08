"""Static modifiers - evaluated *during* legal-action generation and resolution, NOT via
the event bus (handoff §7.1). These change legality/targeting, not game events.

Covered here: covering-rule overrides, connection bypass, removal immunity, untargetability,
the keywords an animal has right now (printed, given by a neighbour, or lost to ink), grazing
and region income modifiers, and who plays with their hand revealed. Each is keyed off card id /
keyword and composes into a small set of predicates the rules and effects call.

An "effect" here is anything printed on a card that isn't its strength: an Octopus's ink
(`inked`) switches a unit's keywords and effects off until the inking player's next turn, so
every static below asks `active` of the unit it reads.
"""

from __future__ import annotations

from collections import deque
from typing import Optional

from .state import GameState, UnitInstance
from .strength import effective_strength, placement_strength


# ------------------------------------------------------------------ ink / tops

def inked(state: GameState, unit: UnitInstance) -> bool:
    """Octopus ink: the unit has lost its keywords and effects until the inking player's next turn."""
    until = state.inked.get(unit.iid)
    return until is not None and state.turn_counter < until


def active(state: GameState, unit: UnitInstance) -> bool:
    return not (state.inked and inked(state, unit))


def active_tops(state: GameState, player: str, card_id: str) -> list[UnitInstance]:
    """`player`'s top units of `card_id` whose effects work (not inked)."""
    return [st[-1] for st in state.board.values()
            if st and st[-1].owner == player and st[-1].card_id == card_id and active(state, st[-1])]


def _controls(state: GameState, player: str, card_id: str) -> bool:
    """True if `player` controls (tops a stack with) a working unit of `card_id`."""
    return any(st and st[-1].owner == player and st[-1].card_id == card_id and active(state, st[-1])
               for st in state.board.values())


def crossroad_of(state: GameState, unit: UnitInstance) -> Optional[str]:
    for cr, st in state.board.items():
        for u in st:
            if u is unit or u.iid == unit.iid:
                return cr
    return None


# --------------------------------------------------------------------- keywords

# Auras that give an adjacent ally a keyword: card id -> (keyword, the family it's limited to, or None).
KEYWORD_AURAS = {
    "armadillo": ("Stealth", None),               # "Your adjacent animals have Stealth."
    "capybara": ("Armor", None),                  # "Your adjacent animals have Armor."
    "fish_legend_jellyfish": ("Poison", "Fish"),  # "Your adjacent Fish have Poison."
}


def unit_keywords(state: GameState, unit: UnitInstance, cr: Optional[str] = None) -> frozenset:
    """The keywords a board unit has right now: printed, plus any an adjacent ally's aura gives it; none while inked."""
    if state.inked and inked(state, unit):
        return frozenset()
    card = state.cards[unit.card_id]
    kws = card.keywords
    if not any(st and st[-1].owner == unit.owner and st[-1].card_id in KEYWORD_AURAS for st in state.board.values()):
        return kws
    cr = cr if cr is not None else crossroad_of(state, unit)
    if cr is None:
        return kws
    extra = set()
    for nb in state.game_map.neighbors(cr):
        top = state.top_unit(nb)
        if top is None or top.owner != unit.owner or top.card_id not in KEYWORD_AURAS or not active(state, top):
            continue
        kw, family = KEYWORD_AURAS[top.card_id]
        if family is None or family in card.tags:
            extra.add(kw)
    return kws | extra if extra else kws


def has_keyword(state: GameState, unit: UnitInstance, kw: str, cr: Optional[str] = None) -> bool:
    return kw in unit_keywords(state, unit, cr)


# --------------------------------------------------------------------- covering

def can_cover(state: GameState, placer: UnitInstance, target: UnitInstance, *, roaming: bool = False) -> bool:
    """May `placer` cover the enemy `target` unit? `placer` is a hand instance being placed, or (`roaming`) a board
    unit moving onto it, whose strength is its live one on the board.

    Only called for covering an ENEMY top unit (own-stacking needs no strength check).
    Base rule is strictly-greater strength; the modifiers below override it.
    """
    placer_card = state.cards[placer.card_id]
    owner = placer.owner

    # Chameleon covers units of any strength (its own side needs no strength anyway).
    if placer_card.id == "chameleon" and (not roaming or active(state, placer)):
        return True

    placer_str = effective_strength(state, placer) if roaming else placement_strength(state, placer)
    target_str = effective_strength(state, target)

    if roaming:
        if roam_covers_equal(state, placer) and placer_str >= target_str:
            return True
    else:
        # Leopard: "Your other Cats can be placed on enemies of equal or lower strength." (placing, not roaming)
        if "Cat" in placer_card.tags and placer_str >= target_str and any(
                u is not placer for u in active_tops(state, owner, "leopard")):
            return True
        # The legendary Piranha: "Your Fish can be placed on enemies with strength up to the number of Fish you control."
        if "Fish" in placer_card.tags and _controls(state, owner, "fish_legend_piranha"):
            fish = sum(1 for st in state.board.values()
                       if st and st[-1].owner == owner and "Fish" in state.cards[st[-1].card_id].tags)
            if target_str <= fish:
                return True

    return placer_str > target_str  # default: strictly greater


# ------------------------------------------------------------------------- Roam

def can_roam(state: GameState, unit: UnitInstance) -> bool:
    """Whether `unit` has Roam right now (printed, and not inked)."""
    return "Roam" in state.cards[unit.card_id].keywords and active(state, unit)


# Card ids that, while on top of their crossroad, give their controller one free roam each turn for one of their animals
# of a family ("Once each turn, an allied Canine can roam for free."): card id -> the family.
FREE_ROAM_CARDS: dict[str, str] = {"clarion": "Canine"}


def free_roams(state: GameState, player: str, unit: Optional[UnitInstance] = None) -> int:
    """Free roams `player`'s board gives them each turn (spent before an action; effects.free_roams_left). With `unit`,
    only those that animal may use (a Clarion's goes to a Canine)."""
    n = 0
    for st in state.board.values():
        top = st[-1] if st else None
        if top and top.owner == player and top.card_id in FREE_ROAM_CARDS and active(state, top):
            if unit is None or FREE_ROAM_CARDS[top.card_id] in state.cards[unit.card_id].tags:
                n += 1
    return n


def roam_covers_equal(state: GameState, unit: UnitInstance) -> bool:
    """Whether `unit`'s roams may cover an enemy of equal strength (Dhole: "Your animals can roam onto enemies of equal
    strength", id `red_wolf`)."""
    return _controls(state, unit.owner, "red_wolf")


# ------------------------------------------------------------------------ Reach

def reach_of(state: GameState, card_id: str) -> int:
    """How far a card lands (Reach N), 0 for none: printed, or the Great White Shark's "If an animal was removed this
    turn, this has Reach 3."."""
    card = state.cards[card_id]
    if card_id == "great_white_shark" and state.turn_flags.get("removed_any"):
        return state.config.shark_reach
    return card.reach


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


# ------------------------------------------------------------ Armor and Stealth

def can_be_removed(state: GameState, unit: UnitInstance, cr: Optional[str] = None) -> bool:
    """Armor (keyword-review decision A2, 2026-07-02): *physics*. The unit cannot be
    removed, moved (bounced), or eaten by ANY ability - the enemy's or its own
    controller's (covering is placement, not an ability, and stays legal). Consulted by
    every effect-removal/bounce/eat path regardless of who chose it.

    Carriers: Methuselah, Armadillo, Cairn, Tortoise, the legendary Honey Badger; Capybara gives it to its neighbours.
    """
    return "Armor" not in unit_keywords(state, unit, cr)


def can_be_chosen(state: GameState, unit: UnitInstance, by_player: str, cr: Optional[str] = None) -> bool:
    """Stealth (keyword-review decisions A2/B/E, 2026-07-02): the unit cannot be *chosen*
    by an enemy ability - consulted ONLY when building option lists an enemy chooser picks
    from. Mass, random, and automatic effects (and an Apex Predator's eat) do NOT consult
    this and hit Stealth units normally.

    Carriers: Black Panther, the legendary Honey Badger, the Butterfly's later stages; Armadillo gives it to its
    neighbours.
    """
    if by_player != unit.owner:
        return "Stealth" not in unit_keywords(state, unit, cr)
    return True


# ------------------------------------------------------------- regions, grazing

def regions_of(state: GameState, player: str) -> list:
    """Regions where `player` occupies every corner (overview.md §10)."""
    return [r for r in state.game_map.regions.values() if all(state.owner_of(c) == player for c in r.corners)]


def grazing(state: GameState, unit: UnitInstance, cr: Optional[str] = None) -> bool:
    """An animal grazes while it's a corner of a region its owner controls (effects-pass.md, the herd). Only a top unit
    grazes: a buried one holds no corner."""
    cr = cr if cr is not None else crossroad_of(state, unit)
    if cr is None or state.top_unit(cr) is not unit:
        return False
    return any(cr in r.corners and all(state.owner_of(c) == unit.owner for c in r.corners)
               for r in state.game_map.regions.values())


def regions_starved(state, player: str) -> bool:
    """The Unnamed Giant: while `player` controls it (on top of its crossroad), their regions
    produce no food."""
    return _controls(state, player, "unnamed_giant")


def region_food_modifier(state: GameState, player: str) -> int:
    """What each of `player`'s regions produces on top of its printed food: +5 for each legendary Wildebeest they
    control ("Your regions produce 5 more food."), -5 for each legendary Boar their opponent controls ("Your opponent's
    regions produce 5 less food."). A region never produces less than nothing."""
    from .state import other_player
    cfg = state.config
    return (cfg.migration_bonus * len(active_tops(state, player, "hoofed_legend_wildebeest"))
            - cfg.boar_penalty * len(active_tops(state, other_player(player), "hoofed_legend_boar")))


def food_cap(state: GameState) -> Optional[int]:
    """Methuselah: "Each player gains at most 20 food per turn." While either player tops a crossroad with a working
    Methuselah (a buried or inked one rules nothing, like every static), the most food each player may gain in the
    current turn; None when no cap holds."""
    if any(active_tops(state, p, "methuselah") for p in ("A", "B")):
        return state.config.methuselah_food_cap
    return None


# ------------------------------------------------------------------- hidden info

def hand_revealed(state: GameState, player: str) -> bool:
    """`player` plays with their hand revealed while their opponent controls the legendary Giraffe."""
    from .state import other_player
    return _controls(state, other_player(player), "hoofed_legend_giraffe")
