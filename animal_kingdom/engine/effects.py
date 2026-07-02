"""The effect engine: placement mechanic, event dispatch, and the effect-stack interpreter.

Design (plan decision 6): effect resolution is **declarative op-step data** on
`state.effect_stack`, drained by `resolve()`. A step that needs a choice surfaces as
`state.pending`; the choice arrives as a normal Action and resumes the paused op. Steps
are plain dicts (serializable / cloneable / replayable) - never closures.

Layering: this module sits below rules.py (rules orchestrates; effects holds the core
mechanic + card behavior). It imports state/statics/strength only - never rules.

Card behavior lives in two registries:
  - EFFECTS[card_id] -> {hook_name: fn}   (triggered effects; push op-steps)
  - OPS[op_name] -> fn(state, step)        (the op interpreter; returns PendingRequest|None)

M2a implements a representative slice; remaining cards are added in M2b.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .actions import SKIP, ChoiceAction, PlaceAction
from .state import EngineError, GameState, Result, UnitInstance, other_player
from . import statics
from .strength import effective_strength


# ============================================================== pending / requests

@dataclass
class PendingRequest:
    """What an op returns when it needs a choice; converted into state.pending."""
    mode: str                       # "choice" or "place"
    chooser: str
    optional: bool = False
    options: Optional[list] = None        # mode == "choice": serializable option values
    placements: Optional[list] = None     # mode == "place": [{card_id, target}]

    def to_pending(self) -> dict:
        p = {"mode": self.mode, "chooser": self.chooser, "optional": self.optional}
        if self.mode == "choice":
            p["options"] = list(self.options)
        else:
            p["placements"] = list(self.placements)
        return p


def legal_pending(state: GameState) -> list:
    """Actions offered while a choice is pending."""
    p = state.pending
    if p["mode"] == "choice":
        acts = [ChoiceAction(o) for o in p["options"]]
    else:  # "place"
        acts = [PlaceAction(pl["card_id"], tuple(pl["target"])) for pl in p["placements"]]
    if p.get("optional"):
        acts.append(ChoiceAction(SKIP))
    return acts


def apply_pending(state: GameState, action) -> None:
    """Record the chosen option onto the paused step, then continue resolving."""
    p = state.pending
    step = state.effect_stack[-1]  # the paused op (left on the stack by resolve)
    if p["mode"] == "choice":
        step["choice"] = action.choice
    else:  # "place"
        if isinstance(action, ChoiceAction) and action.choice == SKIP:
            step["place_action"] = SKIP
        else:
            step["place_action"] = {"card_id": action.card_id, "target": list(action.target)}
    state.pending = None
    # Resolution is driven by the caller (rules._resolve_and_maybe_end_turn).


# ===================================================================== resolve loop

def resolve(state: GameState) -> None:
    """Drain the effect stack until empty, a choice is needed, or the game is won."""
    while state.pending is None and state.result is None and state.effect_stack:
        step = state.effect_stack.pop()
        req = OPS[step["op"]](state, step)
        if req is not None:           # op needs a choice: put the step back and pause
            state.effect_stack.append(step)
            state.pending = req.to_pending()
            return


# ============================================================ placement + events

def do_placement(state: GameState, player: str, card_id: str, target) -> None:
    """Place an occupant from hand. Handles food cost, HQ capture, and crossroad landing."""
    unit = _take_from_hand(state, player, card_id)
    cost = state.cards[card_id].food_cost          # "Costs X food" (decision F): paid on placement
    if cost:
        state.food[player] -= cost
    state.units_placed_this_turn += 1
    kind, where = target
    if kind == "hq":
        if state.cards[card_id].is_unit:           # Landmarks cannot capture an HQ (decision C)
            state.result = Result(player, "hq_capture")
        return
    _land_unit(state, player, unit, where)


def _take_from_hand(state: GameState, player: str, card_id: str) -> UnitInstance:
    """Remove and return a hand instance of `card_id`, preferring the highest-counter copy
    (so a buffed copy is the one actually played - PlaceAction is keyed only by card id)."""
    candidates = [u for u in state.hands[player] if u.card_id == card_id]
    unit = max(candidates, key=lambda u: u.strength_counter)
    state.hands[player].remove(unit)
    return unit


def _land_unit(state: GameState, player: str, unit: UnitInstance, cr: str) -> None:
    # The same hand instance lands on the board, carrying its strength counter.
    covered = state.top_unit(cr)
    is_apex = "Apex Predator" in state.cards[unit.card_id].keywords
    cover_enemy = None

    # Apex Predator (decision D): eat the occupant it lands on instead of covering it; its
    # Deathrattle / remove triggers fire, then the predator occupies what remains beneath.
    # If the occupant can't be eaten (Immovable, or enemy Stealth - the eat is a chosen
    # single-out, keyword-review decision C3), the predator falls back to a normal cover,
    # burying it — it isn't restricted to prey it can eat.
    if is_apex and covered is not None:
        if (statics.can_be_chosen(state, covered, player)
                and _remove_specific(state, cr, covered, by_player=player, by_card=unit.card_id)):
            covered = state.top_unit(cr)  # ate it: whatever remains beneath is now covered
        elif covered.owner != player:
            cover_enemy = covered         # couldn't eat -> normal cover (King Theron watches)
    elif covered is not None and covered.owner != player:
        cover_enemy = covered            # a normal cover of an enemy (King Theron watches this)

    onto_enemy = covered is not None and covered.owner != player

    unit.placed_on_turn = state.turn_counter
    state.board.setdefault(cr, []).append(unit)

    # Reactive triggers resolve AFTER the placed unit's battlecry (decision 8). The stack
    # is LIFO, so push reactive first (lower) and the battlecry last (on top).
    _push_reactions(state, unit, cr, covered, onto_enemy)
    if cover_enemy is not None:
        _fire_cover_event(state, unit, cover_enemy)
    _fire_play_event(state, unit)        # Queen Honoria: gain food when you play a Colony unit
    _push_hook(state, unit, cr, "on_place")
    if onto_enemy:
        _push_hook(state, unit, cr, "on_place_onto_enemy")


def _fire_cover_event(state, coverer, covered) -> None:
    """King Theron: when one of your Cats covers an enemy unit, remove that enemy (now buried).
    Decision G: House Cat/extra-placement chains can cover multiple enemies in one turn -
    `cap_king_theron` (off by default) limits Theron to one free removal per turn."""
    if "Cat" not in state.cards[coverer.card_id].tags:
        return
    for st in state.board.values():
        top = st[-1] if st else None
        if top and top.owner == coverer.owner and top.card_id == "king_theron":
            if not _capped(state, "cap_king_theron", top):
                state.effect_stack.append(
                    {"op": "remove_iid", "iid": covered.iid, "by_player": coverer.owner,
                     "by_card": coverer.card_id})
            return


def _fire_play_event(state, played) -> None:
    """Queen Honoria: whenever you play a Colony unit, gain food (not for Honoria herself)."""
    if "Colony" not in state.cards[played.card_id].tags:
        return
    for st in state.board.values():
        top = st[-1] if st else None
        if (top and top.owner == played.owner and top.card_id == "queen_honoria"
                and top.iid != played.iid):
            if not _capped(state, "cap_queen_honoria", top):
                gain_food(state, played.owner, state.config.queen_honoria_per_play)


def _push_reactions(state, unit, cr, covered, onto_enemy) -> None:
    # Enemy hippos etc. reacting to a unit placed adjacent.
    for nb in state.game_map.neighbors(cr):
        top = state.top_unit(nb)
        if top and top.owner != unit.owner:
            hook = _hook(state, top.card_id, "on_enemy_placed_adjacent")
            if hook:
                hook(state, top, unit, cr)
    if covered is not None:
        hook = _hook(state, covered.card_id, "on_covered")
        if hook:
            hook(state, covered, unit, cr)
        if "Fragile" in state.cards[covered.card_id].keywords:
            state.effect_stack.append(
                {"op": "remove_iid", "iid": covered.iid, "by_player": unit.owner, "by_effect": False}
            )


def _push_hook(state, unit, cr, hook_name) -> None:
    hook = _hook(state, unit.card_id, hook_name)
    if hook:
        hook(state, unit, cr)


def _hook(state, card_id, hook_name) -> Optional[Callable]:
    return EFFECTS.get(card_id, {}).get(hook_name)


# ================================================================= removal & food

def _dispose(state: GameState, unit: UnitInstance) -> bool:
    """Send a board unit to its destination. Returns True if it entered the Remove Pile
    (a genuine *remove*), False for a "return instead" that never reaches the pile (F9)."""
    if unit.card_id == "opossum":           # "return instead": not a remove, fires no triggers
        state.add_to_hand(unit.owner, "opossum")
        return False
    state.remove_pile.append(unit.card_id)
    return True


def _remove_specific(state, cr, unit, *, by_player, by_effect=True, by_card=None) -> bool:
    """Remove a specific unit from a stack (mid-stack ok). Fires removal reactions. `by_card`
    is the card id of the effect's source unit, if any (for Queen Adira's "a Cat removes")."""
    stack = state.board.get(cr)
    if not stack or unit not in stack:
        return False
    # Only the physics gate lives here (Immovable blocks any effect-removal, whoever chose
    # it). Stealth is a *choice* restriction, enforced where enemy option lists are built
    # (and at the Apex eat), never at resolution - so mass/random/automatic removals
    # (Pestis, Rhino/Bulwark, Grizzly, Hippo, King Theron, Pufferfish) hit Stealth units.
    if by_effect and not statics.can_be_removed(state, unit):
        return False
    stack.remove(unit)
    if not stack:
        del state.board[cr]
    entered_pile = _dispose(state, unit)
    if entered_pile:                        # the remove trigger fires first (F9), then...
        _fire_remove_event(state, unit.card_id, unit.owner, cr, by_player, by_card)
    _fire_on_remove(state, unit)            # ...the unit's own Deathrattle (e.g. Ember relocates)
    return True


def remove_top(state, cr, *, by_player, by_effect=True, by_card=None) -> bool:
    top = state.top_unit(cr)
    if top is None:
        return False
    return _remove_specific(state, cr, top, by_player=by_player, by_effect=by_effect, by_card=by_card)


def _find_unit(state, iid):
    for cr, stack in state.board.items():
        for u in stack:
            if u.iid == iid:
                return cr, u
    return None, None


def _fire_on_remove(state, unit) -> None:
    # A unit leaving the board: its own Deathrattle. (Board-wide reactors to removal events -
    # Vulture/Eon/Jackal/Egg Eater - are wired in Stage 2.2's event engine.)
    hook = _hook(state, unit.card_id, "on_remove")
    if hook:
        hook(state, unit)


def gain_food(state: GameState, player: str, amount: int, *, rider: bool = True) -> None:
    if amount <= 0:
        return
    state.food[player] += amount
    if state.food[player] >= state.game_map.win_food:
        state.result = Result(player, "food")
        return
    # Falstaff: whenever you gain food, gain N more (once per gain event; never recursively).
    if rider:
        falstaffs = sum(1 for st in state.board.values()
                        if st and st[-1].owner == player and st[-1].card_id == "falstaff")
        if falstaffs and not (state.config.cap_falstaff and state.turn_flags.get(f"falstaff_{player}")):
            if state.config.cap_falstaff:
                state.turn_flags[f"falstaff_{player}"] = True
            gain_food(state, player, falstaffs * state.config.falstaff_food_rider, rider=False)


# ============================================ draw / shuffle / remove event engine
#
# Discrete events (decision F2/F9): one event per card drawn, shuffled-into-deck, or
# removed. Board-top units react via on_draw_event / on_shuffle_event / on_remove_event
# hooks (Eon/Vulture/Rattlesnake/Egg Eater/Jackal); a *drawn card* may also react to
# itself via on_draw (Black Swan). Reactors resolve immediately (they only gain food /
# discard), so no extra stack steps and no re-entrancy in this stage. state.py stays free
# of effect imports - these wrappers sit above the card-movement primitives on GameState.

def _fire_event(state, hook_name: str, event: dict) -> None:
    """Dispatch one event to every board-top unit that reacts to it (deterministic order)."""
    for cr in sorted(state.board):
        top = state.board[cr][-1]
        hook = _hook(state, top.card_id, hook_name)
        if hook:
            hook(state, top, cr, event)


def _fire_remove_event(state, card_id: str, owner: str, cr, by_player=None, by_card=None) -> None:
    _fire_event(state, "on_remove_event",
                {"card_id": card_id, "owner": owner, "cr": cr, "tags": state.cards[card_id].tags,
                 "by_player": by_player, "by_card": by_card})


def _fire_draw(state, drawn) -> None:
    for inst in drawn:
        _fire_event(state, "on_draw_event", {"card_id": inst.card_id, "player": inst.owner})
        hook = _hook(state, inst.card_id, "on_draw")     # the drawn card reacting to itself
        if hook:
            hook(state, inst)


def draw_cards(state: GameState, player: str, n: int) -> list:
    """Draw n cards (the canonical draw used by ops/rules) and fire ON_DRAW events."""
    drawn = state.draw(player, n)
    _fire_draw(state, drawn)
    return drawn


def draw_filtered_random(state: GameState, player: str, n: int, spec: str) -> list:
    """Draw up to n cards chosen uniformly at random among the deck cards matching `spec`
    (decision F10: random, no inspection, no choice; fizzle if none). Fires ON_DRAW."""
    drawn = []
    for _ in range(n):
        candidates = [cid for cid in state.decks[player] if _matches(state.cards[cid], spec)]
        if not candidates:
            break
        cid = state.rng.choice(candidates)
        state.decks[player].remove(cid)
        inst = UnitInstance(cid, player, state.new_iid())
        state.hands[player].append(inst)
        drawn.append(inst)
    _fire_draw(state, drawn)
    return drawn


def shuffle_back(state: GameState, player: str, card_ids: list) -> None:
    """Put `card_ids` into the deck, shuffle, and fire one ON_SHUFFLE event per card (F2)."""
    deck = state.decks[player]
    deck.extend(card_ids)
    state.rng.shuffle(deck)
    for cid in card_ids:
        _fire_event(state, "on_shuffle_event", {"card_id": cid, "player": player})


def remove_from_hand(state: GameState, player: str, inst: UnitInstance) -> None:
    """Remove a card from hand to the Remove Pile: a *remove* (fires the remove event) but
    NOT a Deathrattle (it never was on the board). Used by Black Swan, later by Rat."""
    state.hands[player].remove(inst)
    state.remove_pile.append(inst.card_id)
    _fire_remove_event(state, inst.card_id, inst.owner, None)


def _matches(card, spec: str) -> bool:
    """A serializable filter for filtered draws: 'tag:Bird', 'rarity:legendary',
    'strength_min:6' (printed base only; dynamic-strength cards never match)."""
    kind, _, val = spec.partition(":")
    if kind == "tag":
        return val in card.tags
    if kind == "rarity":
        return card.rarity == val
    if kind == "strength_min":
        return isinstance(card.base_strength, int) and card.base_strength >= int(val)
    raise EngineError(f"unknown filter spec {spec!r}")


def _capped(state, flag_name: str, unit: UnitInstance) -> bool:
    """For decision-G once-per-turn caps: True if this reactor already fired this turn under
    an enabled cap (so it should be skipped). Caps default off (config) = uncapped/as printed."""
    if not getattr(state.config, flag_name):
        return False
    key = f"{flag_name}_{unit.iid}"
    if state.turn_flags.get(key):
        return True
    state.turn_flags[key] = True
    return False


# ========================================================== legal placement helper

def legal_placements(state: GameState, player: str, allowed_cards: Optional[set] = None) -> list:
    """All legal placements for `player` (used by rules.legal_actions and play_extra).

    `allowed_cards` (a set of card ids) restricts which hand cards may be played.
    Deterministic order (sorted) for reproducible replay.
    """
    gm = state.game_map
    occ = state.connected_occupied(player)
    enemy = other_player(player)
    enemy_hq = any(cr in occ for cr in gm.hq_front(enemy))  # HQ capture: connection only (not Flight)

    # One placement per distinct hand card id; covering uses the highest-counter copy (the
    # copy that would actually be played - see _take_from_hand).
    best: dict[str, "UnitInstance"] = {}
    for u in state.hands[player]:
        if allowed_cards is not None and u.card_id not in allowed_cards:
            continue
        if u.locked_until_turn > state.turn_counter:    # Skunk lock (F4)
            continue
        cur = best.get(u.card_id)
        if cur is None or u.strength_counter > cur.strength_counter:
            best[u.card_id] = u

    out = []
    for card_id in sorted(best):
        placer = best[card_id]
        card = state.cards[card_id]
        if card.food_cost > state.food[player]:
            continue                                  # "Costs X food": only if affordable (dec. F)
        is_apex = "Apex Predator" in card.keywords
        flight = statics.ignores_connection(state, card_id)
        extra = statics.extra_placement_crossroads(state, card_id, player)
        for cr in sorted(gm.crossroads):
            if not (flight or cr in extra or state.is_connected(player, cr, occ)):
                continue
            top = state.top_unit(cr)
            if is_apex:
                if top is not None and _apex_can_land(state, placer, top):
                    out.append(PlaceAction(card_id, ("cr", cr)))   # must land on an occupant
            elif top is None or top.owner == player:
                out.append(PlaceAction(card_id, ("cr", cr)))
            elif statics.can_cover(state, placer, top):
                out.append(PlaceAction(card_id, ("cr", cr)))
        # Apex Predators and Landmarks can never capture an HQ (decisions C/D).
        if enemy_hq and card.is_unit and not is_apex:
            out.append(PlaceAction(card_id, ("hq", enemy)))
    return out


def _apex_can_land(state: GameState, placer: UnitInstance, top: UnitInstance) -> bool:
    """Apex Predator landing rules (decision D + keyword-review C1): it may land wherever it
    could legally cover - free on your own occupants, `statics.can_cover` vs an enemy, so
    the covering statics apply to apexes exactly as to normal placements: Snow Leopard lets
    an apex Cat land at equal strength, Chameleon is land-on-able regardless of strength,
    and Porcupine ("cannot be covered by enemy units") blocks the landing entirely - quills
    beat teeth. If the occupant is eat-eligible it gets eaten; if not (Immovable / enemy
    Stealth) it is simply covered (see _land_unit)."""
    if top.owner == placer.owner:
        return True
    return statics.can_cover(state, placer, top)


# ============================================================= delayed scheduler

def schedule(state: GameState, owner: str, owner_turn_delay: int, step: dict) -> None:
    """Queue `step` to fire at the start of `owner`'s turn `owner_turn_delay` turns later."""
    due = state.turn_counter + 2 * owner_turn_delay  # a player's turns are 2 apart
    state.scheduled.append({"due": due, "owner": owner, "step": step})


