"""The raw position, as the evaluation network sees it: everything the rules read, nothing an agent summarised.

Agreed with Martin line by line and audited against the engine on 2026-11-03 (`knowledge/bot-diagnosis-2026-11-01.md`,
"The raw position"). What a card's printed text says comes through its card id (one learned vector per id, shared across
every zone); what differs between two copies of the same card is given as state. Read from the seat of `me`, the board
mirrored so my den is always at the bottom (map_b is symmetric under the row flip); only on a quiet position, which is
how both searches call the evaluation.

A position is three kinds of input:

- the 15 crossroads, each as its top piece and the card directly beneath (`cr_card`, `cr_owner`, `top_num`, `under_num`);
- bags of cards (`BAGS`): a list of (card index, weight) pairs each, read by the network as a weighted sum of card
  vectors: my hand, my deck, the opponent's unseen pool (hand and deck as one multiset, priced from the card id and
  public growth only, never from the hidden instance), the piles, locked cards, cards played this turn, pieces buried
  deeper than second, the Macaw's last Roar;
- the global numbers (`GLOBALS`).

`inventory_check` is the upkeep: every state field, piece field and turn-flag key the engine keeps is either encoded
here or listed in `EXCLUDED` with its reason, so a mechanic that adds state fails the test until someone decides what
the network sees.
"""

from __future__ import annotations

from typing import Optional

from ..engine import rules
from ..engine.state import GameState, UnitInstance, WILD, other_player
from ..engine.statics import hand_revealed
from ..engine.strength import aura_sources, card_strength, effective_strength, placement_strength, raw_strength

N_CROSSROADS = 15
OWNER_NONE, OWNER_MINE, OWNER_THEIRS, OWNER_WILD = 0, 1, 2, 3

# A scheduled effect's kind, from its step's op (`effects.schedule` and the Venom/Poison appends).
SCHED_OPS = ("remove_iid", "gain_food", "draw", "grant_action", "cap_actions", "egg_hatch", "bird_egg_hatch", "locust_eat")

TOP_NUM = (
    "str_my_turn", "str_their_turn", "counter", "inked", "charge_spent", "granted_roam", "roamed_this_turn",
    "play_order_rank", "buried_count",
    "sched_n", "sched_min_remaining", "sched_ticks_mine", "sched_ticks_theirs", "sched_ticks_every", "sched_while_buried",
    *[f"sched_op_{op}" for op in SCHED_OPS], "sched_op_other", "sched_amount",
)
UNDER_NUM = (
    "str_if_surfaced", "counter", "inked", "charge_spent", "granted_roam",
    "sched_n", "sched_min_remaining", "sched_removal", "more_beneath",
)
BAGS = (
    "hand", "hand_w", "deck", "deck_w",
    "pool", "pool_w", "opp_hand", "opp_hand_w", "opp_deck", "opp_deck_w",
    "pile_mine", "pile_mine_w", "pile_theirs", "pile_theirs_w", "pile_unknown",
    "locked_mine", "locked_theirs", "played_mine", "played_theirs",
    "deep_mine", "deep_theirs", "macaw_mine", "macaw_theirs",
)
GLOBALS = (
    "food_mine", "food_theirs", "side_to_move", "actions_left", "idle_turns", "placed_this_turn",
    "food_gained_mine", "food_gained_theirs", "lost_mine", "lost_theirs", "lost_wild", "removed_any",
    "roams_mine", "roams_theirs", "free_roams_mine", "free_roams_used_mine", "free_roams_theirs", "free_roams_used_theirs",
    "titan_discount_mine", "titan_discount_theirs", "woodpecker_mine", "woodpecker_theirs",
    "hungry_eaten_mine", "hungry_eaten_theirs",
    "hand_n_mine", "hand_n_theirs", "deck_n_mine", "deck_n_theirs", "revealed",
    "deep_removals_mine", "deep_removals_theirs", "pile_n",
)