def start_of_turn(state: GameState, player: str) -> None:
    """Fire due scheduled effects and on_start_of_turn hooks for `player` (then caller resolves)."""
    due = [s for s in state.scheduled if s["owner"] == player and s["due"] <= state.turn_counter]
    state.scheduled = [s for s in state.scheduled if s not in due]
    for s in sorted(due, key=lambda x: x["due"], reverse=True):  # earliest ends on top of stack
        state.effect_stack.append(s["step"])
    for cr, stack in sorted(state.board.items()):
        top = stack[-1]
        if top.owner == player:
            hook = _hook(state, top.card_id, "on_start_of_turn")
            if hook:
                hook(state, top, cr)


def end_of_turn(state: GameState, player: str) -> None:
    """Fire on_end_of_turn hooks for `player`'s units (then caller resolves).

    End-of-turn effects are choice-free (auto/deterministic) so the turn can still advance
    without a pending decision - see rules._end_turn.
    """
    for cr, stack in sorted(state.board.items()):
        top = stack[-1]
        if top.owner == player:
            hook = _hook(state, top.card_id, "on_end_of_turn")
            if hook:
                hook(state, top, cr)


# ===================================================================== op registry

def _op_gain_food(state, step):
    gain_food(state, step["player"], step["amount"])
    return None


def _op_draw(state, step):
    draw_cards(state, step["player"], step["n"])
    return None


def _op_draw_filtered(state, step):
    draw_filtered_random(state, step["player"], step["n"], step["spec"])
    return None


def _op_egg_hatch(state, step):
    cr, egg = _find_unit(state, step["iid"])
    if egg is None:
        return None  # egg already gone (e.g. covered while Fragile) - no payoff
    _remove_specific(state, cr, egg, by_player=egg.owner, by_effect=False)
    draw_filtered_random(state, egg.owner, step["n"], step["spec"])
    return None


def _op_raven_dig(state, step):
    player = step["player"]
    drawn = draw_cards(state, player, 2)            # draw 2 (fires ON_DRAW), then...
    shuffled = []
    for inst in drawn:                              # ...shuffle those 2 back (fires ON_SHUFFLE)
        if inst in state.hands[player]:             # a drawn card may have been discarded (Black Swan)
            state.hands[player].remove(inst)
            shuffled.append(inst.card_id)
    if shuffled:
        shuffle_back(state, player, shuffled)
    return None


def _op_owl_peek(state, step):
    """Look at the top 3 of your deck, draw 1 (chosen), shuffle the other 2 back."""
    player = step["player"]
    if "pulled" not in step:
        deck = state.decks[player]
        pulled = [deck.pop() for _ in range(min(3, len(deck)))]  # top of deck = end
        if not pulled:
            return None
        step["pulled"] = pulled
        if len(pulled) == 1:
            step["choice"] = pulled[0]
        else:
            return PendingRequest("choice", player, options=sorted(set(pulled)))
    pulled = list(step["pulled"])
    pulled.remove(step["choice"])
    inst = UnitInstance(step["choice"], player, state.new_iid())
    state.hands[player].append(inst)
    _fire_draw(state, [inst])
    shuffle_back(state, player, pulled)
    return None


def _op_remove_choice(state, step):
    """Remove the top unit at a chosen crossroad among `options`."""
    options = step["options"]
    if not options:
        return None
    if "choice" not in step:
        if len(options) == 1:
            step["choice"] = options[0]
        else:
            return PendingRequest("choice", step["chooser"], optional=step.get("optional", False),
                                  options=options)
    chosen = step["choice"]
    if chosen == SKIP:
        return None
    remove_top(state, chosen, by_player=step["by_player"], by_card=step.get("by_card"))
    return None