# State the engine keeps that the network is not given, each with its reason (the inventory test reads this).
EXCLUDED = {
    # GameState
    "game_map": "fixed", "cards": "fixed", "config": "fixed", "rng": "not readable by a player",
    "starting_decks": "Capybara and the Python fold into strength and counters", "first_player": "mulligan only",
    "turn_counter": "read for the first turn (actions_left), the 400-turn cap and relative comparisons (lock, roar_twice), all encoded",
    "_next_iid": "bookkeeping", "next_iid": "bookkeeping", "play_seq": "given as each piece's rank in its owner's play order, not the raw counter",
    "effect_stack": "never evaluated mid-resolution", "pending": "never evaluated with a choice open",
    "result": "a decided game is scored by the search, not the network",
    "units_placed_this_turn": "encoded (placed_this_turn)", "actions_taken_this_turn": "encoded (actions_left)",
    "card_strength_counters": "folded into every strength", "jelly": "folded into deck and pool strengths",
    "roar_twice": "encoded (woodpecker_*, live this turn only)", "hungry_eaten": "encoded", "last_roar": "encoded (macaw_* bags)",
    "inked": "encoded per piece", "pile_owners": "encoded (pile bags by owner)", "remove_pile": "encoded",
    "scheduled": "encoded per piece", "turn_flags": "see the flag keys", "idle_turns": "encoded",
    "board": "encoded", "hands": "encoded", "decks": "encoded", "food": "encoded", "current": "encoded (side_to_move)",
    "events": "a log", "cause": "a log", "cause_iid": "a log", "strength_sources": "where each counter came from: the counter is encoded",
    # UnitInstance
    "card_id": "encoded", "owner": "encoded", "iid": "bookkeeping",
    "placed_on_turn": "written by the engine, read by no rule", "strength_counter": "encoded",
    "locked_until_turn": "encoded (locked_* bags, lock live only)", "retaliation_used": "encoded (charge_spent)",
    "granted_roam": "encoded",
    # turn_flags keys (the `<p>`/`<iid>` suffix stripped)
    "played_": "encoded (played_* bags)", "food_gained_": "encoded", "lost_": "encoded", "removed_any": "encoded",
    "roams_": "encoded", "roamed_": "encoded per piece", "any_roamed": "roams_mine + roams_theirs > 0",
    "free_roams_": "encoded", "free_roams_used_": "encoded", "free_roam_iid_": "never written by the engine",
    "titan_discount_": "encoded", "bonus_actions_": "encoded (actions_left)", "action_cap_": "encoded (actions_left)",
    "falstaff_": "dead unless config.cap_falstaff", "gain_str_": "no card reacts to it",
}


def card_index(cards: dict) -> dict[str, int]:
    """Card id -> row in the card table; stable under the registry's sorted ids."""
    return {cid: i for i, cid in enumerate(sorted(cards))}


def mirrored_crossroads(state: GameState, me: str) -> list[str]:
    """The crossroads in slot order, rows flipped for B so my den front is always row 1."""
    def key(cr):
        r, c = (int(x) for x in cr.split(","))
        return (6 - r if me == "B" else r, c)
    return sorted(state.game_map.crossroads, key=key)


def _owner_code(owner: str, me: str) -> int:
    return OWNER_MINE if owner == me else OWNER_WILD if owner == WILD else OWNER_THEIRS


def _sched_on(state: GameState, iid: int) -> list[dict]:
    return [s for s in state.scheduled if s["iid"] == iid]


def _sched_features(state: GameState, entries: list[dict], me: str) -> list[float]:
    """The scheduled-effect part of a top piece: count, nearest firing, whose turns tick it, buried behaviour, kind, amount."""
    if not entries:
        return [0.0] * (6 + len(SCHED_OPS) + 2)
    ticks_mine = sum(s["owner"] == me for s in entries)
    ticks_theirs = sum(s["owner"] not in (me, WILD) for s in entries)
    ticks_every = sum(s["owner"] == WILD for s in entries)
    ops = [0.0] * len(SCHED_OPS)
    other = 0.0
    amount = 0.0
    for s in entries:
        op = s["step"].get("op")
        if op in SCHED_OPS:
            ops[SCHED_OPS.index(op)] += 1.0
        else:
            other += 1.0
        amount += float(s["step"].get("amount", s["step"].get("n", 0)) or 0)
    return [len(entries), min(s["remaining"] for s in entries) / 3.0, ticks_mine, ticks_theirs, ticks_every,
            float(any(s["while_buried"] for s in entries)), *ops, other, amount / 10.0]


def _strength_both_turns(state: GameState, unit: UnitInstance) -> tuple[float, float]:
    """Effective strength on my turn and on the opponent's (Giraffe, Crocodile and Cape Buffalo read whose turn it is)."""
    cur = state.current
    try:
        state.current = unit.owner
        mine = effective_strength(state, unit, aura_sources(state))
        state.current = other_player(unit.owner) if unit.owner != WILD else cur
        theirs = effective_strength(state, unit, aura_sources(state))
    finally:
        state.current = cur
    return mine / 10.0, theirs / 10.0


def _pool_price(state: GameState, owner: str, cid: str) -> float:
    """A card's strength as it would leave `owner`'s deck or hand, from public growth only: the Dung Beetle's reached form,
    the card's growth in every zone; the royal jelly is added per copy by the caller."""
    return card_strength(state, state.eaten_form(owner, cid), owner) / 10.0


def _jelly_copies(state: GameState, owner: str, cid: str) -> tuple[int, float]:
    """(copies of `cid` still carrying the royal jelly among owner's unseen cards, the counter)."""
    val = state.jelly.get(owner, {}).get(cid)
    if not val:
        return 0, 0.0
    if isinstance(val, int):
        return val, float(state.jelly_counter(owner, cid))
    return int(val[0]), float(val[1])


def extract(state: GameState, me: str) -> dict:
    """The raw position from `me`'s seat. Returns dense lists and bags; `pack` turns many into arrays."""
    if state.pending is not None or state.effect_stack:
        raise ValueError("the raw position is read only on a quiet position")
    opp = other_player(me)
    idx = card_index(state.cards)
    crs = mirrored_crossroads(state, me)
    flags = state.turn_flags
    tc = state.turn_counter

    # play-order rank among each owner's top pieces
    tops = [(stack[-1], cr) for cr, stack in state.board.items() if stack]
    rank: dict[int, float] = {}
    for owner in (me, opp, WILD):
        mine = sorted((u for u, _ in tops if u.owner == owner), key=lambda u: u.play_seq)
        for r, u in enumerate(mine):
            rank[u.iid] = r / 10.0

    cr_card: list[list[int]] = []
    cr_owner: list[list[int]] = []
    top_num: list[list[float]] = []
    under_num: list[list[float]] = []
    bags: dict[str, list[tuple[int, float]]] = {b: [] for b in BAGS}
    deep_removals = {me: 0.0, opp: 0.0}
    for cr in crs:
        stack = state.board.get(cr) or []
        if not stack:
            cr_card.append([-1, -1]); cr_owner.append([OWNER_NONE, OWNER_NONE])
            top_num.append([0.0] * len(TOP_NUM)); under_num.append([0.0] * len(UNDER_NUM))
            continue
        top = stack[-1]
        s_my, s_their = _strength_both_turns(state, top)
        sched = _sched_on(state, top.iid)
        top_num.append([
            s_my, s_their, top.strength_counter / 5.0, float(top.iid in state.inked), float(top.retaliation_used),
            float(top.granted_roam), float(bool(flags.get(f"roamed_{top.iid}"))), rank.get(top.iid, 0.0),
            (len(stack) - 1) / 4.0, *_sched_features(state, sched, me),
        ])
        if len(stack) >= 2:
            under = stack[-2]
            usched = _sched_on(state, under.iid)
            under_num.append([
                max(0, raw_strength(state, under)) / 10.0, under.strength_counter / 5.0, float(under.iid in state.inked),
                float(under.retaliation_used), float(under.granted_roam), float(len(usched)),
                (min(s["remaining"] for s in usched) / 3.0) if usched else 0.0,
                float(any(s["step"].get("op") == "remove_iid" for s in usched)), (len(stack) - 2) / 3.0,
            ])
            cr_card.append([idx[top.card_id], idx[under.card_id]])
            cr_owner.append([_owner_code(top.owner, me), _owner_code(under.owner, me)])
        else:
            under_num.append([0.0] * len(UNDER_NUM))
            cr_card.append([idx[top.card_id], -1])
            cr_owner.append([_owner_code(top.owner, me), OWNER_NONE])
        for deep in stack[:-2]:
            if deep.owner == WILD:
                continue
            bags["deep_mine" if deep.owner == me else "deep_theirs"].append((idx[deep.card_id], 1.0))
            if any(s["step"].get("op") == "remove_iid" for s in _sched_on(state, deep.iid)):
                deep_removals[deep.owner] += 1.0

    # my hand and deck: mine to know in full
    for u in state.hands[me]:
        bags["hand"].append((idx[u.card_id], 1.0))
        bags["hand_w"].append((idx[u.card_id], placement_strength(state, u) / 10.0))
        if u.locked_until_turn > tc:
            bags["locked_mine"].append((idx[u.card_id], 1.0))
    _deck_bags(state, me, state.decks[me], idx, bags["deck"], bags["deck_w"])

    # the opponent's cards: the public multiset of their hand and deck, priced from the card id and public growth only
    revealed = hand_revealed(state, opp)
    opp_locked = [u for u in state.hands[opp] if u.locked_until_turn > tc]
    for u in opp_locked:
        bags["locked_theirs"].append((idx[u.card_id], 1.0))
    if revealed:
        for u in state.hands[opp]:
            if u in opp_locked:
                continue
            bags["opp_hand"].append((idx[u.card_id], 1.0))
            bags["opp_hand_w"].append((idx[u.card_id], placement_strength(state, u) / 10.0))
        _deck_bags(state, opp, state.decks[opp], idx, bags["opp_deck"], bags["opp_deck_w"])
    else:
        locked_ids = [u.card_id for u in opp_locked]
        pool = [u.card_id for u in state.hands[opp]] + list(state.decks[opp])
        for cid in locked_ids:
            pool.remove(cid)
        _deck_bags(state, opp, pool, idx, bags["pool"], bags["pool_w"])

    for cid, owner in zip(state.remove_pile, state.pile_owners):
        if owner == me:
            bags["pile_mine"].append((idx[cid], 1.0)); bags["pile_mine_w"].append((idx[cid], _pool_price(state, me, cid)))
        elif owner == opp:
            bags["pile_theirs"].append((idx[cid], 1.0)); bags["pile_theirs_w"].append((idx[cid], _pool_price(state, opp, cid)))
        else:
            bags["pile_unknown"].append((idx[cid], 1.0))
    for p, bag in ((me, "played_mine"), (opp, "played_theirs")):
        for _iid, cid in flags.get(f"played_{p}", []):
            bags[bag].append((idx[cid], 1.0))
    for p, bag in ((me, "macaw_mine"), (opp, "macaw_theirs")):
        last = state.last_roar.get(p)
        if last in idx:
            bags[bag].append((idx[last], 1.0))

    actions_left = (rules.turn_actions(state) - state.actions_taken_this_turn) if state.current == me else 0
    g = [
        state.food[me] / 50.0, state.food[opp] / 50.0, float(state.current == me), actions_left / 2.0,
        float(state.idle_turns), state.units_placed_this_turn / 2.0,
        flags.get(f"food_gained_{me}", 0) / 20.0, flags.get(f"food_gained_{opp}", 0) / 20.0,
        flags.get(f"lost_{me}", 0) / 2.0, flags.get(f"lost_{opp}", 0) / 2.0, flags.get(f"lost_{WILD}", 0) / 2.0,
        float(bool(flags.get("removed_any"))),
        flags.get(f"roams_{me}", 0) / 2.0, flags.get(f"roams_{opp}", 0) / 2.0,
        float(flags.get(f"free_roams_{me}", 0)), float(flags.get(f"free_roams_used_{me}", 0)),
        float(flags.get(f"free_roams_{opp}", 0)), float(flags.get(f"free_roams_used_{opp}", 0)),
        float(bool(flags.get(f"titan_discount_{me}"))), float(bool(flags.get(f"titan_discount_{opp}"))),
        float(state.roar_twice.get(me) == tc), float(state.roar_twice.get(opp) == tc),
        state.hungry_eaten.get(me, 0) / 20.0, state.hungry_eaten.get(opp, 0) / 20.0,
        len(state.hands[me]) / 8.0, len(state.hands[opp]) / 8.0, len(state.decks[me]) / 30.0, len(state.decks[opp]) / 30.0,
        float(revealed), deep_removals[me], deep_removals[opp], len(state.remove_pile) / 10.0,
    ]
    assert len(g) == len(GLOBALS)
    return {"cr_card": cr_card, "cr_owner": cr_owner, "top_num": top_num, "under_num": under_num, "bags": bags, "globals": g}