def _op_remove_iid(state, step):
    cr, unit = _find_unit(state, step["iid"])
    if unit is not None:
        _remove_specific(state, cr, unit, by_player=step.get("by_player", unit.owner),
                         by_effect=step.get("by_effect", True), by_card=step.get("by_card"))
    return None


def _hand_allowed(state, player, filt: dict) -> set:
    """Hand card ids a play_extra may place: units only (never Landmarks), matching the
    filter `tags_all` / `tags_none` / `exclude_id` (decision F1 per-card constraints)."""
    allowed = set()
    for u in state.hands[player]:
        card = state.cards[u.card_id]
        if not card.is_unit or u.card_id == filt.get("exclude_id"):
            continue
        if any(t not in card.tags for t in filt.get("tags_all", ())):
            continue
        if any(t in card.tags for t in filt.get("tags_none", ())):
            continue
        allowed.add(u.card_id)
    return allowed


def _op_play_extra(state, step):
    """Play one more unit from hand (optionally filtered), as part of resolution (decision F1:
    a full normal placement that doesn't consume the turn action)."""
    if step.get("played"):
        return None
    if "place_action" in step:
        pa = step["place_action"]
        if pa != SKIP:
            do_placement(state, step["chooser"], pa["card_id"], tuple(pa["target"]))
        step["played"] = True
        return None
    allowed = _hand_allowed(state, step["chooser"], step.get("filter", {}))
    placements = legal_placements(state, step["chooser"], allowed)
    if not placements:
        return None
    return PendingRequest("place", step["chooser"], optional=step.get("optional", False),
                          placements=[{"card_id": p.card_id, "target": list(p.target)} for p in placements])


def _op_play_named(state, step):
    """Play a specific named card from hand OR deck (the Prince Leo / Princess Lea twins -
    the one F10 exception to "filtered draws are random"). Optional; if it was fetched from
    the deck and not played, it goes back."""
    player, cid = step["chooser"], step["card_id"]
    if "fetched" not in step:                       # fetch the twin from deck if not in hand
        in_hand = any(u.card_id == cid for u in state.hands[player])
        if not in_hand and cid in state.decks[player]:
            state.decks[player].remove(cid)
            state.add_to_hand(player, cid)
            step["fetched"] = True
        else:
            step["fetched"] = False

    def _return_if_fetched():
        if step["fetched"] and any(u.card_id == cid for u in state.hands[player]):
            state.decks[player].append(_take_from_hand(state, player, cid).card_id)

    if "place_action" in step:
        pa = step["place_action"]
        if pa == SKIP:
            _return_if_fetched()
        else:
            do_placement(state, player, pa["card_id"], tuple(pa["target"]))
        return None
    allowed = {cid} if any(u.card_id == cid for u in state.hands[player]) else set()
    placements = legal_placements(state, player, allowed)
    if not placements:
        _return_if_fetched()
        return None
    return PendingRequest("place", player, optional=True,
                          placements=[{"card_id": p.card_id, "target": list(p.target)} for p in placements])


def _op_grant_strength(state, step):
    """Add a stored strength counter to each target instance (board or hand), firing
    ON_GAIN_STRENGTH for the board units that gain (decision E)."""
    amount = step["amount"]
    for iid in step["iids"]:
        inst = _find_instance(state, iid)
        if inst is None:
            continue
        inst.strength_counter += amount
        if amount > 0 and _crossroad_of(state, iid) is not None:
            _fire_on_gain_strength(state, inst)
    return None


OPS: dict[str, Callable] = {
    "gain_food": _op_gain_food,
    "draw": _op_draw,
    "draw_filtered": _op_draw_filtered,
    "egg_hatch": _op_egg_hatch,
    "raven_dig": _op_raven_dig,
    "owl_peek": _op_owl_peek,
    "remove_choice": _op_remove_choice,
    "remove_iid": _op_remove_iid,
    "play_extra": _op_play_extra,
    "play_named": _op_play_named,
    "grant_strength": _op_grant_strength,
}


# ============================================ instance / strength-counter helpers

def _find_instance(state, iid):
    """An instance by iid, searching the board then both hands (counters live in both)."""
    for stack in state.board.values():
        for u in stack:
            if u.iid == iid:
                return u
    for hand in state.hands.values():
        for u in hand:
            if u.iid == iid:
                return u
    return None


def _crossroad_of(state, iid):
    for cr, stack in state.board.items():
        for u in stack:
            if u.iid == iid:
                return cr
    return None


def _fire_on_gain_strength(state, unit) -> None:
    """ON_GAIN_STRENGTH reactor for a board unit (Fox, Bush Dog): at most once per turn per
    unit, which also guards against grant->gain->grant loops (decision E)."""
    hook = _hook(state, unit.card_id, "on_gain_strength")
    if hook is None:
        return
    flag = f"gain_str_{unit.iid}"
    if state.turn_flags.get(flag):
        return
    state.turn_flags[flag] = True
    hook(state, unit, _crossroad_of(state, unit.iid))


def _adjacent_enemy_targets(state, unit, cr, *, max_strength=None, min_strength=None,
                            chosen=True):
    """Crossroads adjacent to `cr` whose enemy top unit is removable and within the optional
    [min_strength, max_strength] effective-strength bounds. `chosen=True` (the enemy player
    picks from this list) also excludes Stealth units; mass/random effects pass
    `chosen=False` so Stealth does not hide from them (keyword-review decision B)."""
    out = []
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if not (top and top.owner != unit.owner):
            continue
        if not statics.can_be_removed(state, top):
            continue
        if chosen and not statics.can_be_chosen(state, top, unit.owner):
            continue
        s = effective_strength(state, top)
        if max_strength is not None and s > max_strength:
            continue
        if min_strength is not None and s < min_strength:
            continue
        out.append(nb)
    return out


def _adjacent_friendly_units(state, unit, cr):
    """Crossroads adjacent to `cr` whose top is a friendly, removable unit. Stealth never
    hides from its own controller; Immovable blocks its own controller's sacrifices too
    (decision A2: that's the keyword's cost - e.g. Carmilla can't eat a Scrooge)."""
    out = []
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if (top and top.owner == unit.owner and state.cards[top.card_id].is_unit
                and statics.can_be_removed(state, top)):
            out.append(nb)
    return out


def _control_tag_count(state, player, *tags) -> int:
    """How many crossroads `player` tops with a unit carrying all of `tags`."""
    return sum(
        1 for st in state.board.values()
        if st and st[-1].owner == player and all(t in state.cards[st[-1].card_id].tags for t in tags)
    )


def _friendly_adjacent_canine_iids(state, unit, cr):
    """Top units adjacent to `cr` that are friendly Canines (for the Canine buffers)."""
    iids = []
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if top and top.owner == unit.owner and "Canine" in state.cards[top.card_id].tags:
            iids.append(top.iid)
    return iids


def _grant(state, iids, amount):
    if iids and amount:
        state.effect_stack.append({"op": "grant_strength", "iids": list(iids), "amount": amount})


# ============================================================== card behavior

# --- Canine buff/tempo deck (Stage 2.1) ---

def _gray_wolf_place(state, unit, cr):
    # Remove an adjacent enemy of strength <= this unit's (buffed) strength.
    targets = _adjacent_enemy_targets(state, unit, cr, max_strength=effective_strength(state, unit))
    if targets:
        state.effect_stack.append(
            {"op": "remove_choice", "chooser": unit.owner, "by_player": unit.owner,
             "by_card": "gray_wolf", "options": targets})