def _deck_bags(state: GameState, owner: str, cids: list[str], idx: dict, plain: list, weighted: list) -> None:
    """A deck (or the pool) as two bags: counts, and strengths as each copy would leave the deck (reached form, growth,
    the royal jelly on the copies it reached)."""
    jelly_left: dict[str, int] = {}
    for cid in cids:
        form = state.eaten_form(owner, cid)
        plain.append((idx[form], 1.0))
        price = _pool_price(state, owner, cid)
        if cid not in jelly_left:
            jelly_left[cid] = _jelly_copies(state, owner, cid)[0]
        if jelly_left[cid] > 0:
            jelly_left[cid] -= 1
            price += _jelly_copies(state, owner, cid)[1] / 10.0
        weighted.append((idx[form], price))


def inventory_check(state_cls=GameState, unit_cls=UnitInstance, effects_src: Optional[str] = None) -> list[str]:
    """Every field of the state and of a piece, and every turn-flag key written in the engine, is encoded or excluded.
    Returns the names that are neither (empty when the encoding is up to date)."""
    import inspect, re
    from ..engine import effects, rules as rules_mod
    missing = []
    init_fields = [p for p in inspect.signature(state_cls.__init__).parameters if p not in ("self",)]
    for f in init_fields:
        if f not in EXCLUDED:
            missing.append(f"GameState.{f}")
    for f in unit_cls.__slots__:
        if f not in EXCLUDED:
            missing.append(f"UnitInstance.{f}")
    src = effects_src if effects_src is not None else inspect.getsource(effects) + inspect.getsource(rules_mod)
    keys = set(re.findall(r'turn_flags(?:\.get\(|\[|\.setdefault\(|\.pop\()f?"([a-z_]+)', src))
    for k in sorted(keys):
        if k not in EXCLUDED:
            missing.append(f"turn_flags[{k}]")
    return missing