def _coyote_place(state, unit, cr):
    if effective_strength(state, unit) >= state.config.coyote_draw_threshold:
        state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1})


def _dhole_place(state, unit, cr):
    _grant(state, _friendly_adjacent_canine_iids(state, unit, cr), state.config.dhole_grant)


def _clarion_place(state, unit, cr):
    # Give +1 to all OTHER Canines you control, on the board and in hand.
    iids = [u.iid for st in state.board.values() for u in st
            if u.owner == unit.owner and u.iid != unit.iid and "Canine" in state.cards[u.card_id].tags]
    iids += [u.iid for u in state.hands[unit.owner]
             if u.iid != unit.iid and "Canine" in state.cards[u.card_id].tags]
    _grant(state, iids, state.config.clarion_grant)


def _red_wolf_place(state, unit, cr):
    iids = [u.iid for u in state.hands[unit.owner] if "Canine" in state.cards[u.card_id].tags]
    _grant(state, iids, state.config.red_wolf_grant)


def _dingo_end_of_turn(state, unit, cr):
    # Give +1 to a friendly adjacent Canine; auto-pick deterministically (lowest iid).
    iids = _friendly_adjacent_canine_iids(state, unit, cr)
    if iids:
        _grant(state, [min(iids)], state.config.dingo_grant)


def _fox_gain_strength(state, unit, cr):
    state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1})


def _bush_dog_gain_strength(state, unit, cr):
    _grant(state, _friendly_adjacent_canine_iids(state, unit, cr), state.config.bush_dog_grant)


def _shuck_place(state, unit, cr):
    # Return a removed Canine from the Remove Pile to hand with a +2 counter.
    canines = sorted({cid for cid in state.remove_pile if "Canine" in state.cards[cid].tags})
    if not canines:
        return
    if len(canines) == 1:
        _shuck_return(state, unit.owner, canines[0])
    else:
        state.effect_stack.append(
            {"op": "shuck_return", "chooser": unit.owner, "options": canines})


def _shuck_return(state, owner, card_id):
    state.remove_pile.remove(card_id)
    state.add_to_hand(owner, card_id, strength_counter=state.config.shuck_grant)


def _op_shuck_return(state, step):
    options = step["options"]
    if "choice" not in step:
        return PendingRequest("choice", step["chooser"], options=options)
    _shuck_return(state, step["chooser"], step["choice"])
    return None


OPS["shuck_return"] = _op_shuck_return


# --- Food OTK / shared (kept from M2a; behavior unchanged) ---

def _pufferfish_covered(state, covered, coverer, cr):
    if coverer.owner == covered.owner:
        return  # only triggers vs an enemy coverer
    # Remove the coverer, then the pufferfish (both pushed; coverer resolves first).
    state.effect_stack.append(
        {"op": "remove_iid", "iid": covered.iid, "by_player": covered.owner, "by_effect": False})
    state.effect_stack.append(
        {"op": "remove_iid", "iid": coverer.iid, "by_player": covered.owner, "by_effect": True})


# --- Egg Control deck: draw/shuffle/remove food engine + filtered draws (Stage 2.2) ---

def _eon_event(state, unit, cr, event):           # any draw/shuffle/remove -> +1
    if not _capped(state, "cap_eon", unit):
        gain_food(state, unit.owner, state.config.eon_food)


def _vulture_remove_event(state, unit, cr, event):  # any card removed -> +2
    if not _capped(state, "cap_vulture", unit):
        gain_food(state, unit.owner, state.config.vulture_food)


def _rattlesnake_shuffle_event(state, unit, cr, event):  # any card shuffled -> +5
    if not _capped(state, "cap_rattlesnake", unit):
        gain_food(state, unit.owner, state.config.rattlesnake_food)


def _egg_eater_remove_event(state, unit, cr, event):     # an Egg removed -> +10
    if "Egg" in event["tags"] and not _capped(state, "cap_egg_eater", unit):
        gain_food(state, unit.owner, state.config.egg_eater_food)


def _jackal_remove_event(state, unit, cr, event):        # an *adjacent* unit removed -> +3
    if event["cr"] is not None and event["cr"] in state.game_map.neighbors(cr):
        if not _capped(state, "cap_jackal", unit):
            gain_food(state, unit.owner, state.config.jackal_food)


def _black_swan_drawn(state, inst):
    # Both players remove a random card from their hand (seeded; a remove, not a Deathrattle).
    for player in ("A", "B"):
        hand = state.hands[player]
        if hand:
            remove_from_hand(state, player, state.rng.choice(hand))


def _owl_place(state, unit, cr):
    state.effect_stack.append({"op": "owl_peek", "player": unit.owner})


def _raven_place(state, unit, cr):
    state.effect_stack.append({"op": "raven_dig", "player": unit.owner})


def _ember_remove(state, unit):
    # Deathrattle: shuffle Ember back into its owner's deck (it is already in the Remove Pile).
    if "ember" in state.remove_pile:
        state.remove_pile.remove("ember")
        shuffle_back(state, unit.owner, ["ember"])


def _mouse_place(state, unit, cr):
    state.effect_stack.append({"op": "draw_filtered", "player": unit.owner, "n": 1, "spec": "tag:Rodent"})


def _fathom_place(state, unit, cr):
    state.effect_stack.append({"op": "draw_filtered", "player": unit.owner, "n": 1, "spec": "rarity:legendary"})


def _bird_egg_place(state, unit, cr):
    schedule(state, unit.owner, state.config.egg_hatch_delay,
             {"op": "egg_hatch", "iid": unit.iid, "n": state.config.egg_hatch_draw, "spec": "tag:Bird"})


def _snake_egg_place(state, unit, cr):
    schedule(state, unit.owner, state.config.egg_hatch_delay,
             {"op": "egg_hatch", "iid": unit.iid, "n": state.config.egg_hatch_draw, "spec": "tag:Snake"})


def _opossum_place(state, unit, cr):
    _push_draw(state, unit.owner, 1)                    # Battlecry (its Deathrattle return is in _dispose)


def _gazelle_remove(state, unit):
    gain_food(state, unit.owner, state.config.gazelle_food)


def _impala_remove(state, unit):
    draw_cards(state, unit.owner, 2)


# --- Extra placements / HQ-adjacency / landmarks / start-of-turn (Stage 2.3) ---

def _controls_another_tag(state, unit, tag) -> bool:
    return any(
        st and st[-1].owner == unit.owner and st[-1].iid != unit.iid and tag in state.cards[st[-1].card_id].tags
        for st in state.board.values()
    )


def _push_play_extra(state, owner, *, filter=None, optional=False):
    state.effect_stack.append(
        {"op": "play_extra", "chooser": owner, "filter": filter or {}, "optional": optional})


def _jerboa_place(state, unit, cr):
    _push_play_extra(state, unit.owner)                  # play another unit (mandatory if able)


def _greywhisker_place(state, unit, cr):
    o = unit.owner                                       # gain 1, draw 1, then may play 1 more
    _push_play_extra(state, o, optional=True)
    state.effect_stack.append({"op": "draw", "player": o, "n": 1})
    state.effect_stack.append({"op": "gain_food", "player": o, "amount": state.config.greywhisker_food})


def _house_cat_place(state, unit, cr):
    if _controls_another_tag(state, unit, "Cat"):
        _push_play_extra(state, unit.owner, filter={"tags_all": ["Cat"], "exclude_id": "house_cat"})


def _dog_place(state, unit, cr):
    if _controls_another_tag(state, unit, "Canine"):
        _push_play_extra(state, unit.owner, filter={"tags_all": ["Canine"], "exclude_id": "dog"})


def _queen_bee_place(state, unit, cr):
    _push_play_extra(state, unit.owner, filter={"tags_all": ["Worker"]})


def _termite_queen_place(state, unit, cr):
    _push_play_extra(state, unit.owner, filter={"tags_all": ["Colony"], "tags_none": ["Queen"]}, optional=True)


def _twin_place(twin_id):
    def handler(state, unit, cr):
        state.effect_stack.append({"op": "play_named", "chooser": unit.owner, "card_id": twin_id})
    return handler


def _hq_adjacent_draw(state, unit, cr):
    if cr in state.game_map.hq_front(other_player(unit.owner)):  # next to the enemy base (F6)
        state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1})


def _aurum_start(state, unit, cr):
    state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1})


def _fig_tree_place(state, unit, cr):
    schedule(state, unit.owner, 1, {"op": "fig_tree_payout", "iid": unit.iid,
                                    "player": unit.owner, "amount": state.config.fig_tree_food})


def _watering_hole_place(state, unit, cr):
    schedule(state, unit.owner, 1, {"op": "watering_hole_payout", "iid": unit.iid,
                                    "player": unit.owner, "n": 1, "spec": "strength_min:6"})


def _op_fig_tree_payout(state, step):
    # Fragile: if the landmark was covered/removed before its turn, deny the payoff
    # (same pattern as _op_egg_hatch - see _find_unit).
    cr, unit = _find_unit(state, step["iid"])
    if unit is None:
        return None
    gain_food(state, step["player"], step["amount"])
    return None


def _op_watering_hole_payout(state, step):
    cr, unit = _find_unit(state, step["iid"])
    if unit is None:
        return None  # covered while Fragile - no payoff
    draw_filtered_random(state, step["player"], step["n"], step["spec"])
    return None


OPS["fig_tree_payout"] = _op_fig_tree_payout
OPS["watering_hole_payout"] = _op_watering_hole_payout


# ===================================== Stage 2.4: remaining triggered / removal / utility

def _push_gain(state, owner, amount):
    if amount:
        state.effect_stack.append({"op": "gain_food", "player": owner, "amount": amount})


def _push_draw(state, owner, n):
    state.effect_stack.append({"op": "draw", "player": owner, "n": n})


def _push_remove_choice(state, owner, by_card, targets):
    if targets:
        state.effect_stack.append({"op": "remove_choice", "chooser": owner, "by_player": owner,
                                   "by_card": by_card, "options": targets})


def _adjacent_enemy_unit_crossroads(state, unit, cr, *, chosen=True):
    """Adjacent crossroads topped by an enemy *unit* that can be moved (for bounces).
    Immovable can't be moved by anyone; Stealth only hides from a `chosen` pick (Skunk),
    not from a mass bounce (Sirocco, `chosen=False`) - keyword-review decision B."""
    out = []
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if not (top and top.owner != unit.owner and state.cards[top.card_id].is_unit
                and statics.can_be_removed(state, top)):
            continue
        if chosen and not statics.can_be_chosen(state, top, unit.owner):
            continue
        out.append(nb)
    return out


def _controls_two_same_colony(state, player) -> bool:
    from collections import Counter
    counts = Counter(
        st[-1].card_id for st in state.board.values()
        if st and st[-1].owner == player and "Colony" in state.cards[st[-1].card_id].tags)
    return any(v >= 2 for v in counts.values())


def _bounce(state, cr, top, *, lock_until=0):
    """Return a board unit to its owner's hand (not a removal: no Remove Pile, no triggers)."""
    state.board[cr].remove(top)
    if not state.board[cr]:
        del state.board[cr]
    state.add_to_hand(top.owner, top.card_id).locked_until_turn = lock_until


# --- Removal battlecries (Cats / Colony / Ramp) ---

def _jaguar_place(state, unit, cr):
    _push_remove_choice(state, unit.owner, "jaguar",
                        _adjacent_enemy_targets(state, unit, cr, max_strength=state.config.jaguar_max))


def _serval_place(state, unit, cr):
    _push_remove_choice(state, unit.owner, "serval",
                        _adjacent_enemy_targets(state, unit, cr, min_strength=state.config.serval_min))


def _stoop_place(state, unit, cr):
    _push_remove_choice(state, unit.owner, "stoop",
                        _adjacent_enemy_targets(state, unit, cr, max_strength=state.config.stoop_max))


def _soldier_ant_place(state, unit, cr):
    if _control_tag_count(state, unit.owner, "Colony") >= state.config.colony_synergy_threshold:
        _push_remove_choice(state, unit.owner, "soldier_ant", _adjacent_enemy_targets(state, unit, cr))


def _rhinoceros_place(state, unit, cr):
    for nb in _adjacent_enemy_targets(state, unit, cr, max_strength=state.config.rhinoceros_max,
                                      chosen=False):        # mass AoE hits Stealth
        state.effect_stack.append({"op": "remove_iid", "iid": state.top_unit(nb).iid,
                                   "by_player": unit.owner, "by_card": "rhinoceros"})


def _bulwark_place(state, unit, cr):
    for nb in _adjacent_enemy_targets(state, unit, cr, chosen=False):  # uncapped AoE, hits Stealth
        state.effect_stack.append({"op": "remove_iid", "iid": state.top_unit(nb).iid,
                                   "by_player": unit.owner, "by_card": "bulwark"})


def _hippo_enemy_placed(state, hippo, placed, cr):
    # Automatic trigger, nobody "chose" the target: Stealth doesn't hide (decision B).
    if (effective_strength(state, placed) <= state.config.hippopotamus_max
            and statics.can_be_removed(state, placed)):
        state.effect_stack.append({"op": "remove_iid", "iid": placed.iid,
                                   "by_player": hippo.owner, "by_card": "hippopotamus"})


# --- Hand-cost / friendly-sacrifice removal (Aggro / Food OTK) ---

def _rat_place(state, unit, cr):
    targets = _adjacent_enemy_targets(state, unit, cr)
    if targets and state.hands[unit.owner]:
        state.effect_stack.append({"op": "rat_kill", "chooser": unit.owner, "options": targets})


def _op_rat_kill(state, step):
    chooser = step["chooser"]
    if "choice" not in step:
        return PendingRequest("choice", chooser, optional=True, options=step["options"])
    if step["choice"] == SKIP or not state.hands[chooser]:
        return None
    remove_from_hand(state, chooser, state.hands[chooser][0])   # pay a hand card (a remove, not a Deathrattle)
    remove_top(state, step["choice"], by_player=chooser, by_card="rat")
    return None


def _hornet_place(state, unit, cr):
    targets = _adjacent_enemy_targets(state, unit, cr)
    if targets:
        state.effect_stack.append({"op": "hornet_kill", "chooser": unit.owner, "iid": unit.iid, "options": targets})


def _op_hornet_kill(state, step):
    if "choice" not in step:
        return PendingRequest("choice", step["chooser"], optional=True, options=step["options"])
    if step["choice"] == SKIP:
        return None
    cr_self, hornet = _find_unit(state, step["iid"])
    remove_top(state, step["choice"], by_player=step["chooser"], by_card="hornet")
    if hornet is not None:
        _remove_specific(state, cr_self, hornet, by_player=hornet.owner, by_effect=False)
    return None


def _carmilla_place(state, unit, cr):
    state.effect_stack.append({"op": "carmilla_sac", "chooser": unit.owner, "remaining": 3})


def _op_carmilla_sac(state, step):
    chooser = step["chooser"]
    if "choice" in step:
        if step["choice"] != SKIP:
            remove_top(state, step["choice"], by_player=chooser, by_card="carmilla")
            draw_cards(state, chooser, 1)
            if step["remaining"] - 1 > 0:
                state.effect_stack.append({"op": "carmilla_sac", "chooser": chooser, "remaining": step["remaining"] - 1})
        return None
    options = _friendly_unit_crossroads(state, chooser)
    if not options:
        return None
    return PendingRequest("choice", chooser, optional=True, options=options)


def _black_widow_place(state, unit, cr):
    targets = _adjacent_friendly_units(state, unit, cr)
    if targets:
        state.effect_stack.append({"op": "black_widow_sac", "chooser": unit.owner, "options": targets})


def _op_black_widow_sac(state, step):
    chooser = step["chooser"]
    if "choice" not in step:
        return PendingRequest("choice", chooser, optional=True, options=step["options"])
    if step["choice"] == SKIP:
        return None
    remove_top(state, step["choice"], by_player=chooser, by_card="black_widow")
    draw_cards(state, chooser, 1)
    return None


def _friendly_unit_crossroads(state, player):
    # Own sacrifices: Stealth never hides from its controller; Immovable still refuses
    # (decision A2 - Carmilla/Black Widow can't eat a Tortoise or Scrooge).
    return sorted(
        c for c, st in state.board.items()
        if st[-1].owner == player and state.cards[st[-1].card_id].is_unit
        and statics.can_be_removed(state, st[-1]))


# --- Mass effects (Aggro) ---

def _pestis_place(state, unit, cr):
    options = sorted(nb for nb in state.game_map.neighbors(cr) if state.board.get(nb))
    if options:
        state.effect_stack.append({"op": "pestis_wipe", "chooser": unit.owner, "options": options})


def _op_pestis_wipe(state, step):
    if "choice" not in step:
        opts = step["options"]
        if len(opts) == 1:
            step["choice"] = opts[0]
        else:
            return PendingRequest("choice", step["chooser"], options=opts)
    target = step["choice"]
    # Remove the entire stack, both players, top-down. Immovable occupants are skipped in
    # place, NOT a shield: everything else in the stack is still wiped around them
    # (keyword-review decision B amendment). Stealth doesn't hide from a mass wipe.
    stack = state.board.get(target)
    for unit in reversed(list(stack or [])):
        _remove_specific(state, target, unit, by_player=step["chooser"], by_card="pestis")
    return None


def _sirocco_place(state, unit, cr):
    for nb in _adjacent_enemy_unit_crossroads(state, unit, cr, chosen=False):  # mass bounce
        state.effect_stack.append({"op": "bounce_iid", "iid": state.top_unit(nb).iid})


def _op_bounce_iid(state, step):
    cr, u = _find_unit(state, step["iid"])
    if u is not None:
        _bounce(state, cr, u)
    return None


def _skunk_place(state, unit, cr):
    options = _adjacent_enemy_unit_crossroads(state, unit, cr)
    if options:
        state.effect_stack.append({"op": "skunk_bounce", "chooser": unit.owner, "options": options})


def _op_skunk_bounce(state, step):
    if "choice" not in step:
        opts = step["options"]
        if len(opts) == 1:
            step["choice"] = opts[0]
        else:
            return PendingRequest("choice", step["chooser"], options=opts)
    top = state.top_unit(step["choice"])
    if top is not None:                                  # locked through the owner's next turn (F4)
        _bounce(state, step["choice"], top, lock_until=state.turn_counter + 2)
    return None


def _lemming_place(state, unit, cr):
    hand_lemmings = [u for u in state.hands[unit.owner] if u.card_id == "lemming"]
    deck_lemming_count = state.decks[unit.owner].count("lemming")
    sources = [("hand", inst) for inst in hand_lemmings] + [("deck", None)] * deck_lemming_count
    state.rng.shuffle(sources)
    empty = [nb for nb in state.game_map.neighbors(cr) if not state.board.get(nb)]
    state.rng.shuffle(empty)
    for (kind, inst), spot in zip(sources, empty):       # auto-placed copies' Battlecries fizzle (F8)
        if kind == "hand":
            state.hands[unit.owner].remove(inst)
        else:
            state.decks[unit.owner].remove("lemming")
            inst = UnitInstance("lemming", unit.owner, state.new_iid())
        inst.placed_on_turn = state.turn_counter
        state.board.setdefault(spot, []).append(inst)


# --- Team triggers (Cats); King Theron's cover trigger fires from _fire_cover_event ---

def _queen_adira_remove_event(state, unit, cr, event):
    if (event.get("by_player") == unit.owner and event["owner"] != unit.owner
            and event.get("by_card") and "Cat" in state.cards[event["by_card"]].tags):
        if not _capped(state, "cap_queen_adira", unit):
            draw_cards(state, unit.owner, 1)


# --- Food gains (Colony / Food OTK) ---

def _worker_ant_place(state, unit, cr):
    _push_gain(state, unit.owner, state.config.worker_ant_food)


def _worker_bee_place(state, unit, cr):
    amount = state.config.worker_bee_food
    if _control_tag_count(state, unit.owner, "Worker") - 1 > 0:   # another Worker besides itself
        amount += state.config.worker_bee_extra
    _push_gain(state, unit.owner, amount)


def _flying_squirrel_place(state, unit, cr):
    _push_gain(state, unit.owner, state.config.flying_squirrel_food)


def _squirrel_place(state, unit, cr):
    _push_gain(state, unit.owner, state.config.squirrel_food)


def _chipmunk_place(state, unit, cr):
    _push_gain(state, unit.owner, state.config.chipmunk_food_now)
    schedule(state, unit.owner, 1, {"op": "gain_food", "player": unit.owner, "amount": state.config.chipmunk_food_later})


def _queen_marabunta_place(state, unit, cr):
    others = _control_tag_count(state, unit.owner, "Colony") - 1   # other friendly Colony units
    _push_gain(state, unit.owner, state.config.queen_marabunta_per_colony * max(0, others))


def _worker_wasp_eot(state, unit, cr):
    _push_gain(state, unit.owner, state.config.worker_wasp_food)


def _methuselah_eot(state, unit, cr):
    _push_gain(state, unit.owner, state.config.methuselah_food)


# --- Conditional draws (Cats / Colony / Aggro) ---

def _lynx_place(state, unit, cr):
    if _controls_another_tag(state, unit, "Cat"):
        _push_draw(state, unit.owner, 1)


def _caracal_onto_enemy(state, unit, cr):
    _push_draw(state, unit.owner, 1)


def _bat_place(state, unit, cr):
    _push_draw(state, unit.owner, 1)


def _nurse_bee_place(state, unit, cr):
    if _controls_two_same_colony(state, unit.owner):
        _push_draw(state, unit.owner, 2)


def _nurse_bumblebee_place(state, unit, cr):
    if _control_tag_count(state, unit.owner, "Colony") >= state.config.colony_synergy_threshold:
        _push_draw(state, unit.owner, 2)


def _termite_king_place(state, unit, cr):
    if _control_tag_count(state, unit.owner, "Colony", "Queen") >= 1:
        _push_draw(state, unit.owner, 1)


# --- Delayed (Ramp / Food OTK) ---

def _black_bear_place(state, unit, cr):
    schedule(state, unit.owner, state.config.black_bear_delay,
             {"op": "draw", "player": unit.owner, "n": state.config.black_bear_draw})


def _grizzly_place(state, unit, cr):
    schedule(state, unit.owner, state.config.grizzly_bear_delay,
             {"op": "grizzly_strike", "iid": unit.iid, "by_player": unit.owner})


def _op_grizzly_strike(state, step):
    cr, grizzly = _find_unit(state, step["iid"])
    if grizzly is None:
        return None
    targets = _adjacent_enemy_targets(state, grizzly, cr, chosen=False)  # random, not chosen
    if targets:
        remove_top(state, state.rng.choice(targets), by_player=step["by_player"], by_card="grizzly_bear")
    return None


def _scrooge_place(state, unit, cr):
    o = unit.owner
    stored = state.food[o]
    state.food[o] = 0                                    # bank all food now (F7)
    schedule(state, o, state.config.scrooge_delay,
             {"op": "gain_food", "player": o, "amount": stored * state.config.scrooge_multiplier})


# --- Reveal (Ramp) ---

def _base_int(state, card_id):
    b = state.cards[card_id].base_strength
    return b if isinstance(b, int) else 0


def _andean_condor_place(state, unit, cr):
    o = unit.owner
    mine, theirs = state.decks[o], state.decks[other_player(o)]
    if not mine:
        return                                           # empty own deck: fizzle
    their_str = _base_int(state, theirs[-1]) if theirs else 0
    if _base_int(state, mine[-1]) > their_str:           # strictly greater printed base (F13)
        _push_draw(state, o, 1)


def _oxpecker_place(state, unit, cr):
    n = sum(1 for cid in state.starting_decks.get(unit.owner, ())
            if isinstance(state.cards[cid].base_strength, int) and state.cards[cid].base_strength >= 6)
    _push_gain(state, unit.owner, n)


OPS.update({
    "rat_kill": _op_rat_kill,
    "hornet_kill": _op_hornet_kill,
    "carmilla_sac": _op_carmilla_sac,
    "black_widow_sac": _op_black_widow_sac,
    "pestis_wipe": _op_pestis_wipe,
    "bounce_iid": _op_bounce_iid,
    "skunk_bounce": _op_skunk_bounce,
    "grizzly_strike": _op_grizzly_strike,
})


EFFECTS: dict[str, dict[str, Callable]] = {
    # Canine buff/tempo (anthems Raksha/Lobo/African Wild Dog/Verminus + statics live in
    # strength.py / statics.py - no handler needed here).
    "gray_wolf": {"on_place": _gray_wolf_place},
    "coyote": {"on_place": _coyote_place},
    "dhole": {"on_place": _dhole_place},
    "clarion": {"on_place": _clarion_place},
    "red_wolf": {"on_place": _red_wolf_place},
    "dingo": {"on_end_of_turn": _dingo_end_of_turn},
    "fox": {"on_gain_strength": _fox_gain_strength},
    "bush_dog": {"on_gain_strength": _bush_dog_gain_strength},
    "shuck": {"on_place": _shuck_place},
    "jackal": {"on_remove_event": _jackal_remove_event},
    # Egg Control: draw/shuffle/remove food engine + filtered random draws.
    "eon": {"on_draw_event": _eon_event, "on_shuffle_event": _eon_event,
            "on_remove_event": _eon_event},
    "vulture": {"on_remove_event": _vulture_remove_event},
    "rattlesnake": {"on_shuffle_event": _rattlesnake_shuffle_event},
    "egg_eater": {"on_remove_event": _egg_eater_remove_event},
    "black_swan": {"on_draw": _black_swan_drawn},
    "owl": {"on_place": _owl_place},
    "raven": {"on_place": _raven_place},
    "ember": {"on_remove": _ember_remove},
    "mouse": {"on_place": _mouse_place},
    "bird_egg": {"on_place": _bird_egg_place},
    "snake_egg": {"on_place": _snake_egg_place},
    # Food OTK: filtered draw + Deathrattle payoffs (Opossum's return lives in _dispose).
    "fathom": {"on_place": _fathom_place},
    "opossum": {"on_place": _opossum_place},
    "gazelle": {"on_remove": _gazelle_remove},
    "impala": {"on_remove": _impala_remove},
    # Stage 2.3: extra placements (F1), HQ-adjacency draws (F6), start-of-turn, Landmarks.
    # Apex Predator (tiger/anaconda/polar_bear/borealis/aquila) and "Costs X food"
    # (borealis/aquila/bulwark/elephant) are handled in _land_unit / legal_placements.
    "jerboa": {"on_place": _jerboa_place},
    "greywhisker": {"on_place": _greywhisker_place},
    "house_cat": {"on_place": _house_cat_place},
    "dog": {"on_place": _dog_place},
    "queen_bee": {"on_place": _queen_bee_place},
    "termite_queen": {"on_place": _termite_queen_place},
    "prince_leo": {"on_place": _twin_place("princess_lea")},
    "princess_lea": {"on_place": _twin_place("prince_leo")},
    "cheetah": {"on_place": _hq_adjacent_draw},
    "falcon": {"on_place": _hq_adjacent_draw},
    "aurum": {"on_start_of_turn": _aurum_start},
    "fig_tree": {"on_place": _fig_tree_place},
    "watering_hole": {"on_place": _watering_hole_place},
    # Stage 2.4: removal battlecries (King Theron's cover trigger fires from _fire_cover_event).
    "jaguar": {"on_place": _jaguar_place},
    "serval": {"on_place": _serval_place},
    "stoop": {"on_place": _stoop_place},
    "soldier_ant": {"on_place": _soldier_ant_place},
    "rhinoceros": {"on_place": _rhinoceros_place},
    "bulwark": {"on_place": _bulwark_place},
    "hippopotamus": {"on_enemy_placed_adjacent": _hippo_enemy_placed},
    # Hand-cost / friendly-sacrifice removal.
    "rat": {"on_place": _rat_place},
    "hornet": {"on_place": _hornet_place},
    "carmilla": {"on_place": _carmilla_place},
    "black_widow": {"on_place": _black_widow_place},
    # Mass effects.
    "pestis": {"on_place": _pestis_place},
    "sirocco": {"on_place": _sirocco_place},
    "skunk": {"on_place": _skunk_place},
    "lemming": {"on_place": _lemming_place},
    # Team triggers.
    "queen_adira": {"on_remove_event": _queen_adira_remove_event},
    # Food gains.
    "worker_ant": {"on_place": _worker_ant_place},
    "worker_bee": {"on_place": _worker_bee_place},
    "flying_squirrel": {"on_place": _flying_squirrel_place},
    "squirrel": {"on_place": _squirrel_place},
    "chipmunk": {"on_place": _chipmunk_place},
    "queen_marabunta": {"on_place": _queen_marabunta_place},
    "worker_wasp": {"on_end_of_turn": _worker_wasp_eot},
    "methuselah": {"on_end_of_turn": _methuselah_eot},
    # Conditional draws.
    "lynx": {"on_place": _lynx_place},
    "caracal": {"on_place_onto_enemy": _caracal_onto_enemy},
    "bat": {"on_place": _bat_place},
    "nurse_bee": {"on_place": _nurse_bee_place},
    "nurse_bumblebee": {"on_place": _nurse_bumblebee_place},
    "termite_king": {"on_place": _termite_king_place},
    # Delayed.
    "black_bear": {"on_place": _black_bear_place},
    "grizzly_bear": {"on_place": _grizzly_place},
    "scrooge": {"on_place": _scrooge_place},
    # Reveal.
    "andean_condor": {"on_place": _andean_condor_place},
    "oxpecker": {"on_place": _oxpecker_place},
    # Shared.
    "pufferfish": {"on_covered": _pufferfish_covered},
}
