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

from .actions import SKIP, ChoiceAction, PlaceAction, RoamAction
from .state import EngineError, GameState, Result, UnitInstance, other_player
from . import statics
from .strength import effective_strength, placement_strength


# ============================================================== pending / requests

@dataclass
class PendingRequest:
    """What an op returns when it needs a choice; converted into state.pending."""
    mode: str                       # "choice" or "place"
    chooser: str
    optional: bool                  # may the player skip it: always said, never assumed
    options: Optional[list] = None        # mode == "choice": serializable option values
    placements: Optional[list] = None     # mode == "place": [{card_id, target}]
    kind: Optional[str] = None            # "mulligan" for the setup choice (bots keep by default)
    from_deck_reveal: bool = False        # options are cards just peeked/drawn from the hidden
                                          # deck (Owl, Raven). Generic provenance tag: a search
                                          # bot that re-samples deck order (determinize) knows
                                          # the specific option identities are noise in
                                          # lookahead and may collapse the choice instead of
                                          # branching on every one. Pure engine data.

    def to_pending(self) -> dict:
        p = {"mode": self.mode, "chooser": self.chooser, "optional": self.optional}
        if self.mode == "choice":
            p["options"] = list(self.options)
        else:
            p["placements"] = list(self.placements)
        if self.from_deck_reveal:
            p["from_deck_reveal"] = True
        if self.kind:
            p["kind"] = self.kind
        return p


def legal_pending(state: GameState) -> list:
    """Actions offered while a choice is pending."""
    p = state.pending
    if p["mode"] == "choice":
        acts = [ChoiceAction(o) for o in p["options"]]
    else:  # "place"
        acts = [PlaceAction(pl["card_id"], tuple(pl["target"])) for pl in p["placements"]]
    if p["optional"]:
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

REQUIRE_SOURCE = False   # tests turn it on: every choice but the mulligan must name the card asking (`by_card`)


def resolve(state: GameState) -> None:
    """Drain the effect stack until empty, a choice is needed, or the game is won."""
    while state.pending is None and state.result is None and state.effect_stack:
        step = state.effect_stack.pop()
        n, was = len(state.effect_stack), (state.cause, state.cause_iid)
        state.cause, state.cause_iid = step.get("by_card"), step.get("by_iid")
        try:
            req = OPS[step["op"]](state, step)
        finally:
            state.cause, state.cause_iid = was
        if step.get("by_card"):       # what a step sets off is that card's doing too (that very unit's, when the card matches)
            for new in state.effect_stack[n:]:
                new.setdefault("by_card", step["by_card"])
                if "by_iid" in step and new["by_card"] == step["by_card"]:
                    new.setdefault("by_iid", step["by_iid"])
        if req is not None:           # op needs a choice: put the step back and pause
            if REQUIRE_SOURCE and step["op"] != "mulligan" and not step.get("by_card"):
                raise AssertionError(f"a {step['op']!r} choice with no source card")
            state.effect_stack.append(step)
            state.pending = req.to_pending()
            return


# ================================================================== mulligan

def _op_mulligan(state, step):
    """Gwent-style blacklist mulligan (overview.md §4.4): each returned card is replaced at once by
    the top deck card that is no copy of anything returned so far, up to the config's mulligan_cap returns (the opening hand's size)
    (a replacement may itself be returned); SKIP keeps the rest. Returned cards are shuffled back
    at the end. Raw draws and a raw shuffle: no on-draw or on-shuffle triggers, like the deal."""
    player, returned = step["player"], step["returned"]
    deck, hand = state.decks[player], state.hands[player]
    done = False
    if "choice" in step:
        choice = step.pop("choice")
        if choice == SKIP:
            done = True
        else:
            inst = next((u for u in hand if u.iid == choice), None)
            if inst is not None and _mulligan_replacement(deck, returned + [inst.card_id]) is not None:
                hand.remove(inst)
                returned.append(inst.card_id)
                i = _mulligan_replacement(deck, returned)
                new = UnitInstance(deck.pop(i), player, state.new_iid())
                hand.append(new)
                state.emit("mulligan", player=player, returned=inst.iid, drawn=[new.iid, new.card_id])   # hidden from the other
    if not done and hand and len(returned) < state.config.mulligan_cap(player, state.first_player) and _mulligan_replacement(deck, returned) is not None:
        return PendingRequest("choice", player, optional=True, kind="mulligan", options=[u.iid for u in hand])
    if returned:                      # a kept hand leaves the deck order (and the RNG) untouched
        deck.extend(returned)
        state.rng.shuffle(deck)
    if not any(st.get("op") == "mulligan" for st in state.effect_stack):   # both done: the first turn begins
        for p in ("A", "B"):
            state.ensure_mates(p)         # the opening hands are final: a legendary Eagle brings its mate now
        state.emit("turn_start", player=state.current, turn=state.turn_counter)
    return None


def _mulligan_replacement(deck, blacklist):
    """Index of the topmost deck card (the end) that is no copy of a blacklisted card, or None."""
    banned = set(blacklist)
    return next((i for i in range(len(deck) - 1, -1, -1) if deck[i] not in banned), None)


# ============================================================ placement + events

def do_placement(state: GameState, player: str, card_id: str, target) -> None:
    """Place an occupant from hand. Handles food cost, HQ capture, and crossroad landing."""
    unit = playable_copy(state, player, card_id)
    if unit is None:
        raise EngineError(f"{player} has no playable {card_id!r} in hand")
    strength = placement_strength(state, unit)   # as it is played (a den capture shows it)
    state.hands[player].remove(unit)
    cost = state.cards[card_id].food_cost          # "Costs X food" (decision F): paid on placement
    if cost:
        state.food[player] -= cost
        state.emit("pay", player=player, n=cost, card=card_id)
    state.units_placed_this_turn += 1
    kind, where = target
    if kind == "hq":
        state.emit("capture", player=player, iid=unit.iid, card=card_id, den=where, str=strength)
        state.result = Result(player, "hq_capture")
        return
    _land_unit(state, player, unit, where, from_hand=True)


def playable_copy(state: GameState, player: str, card_id: str) -> Optional[UnitInstance]:
    """The hand instance a PlaceAction for `card_id` plays: the highest-counter copy that is not
    Skunk-locked (F4), first in hand order on ties. PlaceAction is keyed only by card id, so move
    generation and execution must both pick through this one predicate."""
    best = None
    for u in state.hands[player]:
        if u.card_id != card_id or u.locked_until_turn > state.turn_counter:
            continue
        if best is None or u.strength_counter > best.strength_counter:
            best = u
    return best


def _take_from_hand(state: GameState, player: str, card_id: str) -> UnitInstance:
    """Remove and return a hand instance of `card_id`, preferring the highest-counter copy."""
    candidates = [u for u in state.hands[player] if u.card_id == card_id]
    unit = max(candidates, key=lambda u: u.strength_counter)
    state.hands[player].remove(unit)
    return unit


def _land_unit(state: GameState, player: str, unit: UnitInstance, cr: str, *, from_hand: bool,
               roar: bool = True) -> None:
    """The same hand instance lands on the board, carrying its strength counter. `roar=False` is a placement by an
    effect that doesn't set off the animal's Roar (the Sardines and Lemmings an effect fills in); every reaction to the
    landing still happens."""
    covered = state.top_unit(cr)
    is_apex = "Apex Predator" in state.cards[unit.card_id].keywords
    onto_enemy = covered is not None and covered.owner != player

    unit.placed_on_turn = state.turn_counter
    state.stamp_played(unit)
    state.board.setdefault(cr, []).append(unit)
    state.emit("place", player=player, iid=unit.iid, card=unit.card_id, cr=cr, from_hand=from_hand)
    if covered is not None:
        state.emit("cover", cr=cr, iid=covered.iid, card=covered.card_id, owner=covered.owner, by=unit.iid)

    # Apex Predator: it covers the occupant like any placement, and eats it afterwards
    # (Martin, 2026-09-29): the roar, then every reaction to the cover (Porcupine's Spikes,
    # Gale), then the eat. The stack is LIFO, so the eat goes in first, at the bottom.
    if is_apex and covered is not None:
        state.effect_stack.append({"op": "apex_eat", "iid": unit.iid, "prey": covered.iid, "by_card": unit.card_id})

    # Reactive triggers resolve AFTER the placed unit's roar (decision 8). The stack
    # is LIFO, so push reactive first (lower) and the roar last (on top).
    _push_reactions(state, unit, cr, covered, onto_enemy)
    if onto_enemy:
        _fire_cover_event(state, unit, covered)
        _push_flee(state, covered, unit, cr)
    _fire_play_event(state, unit)        # Queen Honoria: gain food when you play a Colony unit
    if roar:
        times = 1
        if (state.roar_twice.get(unit.owner) == state.turn_counter and unit.card_id != "macaw"
                and (_hook(state, unit.card_id, "on_place") or (onto_enemy and _hook(state, unit.card_id, "on_place_onto_enemy")))):
            del state.roar_twice[unit.owner]            # the Macaw: this Roar happens twice, then the double is spent
            times = 2
        for _ in range(times):
            _push_hook(state, unit, cr, "on_place")
            if onto_enemy:
                _push_hook(state, unit, cr, "on_place_onto_enemy")


def _fire_cover_event(state, coverer, covered) -> None:
    """King Theron: when one of your Cats covers an enemy unit, remove that enemy (now buried).
    Decision G: House Cat/extra-placement chains can cover multiple enemies in one turn -
    `cap_king_theron` (off by default) limits Theron to one free removal per turn."""
    hook = _hook(state, coverer.card_id, "on_cover_enemy")   # "Whenever this covers an enemy" (African Wild Dog)
    if hook:
        hook(state, coverer, covered)
    if "Cat" not in state.cards[coverer.card_id].tags:
        return
    for top in statics.active_tops(state, coverer.owner, "king_theron"):
        if not _capped(state, "cap_king_theron", top):
            state.effect_stack.append(
                remove_iid_step(covered.iid, by_player=coverer.owner, by_effect=True, source_iid=None, by_card=coverer.card_id))
        return


def _push_flee(state, covered, coverer, cr) -> None:
    """Flee (keywords.md): when an enemy covers this, it returns to its owner's hand. Pushed after every other reaction
    to the cover, so it resolves first: the animal runs before anything else can eat or remove it (an Apex Predator
    finds nothing left to eat)."""
    if coverer.owner != covered.owner and statics.has_keyword(state, covered, "Flee", cr):
        state.effect_stack.append({"op": "flee", "iid": covered.iid, "coverer": coverer.iid, "by_card": covered.card_id,
                                   "by_iid": covered.iid})


def _op_flee(state, step):
    cr, unit = _find_unit(state, step["iid"])
    if unit is None:
        return None
    _bounce(state, cr, unit)
    hook = _hook(state, unit.card_id, "on_flee")     # Zebra: "When this flees, ..."
    if hook:
        hook(state, unit, step["coverer"])
    return None


def _fire_play_event(state, played) -> None:
    """Fire ON_FRIENDLY_PLAY reactors for a unit its controller just played or spawned
    (Queen Honoria's food, Dhole's on-enter buff). The played unit itself is skipped."""
    for st in state.board.values():
        top = st[-1] if st else None
        if not (top and top.owner == played.owner and top.iid != played.iid):
            continue
        hook = _hook(state, top.card_id, "on_friendly_play")
        if hook is not None:
            hook(state, top, played)


def _push_reactions(state, unit, cr, covered, onto_enemy) -> None:
    # Traps reacting to a unit arriving adjacent: placed, or roamed in (keywords.md, Roam). An enemy's (Hippopotamus,
    # Meerkat, Golden Orb-Weaver) or anyone's (City Spider). A trap that cares which it was can tell from the arriving
    # unit's `roamed_{iid}` turn flag.
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if top is None:
            continue
        if top.owner != unit.owner:
            hook = _hook(state, top.card_id, "on_enemy_placed_adjacent")
            if hook:
                hook(state, top, unit, cr)
        hook = _hook(state, top.card_id, "on_animal_placed_adjacent")
        if hook:
            hook(state, top, unit, cr)
    if covered is not None:
        keywords = statics.unit_keywords(state, covered, cr)
        if "Spikes" in keywords:   # the keyword is the behaviour: any card with Spikes has it
            _spikes_covered(state, covered, unit, cr)
        if "Poison" in keywords:
            _poison_covered(state, covered, unit)
        hook = _hook(state, covered.card_id, "on_covered")
        if hook:
            hook(state, covered, unit, cr)
        # "When an ally is covered" / "Whenever your opponent covers an allied Fish": the covered unit's side watches.
        for st in list(state.board.values()):
            top = st[-1] if st else None
            if top and top.owner == covered.owner and top is not covered:
                hook = _hook(state, top.card_id, "on_ally_covered")
                if hook:
                    hook(state, top, covered, unit, cr)


def _push_hook(state, unit, cr, hook_name) -> None:
    hook = _hook(state, unit.card_id, hook_name)
    if hook:
        hook(state, unit, cr)


def _hook(state, card_id, hook_name) -> Optional[Callable]:
    """A card's hook, wrapped so every step it pushes carries the card as its source (`by_card`): the player is always
    told which card is asking, never left to a guess."""
    fn = EFFECTS.get(card_id, {}).get(hook_name)
    if fn is None:
        return None
    def stamped(state, unit, *args, **kw):   # every hook gets its own card's unit first
        if state.inked and statics.inked(state, unit):
            return None                       # an inked animal has no effects until the inking player's next turn
        n, was = len(state.effect_stack), (state.cause, state.cause_iid)
        state.cause, state.cause_iid = card_id, unit.iid   # what it does now is this unit's doing (events say so)
        try:
            out = fn(state, unit, *args, **kw)
        finally:
            state.cause, state.cause_iid = was
        for step in state.effect_stack[n:]:
            step.setdefault("by_card", card_id)
            if step["by_card"] == card_id:
                step.setdefault("by_iid", unit.iid)
        return out
    return stamped


# ================================================================= removal & food

def _dispose(state: GameState, unit: UnitInstance) -> bool:
    """Send a board unit to the Remove Pile. Returns True: it entered the pile (a genuine *remove*). (A "return
    instead" card, which never reached the pile, would return False here; none is in the pool now.)"""
    state.pile_add(unit.card_id, unit.owner)
    return True


def _remove_specific(state, cr, unit, *, by_player, by_effect=True, by_card=None) -> bool:
    """Remove a specific unit from a stack (mid-stack ok). Fires removal reactions. `by_card`
    is the card id of the effect's source unit, if any (for Queen Adira's "a Cat removes")."""
    stack = state.board.get(cr)
    if not stack or unit not in stack:
        return False
    # Only the physics gate lives here (Armor blocks any effect-removal, whoever chose
    # it). Stealth is a *choice* restriction, enforced where enemy option lists are built,
    # never at resolution - so mass/random/automatic removals
    # (Pestis, Rhino/Brutus, Grizzly, Hippo, King Theron, Pufferfish) hit Stealth units.
    if by_effect and not statics.can_be_removed(state, unit):
        return False
    was_top = stack[-1] is unit
    pos = stack.index(unit)
    state.emit("remove", cr=cr, iid=unit.iid, card=unit.card_id, owner=unit.owner, by=by_player)
    stack.remove(unit)
    # "if an ally was removed this turn" (Piranha, Vulture), "for each of your animals removed this turn" (Hyena),
    # "if an animal was removed this turn" (Great White Shark): board removals, counted per owner.
    state.turn_flags[f"lost_{unit.owner}"] = state.turn_flags.get(f"lost_{unit.owner}", 0) + 1
    state.turn_flags["removed_any"] = True
    # A unit uncovered by this very removal was buried when it happened, so it doesn't react to it.
    uncovered = stack[-1] if was_top and stack else None
    if not stack:
        del state.board[cr]
    entered_pile = _dispose(state, unit)
    if entered_pile:                        # the remove trigger fires first (F9), then...
        _fire_remove_event(state, unit.card_id, unit.owner, cr, by_player, by_card, uncovered)
    _fire_on_remove(state, unit, cr, pos)   # ...the unit's own Deathrattle (e.g. Ember relocates)
    return True


def remove_top(state, cr, *, by_player, by_effect=True, by_card=None) -> bool:
    top = state.top_unit(cr)
    if top is None:
        return False
    return _remove_specific(state, cr, top, by_player=by_player, by_effect=by_effect, by_card=by_card)


def _op_apex_eat(state, step):
    """An Apex eats what it covered, if both are still there, the prey is right beneath it,
    and it can be eaten (not Armor, which _remove_specific refuses). Stealth doesn't save it: a predator eats what it
    lands on, nobody chooses a target (Martin, 2026-10-01)."""
    cr, apex = _find_unit(state, step["iid"])
    if apex is None:
        return None
    stack = state.board[cr]
    i = stack.index(apex)
    prey = stack[i - 1] if i > 0 else None
    if prey is not None and prey.iid == step["prey"]:
        _remove_specific(state, cr, prey, by_player=apex.owner, by_card=apex.card_id)
    return None


def _find_unit(state, iid):
    for cr, stack in state.board.items():
        for u in stack:
            if u.iid == iid:
                return cr, u
    return None, None


def _fire_on_remove(state, unit, cr, pos) -> None:
    """A unit leaving the board: its own "When this is removed" effect, told where it stood (`cr`, and `pos`, its place
    in the stack from the bottom) so it can leave something there (Earthworm)."""
    hook = _hook(state, unit.card_id, "on_remove")
    if hook:
        hook(state, unit, cr, pos)


def _food_gained_this_turn(state: GameState, player: str) -> int:
    """Food `player` has gained since the start of their current turn (turn_flags reset each
    turn end). Powers the food_otk signature cards: Scrooge / Hamster / Muskrat / Groundhog."""
    return state.turn_flags.get(f"food_gained_{player}", 0)


def _fed_this_turn(state: GameState, player: str) -> bool:
    return _food_gained_this_turn(state, player) >= state.config.fed_threshold


def _lost_this_turn(state: GameState, player: str) -> int:
    """How many of `player`'s animals have been removed from the board this turn."""
    return state.turn_flags.get(f"lost_{player}", 0)


def lose_food(state: GameState, player: str, amount: int, *, card: Optional[str] = None) -> None:
    """`player` loses food (the legendary Squirrel's stake, a Hungry animal eating): never below 0."""
    amount = min(amount, state.food[player])
    if amount > 0:
        state.food[player] -= amount
        state.emit("pay", player=player, n=amount, **({"card": card} if card else {}))


def gain_food(state: GameState, player: str, amount: int, *, rider: bool = True, income: bool = False) -> None:
    if amount <= 0:
        return
    state.food[player] += amount
    state.emit("food", player=player, n=amount, **({"income": True} if income else {}))
    state.turn_flags[f"food_gained_{player}"] = _food_gained_this_turn(state, player) + amount
    if state.food[player] >= state.game_map.win_food:
        state.result = Result(player, "food")
        return
    # Falstaff: whenever you gain food, gain N more (once per gain event; never recursively).
    if rider:
        falstaffs = len(statics.active_tops(state, player, "falstaff"))
        if falstaffs and not (state.config.cap_falstaff and state.turn_flags.get(f"falstaff_{player}")):
            if state.config.cap_falstaff:
                state.turn_flags[f"falstaff_{player}"] = True
            gain_food(state, player, falstaffs * state.config.falstaff_food_rider, rider=False)


# ============================================ draw / shuffle / remove event engine
#
# Discrete events (decision F2/F9): one event per card drawn, shuffled-into-deck, or
# removed. Board-top units react via on_draw_event / on_shuffle_event / on_remove_event
# hooks (Eon/Vulture); Rattlesnake's shuffle growth applies in every zone; a *drawn card* may also react to itself via on_draw (Black Swan). Reactors resolve
# immediately, so no extra stack steps and no re-entrancy in this stage. state.py stays
# free of effect imports - these wrappers sit above the card-movement primitives.

def _fire_event(state, hook_name: str, event: dict, skip=None) -> None:
    """Dispatch one event to every board-top unit that reacts to it (deterministic order).
    `skip` is a unit that must not react (one the event itself uncovered)."""
    for cr in sorted(state.board):
        top = state.board[cr][-1]
        if top is skip:
            continue
        hook = _hook(state, top.card_id, hook_name)
        if hook:
            hook(state, top, cr, event)
    if hook_name == "on_shuffle_event":
        _rattlesnake_shuffle_event(state, event)


def _fire_remove_event(state, card_id: str, owner: str, cr, by_player=None, by_card=None, uncovered=None) -> None:
    event = {"card_id": card_id, "owner": owner, "cr": cr, "tags": state.cards[card_id].tags,
             "by_player": by_player, "by_card": by_card}
    _fire_event(state, "on_remove_event", event, skip=uncovered)


def _fire_draw(state, drawn) -> None:
    if drawn:
        state.emit("draw", player=drawn[0].owner, cards=[[u.iid, u.card_id] for u in drawn])
        # Over the hand limit, the newest cards burn: a remove from hand, and no ON_DRAW.
        over = len(state.hands[drawn[0].owner]) - state.config.hand_limit
        if over > 0:
            burned, drawn = drawn[-over:], drawn[:-over]
            for inst in burned:
                remove_from_hand(state, inst.owner, inst)
    for inst in drawn:
        _fire_event(state, "on_draw_event", {"card_id": inst.card_id, "player": inst.owner})
        hook = _hook(state, inst.card_id, "on_draw")     # the drawn card reacting to itself
        if hook:
            hook(state, inst)
    if drawn:
        state.ensure_mates(drawn[0].owner)               # a legendary Eagle entering the hand brings its mate


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


def shuffle_back(state: GameState, player: str, card_ids: list, *, by: Optional[str] = None) -> None:
    """Put `card_ids` into `player`'s deck, shuffle, and fire one ON_SHUFFLE event per card (F2). `by` is the player
    doing the shuffling when it isn't the deck's owner (the Cuckoo shuffles its eggs into the opponent's deck): the
    events are theirs ("Whenever you shuffle a card")."""
    deck = state.decks[player]
    deck.extend(card_ids)
    state.rng.shuffle(deck)
    for cid in card_ids:
        _fire_event(state, "on_shuffle_event", {"card_id": cid, "player": by or player})


def remove_from_hand(state: GameState, player: str, inst: UnitInstance) -> None:
    """Remove a card from hand to the Remove Pile: a *remove* (fires the remove event) but
    NOT a Deathrattle (it never was on the board). Used by Black Swan, Rat, discards."""
    state.hands[player].remove(inst)
    state.pile_add(inst.card_id, inst.owner)
    state.emit("remove", zone="hand", iid=inst.iid, card=inst.card_id, owner=inst.owner)
    _fire_remove_event(state, inst.card_id, inst.owner, None)


def _matches(card, spec: str) -> bool:
    """A serializable filter for filtered draws: 'tag:Bird', 'rarity:legendary',
    """
    kind, _, val = spec.partition(":")
    if kind == "tag":
        return val in card.tags
    if kind == "rarity":
        return card.rarity == val
    if kind == "keyword":                 # Badger: "draw an animal with Roam"
        return val in card.keywords
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

def legal_placements(state: GameState, player: str, allowed_cards: Optional[set] = None, *,
                     titan_ok: bool = False) -> list:
    """All legal placements for `player` (used by rules.legal_actions and play_extra).

    `allowed_cards` (a set of card ids) restricts which hand cards may be played.
    `titan_ok`: a Titan may be played (it costs two actions: the turn has two left; a free placement never can).
    Deterministic order (sorted) for reproducible replay.
    """
    gm = state.game_map
    occ = state.connected_occupied(player)
    enemy = other_player(player)
    enemy_hq = any(cr in occ for cr in gm.hq_front(enemy))  # HQ capture: connection only (not Flight)

    # Connection legality depends only on (player, occ), never on the card, so the set of
    # connection-legal crossroads is identical for every non-Flight/non-extra card. Compute it
    # once instead of calling is_connected per (card x crossroad); Flight/extra bypasses layer
    # on top per card below. (Byte-identical: `cr in connectable` == is_connected(player, cr).)
    sorted_crossroads = sorted(gm.crossroads)
    connectable = {cr for cr in sorted_crossroads if state.is_connected(player, cr, occ)}

    # One placement per distinct hand card id, using the copy that would actually be played.
    best: dict[str, "UnitInstance"] = {}
    for card_id in {u.card_id for u in state.hands[player]}:
        if allowed_cards is not None and card_id not in allowed_cards:
            continue
        placer = playable_copy(state, player, card_id)
        if placer is not None:
            best[card_id] = placer

    out = []
    reach_sets: dict[int, set] = {}                   # Reach N's crossroads, once per N
    for card_id in sorted(best):
        placer = best[card_id]
        card = state.cards[card_id]
        if card.food_cost > state.food[player]:
            continue                                  # "Costs X food": only if affordable (dec. F)
        if "Titan" in card.keywords and not titan_ok:
            continue                                  # Titan: two actions, never a free placement
        is_apex = "Apex Predator" in card.keywords
        flight = statics.ignores_connection(state, card_id)
        extra = statics.extra_placement_crossroads(state, card_id, player)
        reach = statics.reach_of(state, card_id)
        if reach:
            if reach not in reach_sets:
                reach_sets[reach] = statics.reach_crossroads(state, player, reach, occ)
            extra = extra | reach_sets[reach]
        for cr in sorted_crossroads:
            if not (flight or cr in connectable or cr in extra):
                continue
            top = state.top_unit(cr)
            if is_apex:
                if top is not None and _apex_can_land(state, placer, top):
                    out.append(PlaceAction(card_id, ("cr", cr)))   # must land on an occupant
            elif top is None or top.owner == player:
                out.append(PlaceAction(card_id, ("cr", cr)))
            elif statics.can_cover(state, placer, top):
                out.append(PlaceAction(card_id, ("cr", cr)))
        # Apex Predators can never capture an HQ (decision D).
        if enemy_hq and not is_apex:
            out.append(PlaceAction(card_id, ("hq", enemy)))
    return out


def _apex_can_land(state: GameState, placer: UnitInstance, top: UnitInstance) -> bool:
    """Apex Predator landing rules (decision D + keyword-review C1): it may land wherever it
    could legally cover - free on your own occupants, `statics.can_cover` vs an enemy, so
    the covering statics apply to apexes exactly as to normal placements: Snow Leopard lets
    an apex Cat land at equal strength. If the occupant can be eaten it is; if not (Armor) it is simply
    covered (see _land_unit)."""
    if top.owner == placer.owner:
        return True
    return statics.can_cover(state, placer, top)


# ======================================================================== Roam
#
# Roam (keywords.md): as an action, move an animal you own that is connected to your den to an adjacent crossroad under
# the placement rules, at most once per animal per turn. Moving isn't placing: no Roar, no "when you play" reactions, no
# new place in the play order. Arriving is: adjacency traps, covering reactions (Spikes, Poison, Gale, King Theron) and
# an Apex Predator's eat all happen as on a placement.
#
# Hooks for the cards that build on it (none exist yet):
#   - EFFECTS[card]["on_roam"](state, unit, cr, event): "whenever this roams…", resolves first, where a Roar would;
#   - EFFECTS[card]["on_friendly_roam"](state, watcher, roamer, event): "whenever one of your animals roams…" (any of
#     the player's other top units; event["onto_enemy"] tells a cover);
#   - statics.can_roam / statics.roam_covers_equal: who roams, and who may roam onto an equal enemy;
#   - free roams: statics.free_roams(state, player) per turn, plus turn_flags["free_roams_<player>"] granted by the
#     `grant_free_roam` op; a free roam is spent before an action.
# The event dict: {"player", "iid", "from", "to" (None for a den), "covered" (iid or None), "onto_enemy"}.
# turn_flags: "roamed_<iid>" (this animal has roamed this turn), "roams_<player>" (how many this turn).

def legal_roams(state: GameState, player: str, *, free_only: bool = False) -> list:
    """Every legal Roam for `player`, in a deterministic order. `free_only`: only roams a free roam pays for (the turn's
    actions are spent)."""
    if not any(st and st[-1].owner == player and statics.can_roam(state, st[-1]) for st in state.board.values()):
        return []                                     # the usual case, and the search's hot path: skip the BFS
    gm = state.game_map
    occ = state.connected_occupied(player)
    enemy = other_player(player)
    enemy_front = gm.hq_front(enemy)
    out = []
    for cr in sorted(occ):
        unit = state.board[cr][-1]
        if not statics.can_roam(state, unit) or state.turn_flags.get(f"roamed_{unit.iid}"):
            continue
        if free_only and not free_roams_left(state, player, unit):
            continue
        out.extend(RoamAction(cr, t) for t in roam_targets(state, unit, cr, enemy_front=enemy_front))
    return out


def roam_targets(state: GameState, unit, cr: str, *, enemy_front=None) -> list:
    """Where `unit` (on `cr`) may roam to: ("cr", crossroad) targets, and ("hq", enemy) from the enemy's den front."""
    player = unit.owner
    enemy = other_player(player)
    if enemy_front is None:
        enemy_front = state.game_map.hq_front(enemy)
    is_apex = statics.has_keyword(state, unit, "Apex Predator", cr)
    out = []
    for nb in state.game_map.neighbors(cr):
        top = state.top_unit(nb)
        if top is None:
            ok = not is_apex                      # an Apex roams only onto an animal
        elif top.owner == player:
            ok = True
        else:
            ok = statics.can_cover(state, unit, top, roaming=True)
        if ok:
            out.append(("cr", nb))
    if cr in enemy_front and not is_apex:         # an Apex never takes a den
        out.append(("hq", enemy))
    return out


def free_roams_left(state: GameState, player: str, unit=None) -> int:
    """Free roams `player` still holds this turn; with `unit`, those that animal may use (Clarion's are for Canines)."""
    granted = statics.free_roams(state, player, unit) + state.turn_flags.get(f"free_roams_{player}", 0)
    return max(0, granted - state.turn_flags.get(f"free_roams_used_{player}", 0))


def pay_for_roam(state: GameState, player: str, unit=None) -> None:
    """A roam spends a free roam if the player holds one this animal may use, else one of the turn's actions."""
    if free_roams_left(state, player, unit):
        state.turn_flags[f"free_roams_used_{player}"] = state.turn_flags.get(f"free_roams_used_{player}", 0) + 1
    else:
        state.actions_taken_this_turn += 1


def do_roam(state: GameState, player: str, origin: str, target) -> None:
    """Move the top animal of `origin` to `target`. Leaving uncovers whatever was beneath it."""
    stack = state.board.get(origin)
    if not stack or stack[-1].owner != player:
        raise EngineError(f"{player} has no animal on {origin!r} to roam")
    unit = stack[-1]
    state.turn_flags[f"roamed_{unit.iid}"] = True
    state.turn_flags[f"roams_{player}"] = state.turn_flags.get(f"roams_{player}", 0) + 1
    kind, where = target
    if kind == "hq":                                  # the game ends as it steps onto the den
        state.emit("roam", player=player, iid=unit.iid, card=unit.card_id, cr=origin, to=None, den=where)
        state.emit("capture", player=player, iid=unit.iid, card=unit.card_id, den=where,
                   str=effective_strength(state, unit), roam=True)
        state.result = Result(player, "hq_capture")
        return
    stack.pop()
    if not stack:
        del state.board[origin]
    state.emit("roam", player=player, iid=unit.iid, card=unit.card_id, cr=origin, to=where)
    covered = state.top_unit(where)
    onto_enemy = covered is not None and covered.owner != player
    state.board.setdefault(where, []).append(unit)
    if covered is not None:
        state.emit("cover", cr=where, iid=covered.iid, card=covered.card_id, owner=covered.owner, by=unit.iid)
    if statics.has_keyword(state, unit, "Apex Predator", where) and covered is not None:
        state.effect_stack.append({"op": "apex_eat", "iid": unit.iid, "prey": covered.iid, "by_card": unit.card_id})
    _push_reactions(state, unit, where, covered, onto_enemy)
    if onto_enemy:
        _fire_cover_event(state, unit, covered)
        _push_flee(state, covered, unit, where)
    event = {"player": player, "iid": unit.iid, "from": origin, "to": where,
             "covered": covered.iid if covered is not None else None, "onto_enemy": onto_enemy}
    for st in list(state.board.values()):
        top = st[-1] if st else None
        if top and top.owner == player and top.iid != unit.iid:
            hook = _hook(state, top.card_id, "on_friendly_roam")
            if hook:
                hook(state, top, unit, event)
    hook = _hook(state, unit.card_id, "on_roam")
    if hook:
        hook(state, unit, where, event)


def _op_grant_free_roam(state, step):
    """A free roam for `player` this turn (the turn it resolves in): spent before an action."""
    key = f"free_roams_{step['player']}"
    state.turn_flags[key] = state.turn_flags.get(key, 0) + step["n"]
    return None


# ============================================================= delayed scheduler

def schedule(state: GameState, unit, owner_turn_delay: int, step: dict, *, while_buried: bool) -> None:
    """Queue `step` to fire after `owner_turn_delay` more of `unit`'s owner's turns.

    The timer belongs to the **unit**, not the board (rules `overview.md` §9.1): it advances only
    while `unit` is the top of its crossroad, and is cancelled outright if `unit` leaves the board.
    A bounced unit re-enters play as a fresh instance with a new iid, so replaying it starts a new
    timer rather than resuming this one - "bounce resets".
    """
    step.setdefault("by_card", unit.card_id)   # a delayed effect still names its card when it fires
    state.scheduled.append({"iid": unit.iid, "owner": unit.owner, "while_buried": while_buried,   # keep ticking under a cover?
                            "remaining": owner_turn_delay, "step": step})


def start_of_turn(state: GameState, player: str) -> None:
    """Advance `player`'s pending timers, fire those that come due, then run on_start_of_turn
    hooks (the caller resolves the stack).

    Per `overview.md` §9.1 a timer ticks only for a unit that is currently the **top** of its
    crossroad: a buried unit's timer is suspended (not lost) and resumes if it becomes visible
    again; a unit that has left the board has its timer cancelled.
    """
    on_board = {u.iid for stack in state.board.values() for u in stack}
    tops = {stack[-1].iid for stack in state.board.values() if stack}
    fired, keep = [], []
    for s in state.scheduled:
        if s["owner"] != player:
            keep.append(s)
        elif s["iid"] not in on_board:
            continue                       # removed: cancelled outright (§9.1)
        elif s["iid"] not in tops and not s["while_buried"]:
            keep.append(s)                 # buried: suspended, does not tick (§9.1)
        else:
            s["remaining"] -= 1
            (fired if s["remaining"] <= 0 else keep).append(s)
    state.scheduled = keep
    for s in reversed(fired):  # earliest-scheduled ends on top of the stack -> resolves first
        state.effect_stack.append(s["step"])
    _push_timed_hooks(state, player, "on_start_of_turn")   # Dawn, above the timers: it resolves first


def end_of_turn(state: GameState, player: str) -> None:
    """Queue `player`'s Dusk effects (on_end_of_turn hooks); the caller resolves them.

    End-of-turn effects are choice-free (auto/deterministic) so the turn can still advance
    without a pending decision - see rules._end_turn.
    """
    _push_timed_hooks(state, player, "on_end_of_turn")


def _push_timed_hooks(state: GameState, player: str, hook_name: str) -> None:
    """Dawn and Dusk: several of one player's resolve in the order their animals were played (keywords.md), each in
    full before the next begins. Each is a `timed_hook` step, earliest-played on top of the stack, and re-checks its
    animal when its turn comes: one an earlier effect removed or buried does nothing (overview.md §9, a queued reaction
    fizzles when its unit is gone)."""
    due = []
    for cr, stack in state.board.items():
        top = stack[-1] if stack else None
        if not top or top.owner != player:
            continue
        if hook_name in EFFECTS.get(top.card_id, {}):
            due.append((top.play_seq, cr, top.iid, top.card_id, hook_name))
        # Hungry N is a Dawn effect too ("food is made at the end of your turn and eaten at the start of the next").
        if hook_name == "on_start_of_turn" and "Hungry" in state.cards[top.card_id].keywords:
            due.append((top.play_seq, cr, top.iid, top.card_id, "hungry"))
    # The legendary Sloth: "Your Dusk effects happen twice." Each one runs twice in a row.
    times = 2 if hook_name == "on_end_of_turn" and statics.active_tops(state, player, "aristocrats_legend_sloth") else 1
    for _, _, iid, card_id, hook in sorted(due, reverse=True):
        for _ in range(times):
            state.effect_stack.append({"op": "timed_hook", "hook": hook, "iid": iid, "player": player,
                                       "by_card": card_id, "by_iid": iid})


def _op_timed_hook(state, step):
    cr, unit = _find_unit(state, step["iid"])
    if unit is None or state.board[cr][-1] is not unit or unit.owner != step["player"]:
        return None
    if step["hook"] == "hungry":
        _eat(state, unit, cr)
        return None
    hook = _hook(state, unit.card_id, step["hook"])
    if hook:
        hook(state, unit, cr)
    return None


def _eat(state, unit, cr) -> None:
    """Hungry N (keywords.md): at the start of your turn the animal eats N of your food; if you can't feed it, it gets -N
    strength, for good. An adjacent legendary Oxpecker feeds it ("Your adjacent Hungry animals don't need to eat"), and
    an inked animal isn't Hungry until the ink wears off."""
    if not statics.has_keyword(state, unit, "Hungry", cr):
        return
    n = state.cards[unit.card_id].hungry
    if any((top := state.top_unit(nb)) and top.owner == unit.owner and top.card_id == "giants_legend_oxpecker"
           and statics.active(state, top) for nb in state.game_map.neighbors(cr)):
        return
    prev, state.cause, state.cause_iid = (state.cause, state.cause_iid), unit.card_id, unit.iid
    try:
        if state.food[unit.owner] >= n:
            lose_food(state, unit.owner, n, card=unit.card_id)
        else:
            unit.strength_counter -= n
            state.emit("strength", iid=unit.iid, card=unit.card_id, owner=unit.owner, n=-n)
    finally:
        state.cause, state.cause_iid = prev


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
        return None  # egg already gone (removed before it hatched) - no payoff
    _remove_specific(state, cr, egg, by_player=egg.owner, by_effect=False)
    draw_filtered_random(state, egg.owner, step["n"], step["spec"])
    return None


def _op_raven_dig(state, step):
    player = step["player"]
    if "remaining" not in step:
        draw_cards(state, player, state.config.raven_draw)   # draw (fires ON_DRAW), then...
        step["remaining"] = min(state.config.raven_shuffle, len(state.hands[player]))
        step["shuffled"] = []

    if "choice" in step:
        iid = step.pop("choice")
        inst = next((u for u in state.hands[player] if u.iid == iid), None)
        if inst is not None:
            state.hands[player].remove(inst)
            state.emit("leave_hand", zone="hand", owner=player, iid=inst.iid, card=inst.card_id, to="deck")
            step["shuffled"].append(inst.card_id)
            step["remaining"] -= 1

    if step["remaining"] > 0 and state.hands[player]:
        options = [u.iid for u in state.hands[player]]
        if len(options) == 1:
            step["choice"] = options[0]
            return _op_raven_dig(state, step)
        return PendingRequest("choice", player, optional=False, options=options, from_deck_reveal=True)

    if step["shuffled"]:
        shuffle_back(state, player, step["shuffled"])
    return None


def _op_scout(state, step):
    """Scout: look at `scout_count` different cards of your deck, draw one (chosen), shuffle the rest back.
    Unfiltered (Owl) it looks from the top of the deck down; with a `spec` (a Bird, a legendary unit)
    at random matching cards. Either way it takes one copy of a card and passes over its other copies,
    so the choice is between that many different cards whenever the deck holds them (Martin, 2026-10-02:
    three Owls in the deck showed one card three times). Nothing matching: nothing happens."""
    player = step["player"]
    if "pulled" not in step:
        deck = state.decks[player]
        n = state.config.scout_count
        if step["spec"] is None:   # from the top of the deck (its end) down
            order = list(range(len(deck) - 1, -1, -1))
        else:                      # random cards of that kind
            order = [i for i, cid in enumerate(deck) if _matches(state.cards[cid], step["spec"])]
            state.rng.shuffle(order)
        picks, seen = [], set()
        for i in order:
            if len(picks) == n:
                break
            if deck[i] not in seen:
                seen.add(deck[i]); picks.append(i)
        pulled = [deck.pop(i) for i in sorted(picks, reverse=True)]
        if not pulled:
            return None
        step["pulled"] = pulled
        if len(set(pulled)) == 1:
            step["choice"] = pulled[0]
        else:
            return PendingRequest("choice", player, optional=False, options=sorted(set(pulled)),
                                  from_deck_reveal=True)
    pulled = list(step["pulled"])
    pulled.remove(step["choice"])
    inst = UnitInstance(step["choice"], player, state.new_iid())
    state.hands[player].append(inst)
    _fire_draw(state, [inst])
    shuffle_back(state, player, pulled)
    if step.get("grant") and inst in state.hands[player]:    # Tarsier: "Scout a Primate and give it +1 strength"
        _grant(state, [inst.iid], step["grant"])
    return None


def _op_bird_egg_hatch(state, step):
    cr, egg = _find_unit(state, step["iid"])
    if egg is None:
        return None  # removed before it hatched - no payoff
    _remove_specific(state, cr, egg, by_player=egg.owner, by_effect=False)
    state.effect_stack.append({"op": "scout", "player": egg.owner, "spec": "tag:Bird", "by_card": egg.card_id})
    return None


def _op_remove_choice(state, step):
    """Remove the top unit at a chosen crossroad among `options`."""
    options = step["options"]
    if not options:
        return None
    if "choice" not in step:   # asked even with one target: the player clicks what the Roar hits
        return PendingRequest("choice", step["chooser"], optional=step["optional"], options=options)
    chosen = step["choice"]
    if chosen == SKIP:
        return None
    remove_top(state, chosen, by_player=step["by_player"], by_card=step.get("by_card"))
    return None


def remove_iid_step(iid, *, by_player, by_effect, source_iid, by_card=None) -> dict:
    """A queued removal of one unit. Every fact is required: who removes it (the friendly/enemy-removal reactions read it),
    whether as an effect (Armor stops only those), and the unit whose leaving makes it fizzle (None: nothing)."""
    return {"op": "remove_iid", "iid": iid, "by_player": by_player, "by_effect": by_effect, "source_iid": source_iid,
            **({"by_card": by_card} if by_card else {})}


def remove_choice_step(chooser, options, *, by_card, optional) -> dict:
    """A removal the player aims (a Roar's target among `options`)."""
    return {"op": "remove_choice", "chooser": chooser, "by_player": chooser, "by_card": by_card, "options": options,
            "optional": optional}


def _op_remove_iid(state, step):
    # A reactive removal may name the unit that triggered it (`source_iid`). If that source
    # has since left the board - e.g. a fed Muskrat's roar removed the Hippo before the
    # Hippo's queued reaction resolves (decision: reactions fizzle when their source is gone) -
    # the removal fizzles rather than firing from a dead trigger.
    src = step["source_iid"]
    if src is not None and _find_unit(state, src)[1] is None:
        return None
    cr, unit = _find_unit(state, step["iid"])
    if unit is not None:
        _remove_specific(state, cr, unit, by_player=step["by_player"], by_effect=step["by_effect"], by_card=step.get("by_card"))
    return None


def _hand_allowed(state, player, filt: dict) -> set:
    """Hand card ids a play_extra may place, matching the
    filter `tags_all` / `tags_none` / `exclude_id` (decision F1 per-card constraints)."""
    allowed = set()
    for u in state.hands[player]:
        card = state.cards[u.card_id]
        if u.card_id == filt.get("exclude_id"):
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
    allowed = _hand_allowed(state, step["chooser"], step["filter"])   # {} means any card, and is said so
    placements = legal_placements(state, step["chooser"], allowed)
    near = step["filter"].get("adjacent_to")       # Naked Mole-Rat: "play another animal adjacent to this"
    if near is not None:
        enemy_den = state.game_map.hq_front(other_player(step["chooser"]))
        placements = [p for p in placements
                      if (p.target[0] == "cr" and state.game_map.adjacent(near, p.target[1]))
                      or (p.target[0] == "hq" and near in enemy_den)]
    if not placements:
        return None
    return PendingRequest("place", step["chooser"], optional=step["optional"],
                          placements=[{"card_id": p.card_id, "target": list(p.target)} for p in placements])


def _op_play_named(state, step):
    """Play a specific named card from hand OR deck (the Prince Leo / Princess Lea twins -
    the one F10 exception to "filtered draws are random"). Mandatory when it has a legal
    place (Martin, 2026-09-30); a twin fetched from the deck that can't be placed goes back."""
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
            back = _take_from_hand(state, player, cid)
            state.emit("leave_hand", zone="hand", owner=player, iid=back.iid, card=cid, to="deck")
            state.decks[player].append(cid)

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
    return PendingRequest("place", player, optional=False,
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
        state.emit("strength", iid=iid, card=inst.card_id, owner=inst.owner, n=amount)   # a stored gain
        if amount <= 0:
            continue
        if _crossroad_of(state, iid) is not None:
            _fire_on_gain_strength(state, inst)
        elif inst in state.hands[inst.owner]:
            _gain_in_hand(state, inst, amount, step["iids"])
    return None


def _gain_in_hand(state, inst, amount, granted) -> None:
    """A hand card gained strength: its mate shares it (the Eagles: "While this and its mate are in your hand, they
    share their strength", so a buff to either counts for both), and a card that reacts to growing in hand does
    (the legendary Butterfly evolves, the Caterpillar turns into a Butterfly)."""
    mate = state.cards[inst.card_id].mate
    if mate:
        partner = next((u for u in state.hands[inst.owner] if u.card_id == mate and u.iid not in granted), None)
        if partner is not None:
            partner.strength_counter += amount
            state.emit("strength", iid=partner.iid, card=partner.card_id, owner=partner.owner, n=amount)
    hook = _hook(state, inst.card_id, "on_gain_in_hand")
    if hook:
        hook(state, inst, amount)


def _op_grant_action(state, step):
    """Chinchilla: add extra top-level actions to `player` for the turn this fires on (it is
    scheduled to fire at the start of the owner's next turn). Read by rules._resolve_and_maybe_end_turn
    off turn_flags, which resets each turn end - so the grant lasts exactly that one turn."""
    key = f"bonus_actions_{step['player']}"
    state.turn_flags[key] = state.turn_flags.get(key, 0) + step["n"]
    return None


OPS: dict[str, Callable] = {
    "mulligan": _op_mulligan,
    "gain_food": _op_gain_food,
    "draw": _op_draw,
    "draw_filtered": _op_draw_filtered,
    "egg_hatch": _op_egg_hatch,
    "raven_dig": _op_raven_dig,
    "scout": _op_scout,
    "bird_egg_hatch": _op_bird_egg_hatch,
    "remove_choice": _op_remove_choice,
    "remove_iid": _op_remove_iid,
    "apex_eat": _op_apex_eat,
    "play_extra": _op_play_extra,
    "play_named": _op_play_named,
    "grant_strength": _op_grant_strength,
    "grant_action": _op_grant_action,
    "grant_free_roam": _op_grant_free_roam,
    "timed_hook": _op_timed_hook,
    "flee": _op_flee,
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
    """ON_GAIN_STRENGTH reactor for a board unit: at most once per turn per unit, which also guards against
    grant->gain->grant loops (decision E). No card in the pool reacts to it now; the seam stays."""
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
        if not statics.can_be_removed(state, top, nb):
            continue
        if chosen and not statics.can_be_chosen(state, top, unit.owner, nb):
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
    hides from its own controller; Armor blocks its own controller's removals too
    (decision A2: that's the keyword's cost)."""
    return [nb for nb in sorted(state.game_map.neighbors(cr))
            if (top := state.top_unit(nb)) and top.owner == unit.owner and statics.can_be_removed(state, top, nb)]


def _adjacent_tops(state, cr, owner=None):
    """(crossroad, top unit) for every occupied crossroad adjacent to `cr`, sorted; only `owner`'s when given."""
    return [(nb, top) for nb in sorted(state.game_map.neighbors(cr))
            if (top := state.top_unit(nb)) and (owner is None or top.owner == owner)]


def _control_tag_count(state, player, *tags) -> int:
    """How many crossroads `player` tops with a unit carrying all of `tags`."""
    return sum(
        1 for st in state.board.values()
        if st and st[-1].owner == player and all(t in state.cards[st[-1].card_id].tags for t in tags)
    )


def _friendly_adjacent_canine_iids(state, unit, cr):
    """Top units adjacent to `cr` that are friendly Canines (for the Canine buffers)."""
    return [top.iid for _, top in _adjacent_tops(state, cr, unit.owner) if "Canine" in state.cards[top.card_id].tags]


def _grant(state, iids, amount):
    if iids and amount:
        state.effect_stack.append({"op": "grant_strength", "iids": list(iids), "amount": amount})


def _push_gain(state, owner, amount):
    if amount:
        state.effect_stack.append({"op": "gain_food", "player": owner, "amount": amount})


def _push_draw(state, owner, n):
    if n:
        state.effect_stack.append({"op": "draw", "player": owner, "n": n})


def _push_remove_choice(state, owner, by_card, targets, *, optional=False):
    if targets:
        state.effect_stack.append(remove_choice_step(owner, targets, by_card=by_card, optional=optional))


def _push_choose(state, chooser, options, then, *, optional=False, **args):
    """A choice among `options` (crossroads, iids or card ids) whose pick `THEN[then]` acts on. Asked even with one
    option: the player clicks what the effect hits."""
    if options:
        state.effect_stack.append({"op": "choose", "chooser": chooser, "options": list(options), "then": then,
                                   "optional": optional, **args})


def _op_choose(state, step):
    if "choice" not in step:
        return PendingRequest("choice", step["chooser"], optional=step["optional"], options=step["options"],
                              from_deck_reveal=step.get("hidden", False))
    if step["choice"] == SKIP:
        return None
    THEN[step["then"]](state, step, step["choice"])
    return None


def _push_play_extra(state, owner, *, filter=None, optional=False):
    state.effect_stack.append(
        {"op": "play_extra", "chooser": owner, "filter": filter or {}, "optional": optional})


def _bounce(state, cr, top, *, lock_until=0):
    """Return a board unit to its owner's hand (not a removal: no Remove Pile, no triggers)."""
    state.emit("bounce", cr=cr, iid=top.iid, card=top.card_id, owner=top.owner)
    state.board[cr].remove(top)
    if not state.board[cr]:
        del state.board[cr]
    state.add_to_hand(top.owner, top.card_id).locked_until_turn = lock_until


def _spawn(state, owner, card_id, cr):
    """A token made on `cr` by an effect: it lands as a placement would (traps see it), with nothing to Roar."""
    _land_unit(state, owner, UnitInstance(card_id, owner, state.new_iid()), cr, from_hand=False)


def _empty_neighbors(state, cr):
    return [nb for nb in sorted(state.game_map.neighbors(cr)) if not state.board.get(nb)]


def _hand_iids(state, player, *, tag=None):
    return [u.iid for u in state.hands[player] if tag is None or tag in state.cards[u.card_id].tags]


def _transform(state, inst, card_id) -> None:
    """`inst` becomes another card, keeping its strength counter (the Butterfly's stages, the Caterpillar). In hand or on
    the board: it is that card from now on, wherever it goes."""
    was, inst.card_id = inst.card_id, card_id
    state.emit("transform", iid=inst.iid, owner=inst.owner, card=card_id, was=was)


# ============================================================== THEN: what a choice does

def _then_remove(state, step, cr):
    remove_top(state, cr, by_player=step["chooser"], by_card=step.get("by_card"))


def _then_set_strength(state, step, cr):
    """Serval: "set an adjacent enemy's strength to 1." Its counter takes the difference, so later buffs count on top."""
    top = state.top_unit(cr)
    if top is not None:
        delta = state.config.serval_set - effective_strength(state, top)
        top.strength_counter += delta
        state.emit("strength", iid=top.iid, card=top.card_id, owner=top.owner, n=delta)


def _then_drain(state, step, cr):
    """Viper, Mosquito: the chosen adjacent enemy gets -N strength, for good."""
    top = state.top_unit(cr)
    if top is not None:
        top.strength_counter -= step["amount"]
        state.emit("strength", iid=top.iid, card=top.card_id, owner=top.owner, n=-step["amount"])


def _then_grant(state, step, target):
    """Give +N to the chosen animal: on the board (a crossroad) or in hand (an iid)."""
    inst = state.top_unit(target) if isinstance(target, str) else _find_instance(state, target)
    if inst is not None:
        _grant(state, [inst.iid], step["amount"])


def _then_hand_grant(state, step, iid):
    """Baboon: give N different animals in your hand +1, one choice at a time."""
    step.setdefault("picked", []).append(iid)
    left = step["count"] - len(step["picked"])
    rest = [i for i in _hand_iids(state, step["chooser"]) if i not in step["picked"]]
    if left > 0 and rest:
        _push_choose(state, step["chooser"], rest, "hand_grant", amount=step["amount"], count=step["count"],
                     picked=step["picked"], by_card=step.get("by_card"))
    _grant(state, [iid], step["amount"])


def _then_stray_dog(state, step, cr):
    """Stray Dog: the ally gets +2, then it roams (no action spent; only if it still can roam this turn)."""
    top = state.top_unit(cr)
    if top is None:
        return
    state.effect_stack.append({"op": "forced_roam", "iid": top.iid, "player": step["chooser"]})
    _grant(state, [top.iid], step["amount"])


def _then_copy(state, step, cr):
    """The legendary Octopus (a mimic): "this becomes a copy of an adjacent animal" - its strength, keywords and text,
    not its Roar (it isn't placed). It is that card from now on (a Faceless Manipulator: removed, it goes to the Remove
    Pile as the copy)."""
    me, target = _find_instance(state, step["self"]), state.top_unit(cr)
    if me is None or target is None or _crossroad_of(state, me.iid) is None:
        return
    me.strength_counter = target.strength_counter
    _transform(state, me, target.card_id)


def _then_return_ally(state, step, cr):
    top = state.top_unit(cr)
    if top is not None and top.owner == step["chooser"] and statics.can_be_removed(state, top, cr):
        _bounce(state, cr, top)


def _then_cuckoo(state, step, cr):
    """The legendary Cuckoo: remove the chosen animal; if it was yours, play another animal."""
    top = state.top_unit(cr)
    if top is None:
        return
    if top.owner == step["chooser"]:
        _push_play_extra(state, step["chooser"])
    remove_top(state, cr, by_player=step["chooser"], by_card=step.get("by_card"))


def _then_remove_and_draw(state, step, cr):
    """Praying Mantis: remove the chosen ally to draw N cards (no removal, no cards)."""
    if remove_top(state, cr, by_player=step["chooser"], by_card=step.get("by_card")):
        draw_cards(state, step["chooser"], step["n"])


def _then_pile_to_hand(state, step, card_id):
    """Raccoon (your own Remove Pile), the legendary Raven (your opponent's): the chosen card goes to your hand."""
    if state.pile_take(card_id, step["from_owner"]):
        state.emit("unremove", card=card_id, owner=step["from_owner"], to=step["chooser"])
        state.add_to_hand(step["chooser"], card_id)


def _then_duplicate(state, step, iid):
    """Orangutan: a copy of the chosen hand card, its strength counter included."""
    inst = next((u for u in state.hands[step["chooser"]] if u.iid == iid), None)
    if inst is not None:
        state.add_to_hand(step["chooser"], inst.card_id, strength_counter=inst.strength_counter)


def _then_discard(state, step, iid):
    inst = next((u for u in state.hands[step["chooser"]] if u.iid == iid), None)
    if inst is not None:
        remove_from_hand(state, step["chooser"], inst)


def _then_spawn(state, step, cr):
    """Sunfish: a Baby Fish on the chosen empty crossroad."""
    if not state.board.get(cr):
        _spawn(state, step["chooser"], step["token"], cr)


def _then_roam_to(state, step, cr):
    _, unit = _find_unit(state, step["iid"])
    origin = _crossroad_of(state, step["iid"])
    if unit is not None and origin is not None and state.top_unit(origin) is unit:
        do_roam(state, unit.owner, origin, ("cr", cr))


THEN = {
    "remove": _then_remove, "set_strength": _then_set_strength, "drain": _then_drain, "grant": _then_grant,
    "hand_grant": _then_hand_grant, "stray_dog": _then_stray_dog, "copy": _then_copy, "return_ally": _then_return_ally,
    "cuckoo": _then_cuckoo, "remove_and_draw": _then_remove_and_draw, "pile_to_hand": _then_pile_to_hand,
    "duplicate": _then_duplicate, "discard": _then_discard, "spawn": _then_spawn, "roam_to": _then_roam_to,
}


def _op_forced_roam(state, step):
    """"It roams" (Stray Dog): a roam the effect pays for, under the Roam rules (connected to your den, once per turn).
    The player picks where; it can't take a den this way."""
    cr, unit = _find_unit(state, step["iid"])
    if unit is None or state.top_unit(cr) is not unit or state.turn_flags.get(f"roamed_{unit.iid}"):
        return None
    if not statics.can_roam(state, unit) or cr not in state.connected_occupied(unit.owner):
        return None
    targets = [t[1] for t in roam_targets(state, unit, cr) if t[0] == "cr"]
    _push_choose(state, step["player"], targets, "roam_to", iid=unit.iid, by_card=step.get("by_card"))
    return None


def _op_draw_to_match(state, step):
    """Divine Favor (the food-aggro legendary): draw until your hand is as big as your opponent's."""
    n = len(state.hands[other_player(step["player"])]) - len(state.hands[step["player"]])
    if n > 0:
        draw_cards(state, step["player"], n)
    return None


def _op_remove_then_draw(state, step):
    """The legendary Opossum: remove the covered ally, then draw a card (no removal, no card)."""
    cr, unit = _find_unit(state, step["iid"])
    if unit is not None and _remove_specific(state, cr, unit, by_player=step["player"], by_card=step.get("by_card")):
        draw_cards(state, step["player"], 1)
    return None


def _op_anteater(state, step):
    """Anteater: draw a card, then gain food equal to its strength (as it would be played now)."""
    drawn = draw_cards(state, step["player"], 1)
    if drawn and drawn[0] in state.hands[step["player"]]:
        gain_food(state, step["player"], placement_strength(state, drawn[0]))
    return None


def _op_flee_return(state, step):
    """Zebra: "When this flees, return the enemy that covered it to its owner's hand." (A return: Armor resists it.)"""
    cr, unit = _find_unit(state, step["iid"])
    if unit is not None and statics.can_be_removed(state, unit, cr):
        _bounce(state, cr, unit)
    return None


OPS.update({
    "choose": _op_choose,
    "forced_roam": _op_forced_roam,
    "draw_to_match": _op_draw_to_match,
    "remove_then_draw": _op_remove_then_draw,
    "anteater": _op_anteater,
    "flee_return": _op_flee_return,
})


# ============================================================== card behavior

def roar_condition(state, player, card_id, unit=None):
    """Whether the "if ..." of `card_id`'s Roar holds: None for a card with no such
    condition, or one that depends on where it lands (Lynx, Cheetah, Falcon). `unit` is the
    placed unit while its Roar resolves; None asks about the card in hand, as if it were
    played now (the client lights such cards up). The Roars below call this too, so the
    two can't disagree."""
    on_top = unit is not None and any(st and st[-1].iid == unit.iid for st in state.board.values())

    def others(*tags):          # friendly tops carrying `tags`, not counting this card
        n = _control_tag_count(state, player, *tags)
        return n - 1 if on_top and all(t in state.cards[card_id].tags for t in tags) else n
    cfg = state.config
    colony_min = cfg.colony_synergy_threshold

    def hand_after():           # cards in hand once this one has left it
        return len(state.hands[player]) - (0 if unit is not None else 1)

    def strength():
        if unit is not None:
            return effective_strength(state, unit)
        inst = playable_copy(state, player, card_id)
        return placement_strength(state, inst) if inst else 0
    check = {
        "gopher": lambda: _fed_this_turn(state, player),
        "muskrat": lambda: _fed_this_turn(state, player),
        "groundhog": lambda: _fed_this_turn(state, player),
        "bobcat": lambda: others("Cat") >= 1,
        "tutorial_lynx": lambda: others("Cat") >= 1,
        "house_cat": lambda: others("Cat") >= 1,
        "worker_bee": lambda: others("Worker") >= 1,
        "termite_king": lambda: _control_tag_count(state, player, "Colony", "Queen") >= 1,
        "nurse_bumblebee": lambda: others("Colony") + 1 >= colony_min,
        "soldier_ant": lambda: others("Colony") + 1 >= colony_min,
        "nurse_bee": lambda: _controls_two_same_colony(state, player) or (unit is None and any(
            st and st[-1].owner == player and st[-1].card_id == card_id for st in state.board.values())),
        "piranha": lambda: _lost_this_turn(state, player) >= 1,
        "hare": lambda: state.units_placed_this_turn + (0 if unit is not None else 1) >= cfg.hare_played_min,
        "macaque": lambda: hand_after() >= cfg.macaque_hand_min,
        "gorilla": lambda: strength() >= cfg.gorilla_min,
    }.get(card_id)
    return check() if check else None


def _controls_two_same_colony(state, player) -> bool:
    from collections import Counter
    counts = Counter(
        st[-1].card_id for st in state.board.values()
        if st and st[-1].owner == player and "Colony" in state.cards[st[-1].card_id].tags)
    return any(v >= 2 for v in counts.values())


def _conditional(effect):
    """A Roar that happens only while its roar_condition holds."""
    def handler(state, unit, cr):
        if roar_condition(state, unit.owner, unit.card_id, unit):
            effect(state, unit, cr)
    return handler


def _draws(n_attr=None, n=1):
    """A Roar (or Dawn/Dusk) that draws: `n_attr` names the config number, else `n` (1, printed "a card")."""
    def handler(state, unit, cr):
        _push_draw(state, unit.owner, getattr(state.config, n_attr) if n_attr else n)
    return handler


def _gains(attr):
    def handler(state, unit, cr):
        _push_gain(state, unit.owner, getattr(state.config, attr))
    return handler


def _removes(max_attr=None, min_attr=None):
    """Roar: remove an adjacent enemy (of strength N or less / more): the player picks it."""
    def handler(state, unit, cr):
        _push_remove_choice(state, unit.owner, unit.card_id, _adjacent_enemy_targets(
            state, unit, cr,
            max_strength=getattr(state.config, max_attr) if max_attr else None,
            min_strength=getattr(state.config, min_attr) if min_attr else None))
    return handler


def _draws_filtered(spec, n=1):
    def handler(state, unit, cr):
        state.effect_stack.append({"op": "draw_filtered", "player": unit.owner, "n": n, "spec": spec})
    return handler


# --- Aristocrats -----------------------------------------------------------------------------------------------

def _cuckoo_legend_place(state, unit, cr):
    """Roar: remove an adjacent animal of strength 4 or less. If it was yours, play another animal."""
    cap = state.config.cuckoo_legend_max
    options = [nb for nb, top in _adjacent_tops(state, cr)
               if effective_strength(state, top) <= cap and statics.can_be_removed(state, top, nb)
               and statics.can_be_chosen(state, top, unit.owner, nb)]
    _push_choose(state, unit.owner, options, "cuckoo")


def _ember_remove(state, unit, cr, pos):
    """When this is removed, shuffle it into your deck."""
    if state.pile_take(unit.card_id, unit.owner):
        shuffle_back(state, unit.owner, [unit.card_id])


def _opossum_legend_ally_covered(state, watcher, covered, coverer, cr):
    """When an ally is covered (by anyone), remove it and draw a card."""
    state.effect_stack.append({"op": "remove_then_draw", "iid": covered.iid, "player": watcher.owner})


def _mantis_place(state, unit, cr):
    """Roar: remove an adjacent ally to draw 2 cards. (A cost the player may decline.)"""
    _push_choose(state, unit.owner, _adjacent_friendly_units(state, unit, cr), "remove_and_draw", optional=True,
                 n=state.config.mantis_draw)


def _tarantula_eot(state, unit, cr):
    """Dusk: remove a random adjacent ally and gain its strength."""
    options = _adjacent_friendly_units(state, unit, cr)
    if not options:
        return
    nb = state.rng.choice(options)
    prey = state.top_unit(nb)
    gained = effective_strength(state, prey)
    if remove_top(state, nb, by_player=unit.owner, by_card=unit.card_id) and gained:
        unit.strength_counter += gained
        state.emit("strength", iid=unit.iid, card=unit.card_id, owner=unit.owner, n=gained)


def _sea_turtle_eot(state, unit, cr):
    """Dusk: place a Baby Turtle on an adjacent empty crossroad (a random one: Dusk asks no decision)."""
    empty = _empty_neighbors(state, cr)
    if empty:
        _spawn(state, unit.owner, "baby_turtle", state.rng.choice(empty))


def _raccoon_place(state, unit, cr):
    """Roar: return an animal from your Remove Pile to your hand."""
    _push_choose(state, unit.owner, sorted(set(state.pile_cards_of(unit.owner))), "pile_to_hand",
                 from_owner=unit.owner)


def _hyena_eot(state, unit, cr):
    """Dusk: gain 3 food for each of your animals removed this turn."""
    _push_gain(state, unit.owner, state.config.hyena_food_per * _lost_this_turn(state, unit.owner))


def _vulture_eot(state, unit, cr):
    """Dusk: if an ally was removed this turn, draw a card."""
    if _lost_this_turn(state, unit.owner):
        _push_draw(state, unit.owner, 1)


def _city_spider_trap(state, spider, placed, cr):
    """When an animal of strength 2 or less is placed adjacent to this, remove it (yours too)."""
    if effective_strength(state, placed) <= state.config.city_spider_max and statics.can_be_removed(state, placed, cr):
        state.effect_stack.append(remove_iid_step(placed.iid, by_player=spider.owner, by_effect=True,
                                                  source_iid=spider.iid, by_card=spider.card_id))


def _earthworm_remove(state, unit, cr, pos):
    """When this is removed, place two Worms on its crossroad: they land on top, as placements do, while the crossroad is
    empty or yours. Under an enemy there is no room for them (rulings.md: Worms never cover an enemy)."""
    for _ in range(state.config.earthworm_worms):
        top = state.top_unit(cr)
        if top is not None and top.owner != unit.owner or state.result is not None:
            return
        _spawn(state, unit.owner, "worm", cr)


def _worm_remove(state, unit, cr, pos):
    """Worm: when this is removed, draw a card."""
    draw_cards(state, unit.owner, 1)


def _cockroach_remove(state, unit, cr, pos):
    """When this is removed, put it back in your hand and draw a card."""
    if state.pile_take(unit.card_id, unit.owner):
        state.add_to_hand(unit.owner, unit.card_id)
    draw_cards(state, unit.owner, 1)


# --- Canines ----------------------------------------------------------------------------------------------------

def _lobo_friendly_roam(state, watcher, roamer, event):
    """Whenever an ally roams onto an enemy, draw a card."""
    if event["onto_enemy"]:
        _push_draw(state, watcher.owner, 1)


def _wolf_legend_roam(state, unit, cr, event):
    """When this roams, your adjacent animals gain +2 strength."""
    _grant(state, [top.iid for _, top in _adjacent_tops(state, cr, unit.owner)], state.config.wolf_legend_grant)


def _awd_cover(state, unit, covered):
    """Whenever this covers an enemy (placed or roaming), draw a card."""
    _push_draw(state, unit.owner, 1)


def _jackal_place(state, unit, cr):
    """Roar: remove an adjacent enemy that has another of your Canines adjacent to it."""
    def flanked(nb):
        return any(top.iid != unit.iid and "Canine" in state.cards[top.card_id].tags
                   for _, top in _adjacent_tops(state, nb, unit.owner))
    _push_remove_choice(state, unit.owner, unit.card_id,
                        [nb for nb in _adjacent_enemy_targets(state, unit, cr) if flanked(nb)])


def _bush_dog_place(state, unit, cr):
    """Roar: give an adjacent Canine +3 strength (one of yours)."""
    options = [nb for nb, top in _adjacent_tops(state, cr, unit.owner) if "Canine" in state.cards[top.card_id].tags]
    _push_choose(state, unit.owner, options, "grant", amount=state.config.bush_dog_grant)


def _raccoon_dog_friendly_roam(state, watcher, roamer, event):
    """Whenever an allied Canine roams, give it +1 strength."""
    if "Canine" in state.cards[roamer.card_id].tags:
        _grant(state, [roamer.iid], state.config.raccoon_dog_grant)


def _fox_eot(state, unit, cr):
    """Dusk: give your adjacent animals +1 strength."""
    _grant(state, [top.iid for _, top in _adjacent_tops(state, cr, unit.owner)], state.config.fox_grant)


def _stray_dog_place(state, unit, cr):
    """Roar: give an ally with Roam +2 strength. It roams."""
    options = sorted(c for c, st in state.board.items()
                     if st and st[-1].owner == unit.owner and st[-1] is not unit and statics.can_roam(state, st[-1]))
    _push_choose(state, unit.owner, options, "stray_dog", amount=state.config.stray_dog_grant)


def _dingo_eot(state, unit, cr):
    _grant(state, _friendly_adjacent_canine_iids(state, unit, cr), state.config.dingo_grant)


def _spawn_pups(state, unit, cr, n, token_ids=("pup",)):
    """Land up to `n` tokens on random empty crossroads adjacent to `cr`, cycling through `token_ids`."""
    empty = _empty_neighbors(state, cr)
    state.rng.shuffle(empty)
    for i, spot in enumerate(empty[:n]):
        _spawn(state, unit.owner, token_ids[i % len(token_ids)], spot)


def _alpha_place(state, unit, cr):
    _spawn_pups(state, unit, cr, state.config.alpha_pups, ("poppy", "rusty"))


def _unnamed_canine_place(state, unit, cr):
    if effective_strength(state, unit) >= state.config.unnamed_canine_draw_threshold:
        _push_draw(state, unit.owner, 1)


def _shuck_place(state, unit, cr):
    # Reserve design: return a removed Canine from the Remove Pile to hand with a +2 counter.
    canines = sorted({cid for cid in state.remove_pile if "Canine" in state.cards[cid].tags})
    if canines:
        state.effect_stack.append({"op": "shuck_return", "chooser": unit.owner, "options": canines})


def _op_shuck_return(state, step):
    if "choice" not in step:
        return PendingRequest("choice", step["chooser"], optional=False, options=step["options"])
    if state.pile_take(step["choice"]):
        state.add_to_hand(step["chooser"], step["choice"], strength_counter=state.config.shuck_grant)
    return None


OPS["shuck_return"] = _op_shuck_return


# --- Cats -------------------------------------------------------------------------------------------------------

def _serval_place(state, unit, cr):
    """Roar: set an adjacent enemy's strength to 1."""
    _push_choose(state, unit.owner, [nb for nb, top in _adjacent_tops(state, cr)
                                     if top.owner != unit.owner and statics.can_be_chosen(state, top, unit.owner, nb)],
                 "set_strength")


def _house_cat_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_play_extra(state, unit.owner, filter={"tags_all": ["Cat"]})


def _twin_place(twin_id):
    def handler(state, unit, cr):
        state.effect_stack.append({"op": "play_named", "chooser": unit.owner, "card_id": twin_id})
    return handler


def _queen_adira_remove_event(state, unit, cr, event):
    if (event.get("by_player") == unit.owner and event["owner"] != unit.owner
            and event.get("by_card") and "Cat" in state.cards[event["by_card"]].tags):
        if not _capped(state, "cap_queen_adira", unit):
            draw_cards(state, unit.owner, 1)


# --- Colony -----------------------------------------------------------------------------------------------------

def _queen_honoria_friendly_play(state, watcher, played) -> None:
    if "Colony" in state.cards[played.card_id].tags and not _capped(state, "cap_queen_honoria", watcher):
        gain_food(state, played.owner, state.config.queen_honoria_per_play)


def _worker_bee_place(state, unit, cr):
    amount = state.config.worker_bee_food
    if roar_condition(state, unit.owner, unit.card_id, unit):   # another Worker besides itself
        amount += state.config.worker_bee_extra
    _push_gain(state, unit.owner, amount)


def _queen_marabunta_place(state, unit, cr):
    others = _control_tag_count(state, unit.owner, "Colony") - 1   # other friendly Colony units
    _push_gain(state, unit.owner, state.config.queen_marabunta_per_colony * max(0, others))


# --- Den Rush ---------------------------------------------------------------------------------------------------

def _greywhisker_place(state, unit, cr):
    """Roar: gain 1 food, draw a card, play another animal, then discard a card."""
    o = unit.owner
    state.effect_stack.append({"op": "discard_choice", "player": o})
    _push_play_extra(state, o)
    _push_draw(state, o, 1)
    _push_gain(state, o, state.config.greywhisker_food)


def _op_discard_choice(state, step):
    """Discard a card of your choice from your hand (none to discard: nothing)."""
    hand = _hand_iids(state, step["player"])
    if hand:
        _push_choose(state, step["player"], hand, "discard", by_card=step.get("by_card"))
    return None


OPS["discard_choice"] = _op_discard_choice


def _naked_mole_rat_place(state, unit, cr):
    """Roar: play another animal adjacent to this."""
    _push_play_extra(state, unit.owner, filter={"adjacent_to": cr})


def _gale_place(state, unit, cr):
    # "Roar: draw a card for each animal you control adjacent to the opponent's den" (Gale included).
    front = state.game_map.hq_front(other_player(unit.owner))
    _push_draw(state, unit.owner, sum(1 for c in front if (top := state.top_unit(c)) and top.owner == unit.owner))


def _hq_adjacent_draw(state, unit, cr):
    if cr in state.game_map.hq_front(other_player(unit.owner)):  # adjacent to the opponent's den (F6)
        _push_draw(state, unit.owner, 1)


def _adjacent_enemy_unit_crossroads(state, unit, cr, *, chosen=True):
    """Adjacent crossroads topped by an enemy *unit* that can be moved (for bounces).
    Armor can't be moved by anyone; Stealth only hides from a `chosen` pick (Skunk),
    not from a mass bounce (Sirocco, `chosen=False`) - keyword-review decision B."""
    return [nb for nb, top in _adjacent_tops(state, cr)
            if top.owner != unit.owner and statics.can_be_removed(state, top, nb)
            and (not chosen or statics.can_be_chosen(state, top, unit.owner, nb))]


def _rat_place(state, unit, cr):
    # "Remove an adjacent enemy, then discard a random card." The hand card goes whether or not there was a target.
    state.effect_stack.append({"op": "rat_discard", "player": unit.owner})
    _push_remove_choice(state, unit.owner, "rat", _adjacent_enemy_targets(state, unit, cr))


def _op_rat_discard(state, step):
    hand = state.hands[step["player"]]
    if hand:
        remove_from_hand(state, step["player"], state.rng.choice(hand))   # a remove, not a Deathrattle
    return None


def _has_spare_copy(state, player, card_id) -> bool:
    return (any(u.card_id == card_id for u in state.hands[player])
            or card_id in state.decks[player])


def _remove_another_copy(state, player, card_id) -> None:
    """Consume one other copy of `card_id` from hand (if any) else deck, to the Remove Pile
    (a remove, not a Deathrattle - the paid copy never touched the board)."""
    for inst in state.hands[player]:
        if inst.card_id == card_id:
            remove_from_hand(state, player, inst)
            return
    state.decks[player].remove(card_id)
    state.pile_add(card_id, player)
    state.emit("remove", zone="deck", card=card_id, owner=player)
    _fire_remove_event(state, card_id, player, None)


def _hornet_place(state, unit, cr):
    targets = _adjacent_enemy_targets(state, unit, cr)
    if targets and _has_spare_copy(state, unit.owner, "hornet"):
        state.effect_stack.append({"op": "hornet_kill", "chooser": unit.owner, "options": targets})


def _op_hornet_kill(state, step):
    if "choice" not in step:
        return PendingRequest("choice", step["chooser"], optional=True, options=step["options"])
    if step["choice"] == SKIP:
        return None
    _remove_another_copy(state, step["chooser"], "hornet")
    remove_top(state, step["choice"], by_player=step["chooser"], by_card="hornet")
    return None


def _pestis_place(state, unit, cr):
    # "Remove an adjacent enemy and every unit buried under it": the target is a chosen enemy
    # (so Stealth and Armor tops are off limits, as for any removal), the whole stack goes.
    options = _adjacent_enemy_unit_crossroads(state, unit, cr)
    if options:
        state.effect_stack.append({"op": "pestis_wipe", "chooser": unit.owner, "options": options})


def _op_pestis_wipe(state, step):
    if "choice" not in step:   # asked even with one target
        return PendingRequest("choice", step["chooser"], optional=False, options=step["options"])
    target = step["choice"]
    # Remove the entire stack under the enemy, both players' units, top-down. A buried
    # Armor unit is skipped in place, not a shield: everything else is still wiped around it.
    for unit in reversed(list(state.board.get(target) or [])):
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
    if "choice" not in step:   # asked even with one target
        return PendingRequest("choice", step["chooser"], optional=False, options=step["options"])
    top = state.top_unit(step["choice"])
    if top is not None:                                  # locked through the owner's next turn (F4)
        _bounce(state, step["choice"], top, lock_until=state.turn_counter + 2)
    return None


def _fill(state, unit, cr):
    """Lemming, Sardine: place every copy of this card from your hand and deck on random adjacent empty crossroads.
    Hand copies go first; the placed copies don't Roar, and leftovers stay where they are."""
    cid, o = unit.card_id, unit.owner
    hand = [u for u in state.hands[o] if u.card_id == cid]
    sources = [("hand", inst) for inst in hand] + [("deck", None)] * state.decks[o].count(cid)
    state.rng.shuffle(sources)
    empty = _empty_neighbors(state, cr)
    state.rng.shuffle(empty)
    for (kind, inst), spot in zip(sources, empty):
        if state.board.get(spot) or state.result is not None:
            continue
        if kind == "hand":
            if inst not in state.hands[o]:
                continue
            state.hands[o].remove(inst)
        else:
            if cid not in state.decks[o]:
                continue
            state.decks[o].remove(cid)
            inst = UnitInstance(cid, o, state.new_iid())
        _land_unit(state, o, inst, spot, from_hand=kind == "hand", roar=False)


# --- Egg Control ------------------------------------------------------------------------------------------------

def _eon_event(state, unit, cr, event):           # any draw/shuffle/remove -> +1 (reserve design)
    if not _capped(state, "cap_eon", unit):
        gain_food(state, unit.owner, state.config.eon_food)


def _rattlesnake_shuffle_event(state, event):
    """Each copy grows on its owner's shuffle, including copies still in the deck."""
    player = event["player"]
    if _owns_copy(state, player, "rattlesnake"):
        counters = state.card_strength_counters.setdefault(player, {})
        counters["rattlesnake"] = counters.get("rattlesnake", 0) + 1
        state.emit("strength", card="rattlesnake", owner=player, n=1)   # every copy, wherever it is


def _owns_copy(state, player: str, card_id: str) -> bool:
    """Whether `player` has `card_id` anywhere: starting deck, deck, hand or board."""
    return (
        card_id in state.starting_decks.get(player, ())
        or card_id in state.decks[player]
        or any(u.card_id == card_id for u in state.hands[player])
        or any(u.card_id == card_id and u.owner == player
               for stack in state.board.values() for u in stack)
    )


def _omen_drawn(state, inst):
    """Black Swan: whenever you draw it, your opponent discards a random card (a remove, not a Deathrattle)."""
    opponent = other_player(inst.owner)
    hand = state.hands[opponent]
    if hand:
        remove_from_hand(state, opponent, state.rng.choice(hand))


def _raven_legend_place(state, unit, cr):
    """Roar: put an animal from your opponent's Remove Pile into your hand."""
    opp = other_player(unit.owner)
    _push_choose(state, unit.owner, sorted(set(state.pile_cards_of(opp))), "pile_to_hand", from_owner=opp)


def _owl_place(state, unit, cr):
    state.effect_stack.append({"op": "scout", "player": unit.owner, "spec": None})   # the deck's top cards


def _raven_place(state, unit, cr):
    state.effect_stack.append({"op": "raven_dig", "player": unit.owner})


def _viper_place(state, unit, cr):
    _drain_place(state, unit, cr, state.config.viper_poison)


def _mosquito_place(state, unit, cr):
    _drain_place(state, unit, cr, state.config.mosquito_drain)


def _drain_place(state, unit, cr, amount):
    """Roar: give an adjacent enemy -N strength."""
    _push_choose(state, unit.owner, [nb for nb, top in _adjacent_tops(state, cr)
                                     if top.owner != unit.owner and statics.can_be_chosen(state, top, unit.owner, nb)],
                 "drain", amount=amount)


def _king_cobra_place(state, unit, cr):
    """Roar: choose an adjacent enemy. At the start of your next turn, remove it."""
    targets = _adjacent_enemy_targets(state, unit, cr)
    if targets:
        state.effect_stack.append({"op": "venom", "chooser": unit.owner, "options": targets})


def _op_venom(state, step):
    """King Cobra: the chosen adjacent enemy is removed at the start of the cobra owner's next turn. The venom is on the
    bitten unit, not on the snake (rules §9.1 exception): it resolves even if the cobra is gone or the bitten unit is
    buried, and is cancelled only if the bitten unit leaves the board."""
    if "choice" not in step:   # asked even with one target
        return PendingRequest("choice", step["chooser"], optional=False, options=step["options"])
    target = state.top_unit(step["choice"])
    if target is not None:
        state.scheduled.append({"iid": target.iid, "owner": step["chooser"], "remaining": 1, "while_buried": True,
                                "step": remove_iid_step(target.iid, by_player=step["chooser"], by_effect=True,
                                                        source_iid=None, by_card=step.get("by_card"))})
    return None


def _eon_end_of_turn(state, unit, cr):
    # The Ouroboros: it leaves the board (a return, not a remove - no Deathrattle, nothing to
    # the Remove Pile) and shuffles into its owner's deck, a little smaller each cycle. The loss
    # is kept per card id, like Rattlesnake's growth, so it survives the trip through the deck.
    state.emit("to_deck", cr=cr, iid=unit.iid, card=unit.card_id, owner=unit.owner)
    state.board[cr].remove(unit)
    if not state.board[cr]:
        del state.board[cr]
    counters = state.card_strength_counters.setdefault(unit.owner, {})
    counters["eon"] = counters.get("eon", 0) - state.config.eon_decay
    state.emit("strength", card="eon", owner=unit.owner, n=-state.config.eon_decay)   # every copy (this one is in the deck now)
    shuffle_back(state, unit.owner, ["eon"])


def _magpie_place(state, unit, cr):
    state.effect_stack.append({"op": "magpie_steal", "player": unit.owner})


def _op_magpie_steal(state, step):
    """Take a random card from the opponent's hand (it becomes yours), then discard a card of
    your choice. The stolen card isn't a remove: it changes hands; the discard is (Remove Pile)."""
    player = step["player"]
    if "stolen" not in step:
        step["stolen"] = True
        theirs = state.hands[other_player(player)]
        if theirs:
            inst = state.rng.choice(theirs)
            theirs.remove(inst)
            new = UnitInstance(inst.card_id, player, state.new_iid())
            state.hands[player].append(new)
            state.emit("steal", player=player, victim=other_player(player), iid=inst.iid, new=new.iid, card=inst.card_id)
            state.ensure_mates(player)
    hand = state.hands[player]
    if not hand:
        return None
    if "choice" not in step:
        if len(hand) == 1:
            step["choice"] = hand[0].iid
        else:
            return PendingRequest("choice", player, optional=False, options=[u.iid for u in hand], from_deck_reveal=True)
    inst = next((u for u in hand if u.iid == step["choice"]), None)
    if inst is not None:
        remove_from_hand(state, player, inst)
    return None


def _bird_egg_place(state, unit, cr):
    state.effect_stack.append({"op": "scout", "player": unit.owner, "spec": "tag:Bird"})
    schedule(state, unit, state.config.bird_egg_hatch_delay,
             {"op": "bird_egg_hatch", "iid": unit.iid}, while_buried=False)


def _snake_egg_place(state, unit, cr):
    state.effect_stack.append({"op": "draw_filtered", "player": unit.owner,
                               "n": state.config.snake_egg_draw, "spec": "tag:Snake"})
    schedule(state, unit, state.config.egg_hatch_delay,
             {"op": "egg_hatch", "iid": unit.iid, "n": state.config.egg_hatch_draw, "spec": "tag:Snake"}, while_buried=False)


def _aurum_start(state, unit, cr):
    _push_draw(state, unit.owner, 1)


# --- Fish -------------------------------------------------------------------------------------------------------

def _tuna_legend_place(state, unit, cr):
    """Roar: for each region you control, draw a card and gain 5 food."""
    n = len(statics.regions_of(state, unit.owner))
    _push_gain(state, unit.owner, n * state.config.tuna_legend_food)
    _push_draw(state, unit.owner, n)


def _manta_legend_eot(state, unit, cr):
    """Dusk: if you control 2 or more regions, draw a card."""
    if len(statics.regions_of(state, unit.owner)) >= state.config.manta_legend_regions:
        _push_draw(state, unit.owner, 1)


def _adjacent_ally_fish(state, unit, cr) -> int:
    return sum(1 for _, top in _adjacent_tops(state, cr, unit.owner) if "Fish" in state.cards[top.card_id].tags)


def _swordfish_place(state, unit, cr):
    """Roar: remove a random adjacent enemy for each adjacent allied Fish."""
    n = _adjacent_ally_fish(state, unit, cr)
    targets = _adjacent_enemy_targets(state, unit, cr, chosen=False)
    state.rng.shuffle(targets)
    for nb in targets[:n]:
        state.effect_stack.append(remove_iid_step(state.top_unit(nb).iid, by_player=unit.owner, by_effect=True,
                                                  source_iid=None, by_card=unit.card_id))


def _barracuda_place(state, unit, cr):
    """Roar: remove an adjacent enemy with strength up to the number of your Fish (this one included)."""
    _push_remove_choice(state, unit.owner, unit.card_id, _adjacent_enemy_targets(
        state, unit, cr, max_strength=_control_tag_count(state, unit.owner, "Fish")))


def _manta_ally_covered(state, watcher, covered, coverer, cr):
    """Whenever your opponent covers an allied Fish, draw a card."""
    if coverer.owner != watcher.owner and "Fish" in state.cards[covered.card_id].tags:
        _push_draw(state, watcher.owner, 1)


def _remora_place(state, unit, cr):
    _push_play_extra(state, unit.owner, filter={"tags_all": ["Fish"]})


def _cod_place(state, unit, cr):
    """Roar: draw a card for each adjacent allied Fish."""
    _push_draw(state, unit.owner, _adjacent_ally_fish(state, unit, cr))


def _mahi_mahi_place(state, unit, cr):
    """Roar: give your other Fish +1 strength."""
    _grant(state, [st[-1].iid for st in state.board.values()
                   if st and st[-1].owner == unit.owner and st[-1] is not unit
                   and "Fish" in state.cards[st[-1].card_id].tags], state.config.mahi_mahi_grant)


def _sunfish_place(state, unit, cr):
    """Roar: place a Baby Fish on an adjacent empty crossroad (the player picks it)."""
    _push_choose(state, unit.owner, _empty_neighbors(state, cr), "spawn", token="baby_fish")


# --- Food Aggro -------------------------------------------------------------------------------------------------

def _repeat_legend_place(state, unit, cr):
    """Roar: repeat the Roar of each of your adjacent Rodents (as if each roared again where it stands). Another of these
    (a mimic Octopus's copy) isn't repeated: two side by side would repeat each other for ever."""
    for nb, top in reversed(_adjacent_tops(state, cr, unit.owner)):
        if "Rodent" in state.cards[top.card_id].tags and top.card_id != unit.card_id:
            _push_hook(state, top, nb, "on_place")


def _refill_legend_place(state, unit, cr):
    """Roar: draw cards until you have as many as your opponent."""
    state.effect_stack.append({"op": "draw_to_match", "player": unit.owner})


def _scrooge_place(state, unit, cr):
    # Roar: gain food equal to the food you gained this turn. Snapshot now; the gain resolves as a literal amount.
    _push_gain(state, unit.owner, _food_gained_this_turn(state, unit.owner) * state.config.scrooge_gain_multiplier)


def _rat_king_place(state, unit, cr):
    others = _control_tag_count(state, unit.owner, "Rodent") - 1     # Barley: other Rodents
    _push_draw(state, unit.owner, 1)
    _push_gain(state, unit.owner, state.config.rat_king_per_rodent * max(0, others))


def _meerkat_enemy_placed(state, meerkat, placed, cr):
    """When an enemy is placed adjacent to this, draw a card."""
    _push_draw(state, meerkat.owner, 1)


def _chipmunk_place(state, unit, cr):
    """Roar: next turn, take 1 additional action."""
    schedule(state, unit, 1, {"op": "grant_action", "player": unit.owner, "n": state.config.chipmunk_bonus_actions},
             while_buried=False)


def _dormouse_eot(state, unit, cr):
    """Dusk: if your hand is empty, gain 10 food."""
    if not state.hands[unit.owner]:
        _push_gain(state, unit.owner, state.config.dormouse_food)


def _hamster_place(state, unit, cr):
    """Roar: gain 10 food. At the start of your next turn, gain 10 more."""
    _push_gain(state, unit.owner, state.config.hamster_food_now)
    schedule(state, unit, 1, {"op": "gain_food", "player": unit.owner, "amount": state.config.hamster_food_later},
             while_buried=False)


def _mole_place(state, unit, cr):
    """Roar: gain 5 food. If your hand is empty, draw 2 cards."""
    if not state.hands[unit.owner]:
        _push_draw(state, unit.owner, state.config.mole_draw)
    _push_gain(state, unit.owner, state.config.mole_food)


# --- Food OTK ---------------------------------------------------------------------------------------------------

def _fathom_place(state, unit, cr):
    state.effect_stack.append({"op": "scout", "player": unit.owner, "spec": "rarity:legendary"})


def _otk_squirrel_place(state, unit, cr):
    """Roar: lose all your food. In 2 turns, gain three times as much. (A timer on this animal: covering it pauses it,
    removing it loses the stake.)"""
    stake = state.food[unit.owner]
    lose_food(state, unit.owner, stake, card=unit.card_id)
    if stake:
        schedule(state, unit, state.config.otk_squirrel_delay,
                 {"op": "gain_food", "player": unit.owner, "amount": stake * state.config.otk_squirrel_multiplier},
                 while_buried=False)


def _mimic_place(state, unit, cr):
    """Roar: this becomes a copy of an adjacent animal (an enemy only if it may be chosen)."""
    _push_choose(state, unit.owner, [nb for nb, top in _adjacent_tops(state, cr)
                                     if statics.can_be_chosen(state, top, unit.owner, nb)], "copy", self=unit.iid)


def _orb_weaver_enemy_placed(state, spider, placed, cr):
    """When an enemy with Flight is placed adjacent to this, remove it."""
    if statics.has_keyword(state, placed, "Flight", cr) and statics.can_be_removed(state, placed, cr):
        state.effect_stack.append(remove_iid_step(placed.iid, by_player=spider.owner, by_effect=True,
                                                  source_iid=spider.iid, by_card=spider.card_id))


def _tortoise_place(state, unit, cr):
    """Roar: gain 5 food for each of your animals with Armor (this one included)."""
    n = sum(1 for c, st in state.board.items()
            if st and st[-1].owner == unit.owner and statics.has_keyword(state, st[-1], "Armor", c))
    _push_gain(state, unit.owner, n * state.config.tortoise_per_armor)


def _black_bear_place(state, unit, cr):
    schedule(state, unit, state.config.black_bear_delay,
             {"op": "draw", "player": unit.owner, "n": state.config.black_bear_draw}, while_buried=False)


# --- Giants -----------------------------------------------------------------------------------------------------

def _rhinoceros_place(state, unit, cr):
    for nb in _adjacent_enemy_targets(state, unit, cr, max_strength=state.config.rhinoceros_max,
                                      chosen=False):        # mass AoE hits Stealth
        state.effect_stack.append(remove_iid_step(state.top_unit(nb).iid, by_player=unit.owner, by_effect=True,
                                                  source_iid=None, by_card=unit.card_id))


def _remove_all_adjacent(state, unit, cr):
    """Brutus, Sperm Whale: "Roar: remove all adjacent animals." Yours too; Armor survives; Stealth doesn't hide."""
    for nb, top in _adjacent_tops(state, cr):
        if statics.can_be_removed(state, top, nb):
            state.effect_stack.append(remove_iid_step(top.iid, by_player=unit.owner, by_effect=True,
                                                      source_iid=None, by_card=unit.card_id))


def _mocha_place(state, unit, cr):
    """Roar: remove all enemies adjacent to your animals (this one included)."""
    mine = [c for c, st in state.board.items() if st and st[-1].owner == unit.owner]
    hit = sorted({nb for c in mine for nb, top in _adjacent_tops(state, c)
                  if top.owner != unit.owner and statics.can_be_removed(state, top, nb)})
    for nb in hit:
        state.effect_stack.append(remove_iid_step(state.top_unit(nb).iid, by_player=unit.owner, by_effect=True,
                                                  source_iid=None, by_card=unit.card_id))


def _hippo_enemy_placed(state, hippo, placed, cr):
    # Automatic trigger, nobody "chose" the target: Stealth doesn't hide (decision B).
    if (effective_strength(state, placed) <= state.config.hippopotamus_max
            and statics.can_be_removed(state, placed, cr)):
        state.effect_stack.append(remove_iid_step(placed.iid, by_player=hippo.owner, by_effect=True,
                                                  source_iid=hippo.iid, by_card=hippo.card_id))


def _methuselah_eot(state, unit, cr):
    _push_gain(state, unit.owner, state.config.methuselah_food)


def _oxpecker_place(state, unit, cr):
    """Roar: gain 1 food for each animal of strength 8 or more in your starting deck."""
    n = sum(1 for cid in state.starting_decks.get(unit.owner, ())
            if isinstance(state.cards[cid].base_strength, int)
            and state.cards[cid].base_strength >= state.config.oxpecker_min)
    _push_gain(state, unit.owner, n)


def _anteater_place(state, unit, cr):
    state.effect_stack.append({"op": "anteater", "player": unit.owner})


def _dung_beetle_eot(state, unit, cr):
    """At the end of your turn, gain 2 food for each Hungry animal you control."""
    n = sum(1 for c, st in state.board.items()
            if st and st[-1].owner == unit.owner and statics.has_keyword(state, st[-1], "Hungry", c))
    _push_gain(state, unit.owner, n * state.config.dung_beetle_per)


def _sloth_place(state, unit, cr):
    """"In 2 turns, gain 30 food." Its counterplay is the timed-effect rule (overview.md 9.1): cover the Sloth and the
    timer suspends for as long as the cover holds."""
    schedule(state, unit, state.config.sloth_delay,
             {"op": "gain_food", "player": unit.owner, "amount": state.config.sloth_food}, while_buried=False)


# --- Handlock ---------------------------------------------------------------------------------------------------

def _baboon_legend_eot(state, unit, cr):
    """Dusk: give 2 random animals in your hand +1 strength."""
    hand = _hand_iids(state, unit.owner)
    k = min(len(hand), state.config.baboon_legend_count)
    _grant(state, state.rng.sample(hand, k), state.config.baboon_legend_grant)


def _silverback_place(state, unit, cr):
    """Roar: give all animals in your hand +2 strength."""
    _grant(state, _hand_iids(state, unit.owner), state.config.silverback_grant)


BUTTERFLY_STAGES = ["handlock_legend_butterfly", "handlock_legend_butterfly_2", "handlock_legend_butterfly_3",
                    "handlock_legend_butterfly_4", "handlock_legend_butterfly_5"]


def _butterfly_evolve(state, inst, amount):
    """The legendary Butterfly: whenever it gains strength in your hand, it moves one stage on (one buff, one stage;
    five stages, each adding to the last)."""
    i = BUTTERFLY_STAGES.index(inst.card_id)
    if i + 1 < len(BUTTERFLY_STAGES):
        _transform(state, inst, BUTTERFLY_STAGES[i + 1])


def _hand_grant_one(state, unit, amount):
    """"give an animal in your hand +N": the player picks it."""
    _push_choose(state, unit.owner, _hand_iids(state, unit.owner), "grant", amount=amount)


def _draw_then_give_one(state, unit, cr):
    """Butterfly, the Chrysalis stage: "Roar: draw a card, then give an animal in your hand +1 strength."."""
    state.effect_stack.append({"op": "hand_grant_one", "player": unit.owner, "amount": state.config.butterfly_grant})
    _push_draw(state, unit.owner, 1)


def _op_hand_grant_one(state, step):
    _push_choose(state, step["player"], _hand_iids(state, step["player"]), "grant", amount=step["amount"],
                 by_card=step.get("by_card"))
    return None


OPS["hand_grant_one"] = _op_hand_grant_one


def _op_hand_grant_all(state, step):
    _grant(state, _hand_iids(state, step["player"]), step["amount"])
    return None


OPS["hand_grant_all"] = _op_hand_grant_all


def _butterfly_stage_place(draw_attr, grant_attr):
    """The Butterfly stage and the Monarch: "Roar: draw N, then give all animals in your hand +N strength."."""
    def handler(state, unit, cr):
        state.effect_stack.append({"op": "hand_grant_all", "player": unit.owner,
                                   "amount": getattr(state.config, grant_attr)})
        _push_draw(state, unit.owner, getattr(state.config, draw_attr) if draw_attr else 1)
    return handler


def _macaque_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_remove_choice(state, unit.owner, unit.card_id, _adjacent_enemy_targets(state, unit, cr))


def _orangutan_place(state, unit, cr):
    """Roar: duplicate a Primate in your hand."""
    _push_choose(state, unit.owner, _hand_iids(state, unit.owner, tag="Primate"), "duplicate")


def _tarsier_place(state, unit, cr):
    """Roar: Scout a Primate and give it +1 strength."""
    state.effect_stack.append({"op": "scout", "player": unit.owner, "spec": "tag:Primate",
                               "grant": state.config.tarsier_grant})


def _chimpanzee_place(state, unit, cr):
    """Roar: remove an adjacent enemy of equal or lower strength."""
    _push_remove_choice(state, unit.owner, unit.card_id,
                        _adjacent_enemy_targets(state, unit, cr, max_strength=effective_strength(state, unit)))


def _baboon_place(state, unit, cr):
    """Roar: give 2 animals in your hand +1 strength (two different ones, the player's pick)."""
    cfg = state.config
    hand = _hand_iids(state, unit.owner)
    if len(hand) <= cfg.baboon_count:
        _grant(state, hand, cfg.baboon_grant)
    else:
        _push_choose(state, unit.owner, hand, "hand_grant", amount=cfg.baboon_grant, count=cfg.baboon_count)


YOUNGLINGS = ["baby_lion", "baby_wolf", "baby_squirrel", "baby_owl", "baby_python", "baby_bear", "baby_gorilla",
              "baby_zebra"]


def _stork_place(state, unit, cr):
    """Roar: add two random younglings to your hand (two different ones)."""
    for cid in state.rng.sample(YOUNGLINGS, state.config.stork_younglings):
        state.add_to_hand(unit.owner, cid)


def _caterpillar_grows(state, inst, amount):
    """When this gains strength in your hand, draw a card and turn this into a Butterfly."""
    _transform(state, inst, "butterfly")
    draw_cards(state, inst.owner, 1)


def _gorilla_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_draw(state, unit.owner, 1)


# --- Hoofed -----------------------------------------------------------------------------------------------------

def _zebra_legend_place(state, unit, cr):
    """Roar: draw a card for each different Hoofed ally adjacent to this (allies only; different cards)."""
    kinds = {top.card_id for _, top in _adjacent_tops(state, cr)
             if top.owner == unit.owner and "Hoofed" in state.cards[top.card_id].tags}
    _push_draw(state, unit.owner, len(kinds))


def _okapi_eot(state, unit, cr):
    """Dusk: if this is grazing, draw a card."""
    if statics.grazing(state, unit, cr):
        _push_draw(state, unit.owner, 1)


def _zebra_flee(state, unit, coverer_iid):
    """When this flees, return the enemy that covered it to its owner's hand."""
    state.effect_stack.append({"op": "flee_return", "iid": coverer_iid})


def _cape_buffalo_place(state, unit, cr):
    """Roar: remove an adjacent enemy covering an allied Hoofed animal (the animal right beneath it)."""
    def covering(nb):
        st = state.board[nb]
        return len(st) >= 2 and st[-2].owner == unit.owner and "Hoofed" in state.cards[st[-2].card_id].tags
    _push_remove_choice(state, unit.owner, unit.card_id,
                        [nb for nb in _adjacent_enemy_targets(state, unit, cr) if covering(nb)])


def _wildebeest_eot(state, unit, cr):
    """At the end of your turn, if this is grazing, gain 5 food."""
    if statics.grazing(state, unit, cr):
        _push_gain(state, unit.owner, state.config.wildebeest_food)


# --- The pool ---------------------------------------------------------------------------------------------------

def _octopus_ink_place(state, unit, cr):
    """Roar: choose an adjacent enemy. Until your next turn, it loses all its effects (keywords included, so an
    animal with Armor can be inked; Stealth still keeps it from being chosen)."""
    options = [nb for nb in sorted(state.game_map.neighbors(cr))
               if (top := state.top_unit(nb)) is not None and top.owner != unit.owner
               and statics.can_be_chosen(state, top, unit.owner, nb)]
    _push_choose(state, unit.owner, options, "ink", until=state.turn_counter + 2)   # the inking player's next turn


def _then_ink(state, step, cr):
    top = state.top_unit(cr)
    if top is not None and top.owner != step["chooser"]:
        state.inked[top.iid] = step["until"]
        state.emit("inked", iid=top.iid, card=top.card_id, owner=top.owner)


THEN["ink"] = _then_ink


def _macaw_place(state, unit, cr):
    """Roar: your next Roar this turn happens twice."""
    state.roar_twice[unit.owner] = state.turn_counter


def _cuckoo_place(state, unit, cr):
    """Roar: shuffle two Cuckoo Eggs into your opponent's deck."""
    shuffle_back(state, other_player(unit.owner), ["cuckoo_egg"] * state.config.cuckoo_eggs, by=unit.owner)


def _cuckoo_egg_drawn(state, inst):
    """Cuckoo Egg: when you draw this, your opponent draws a card."""
    draw_cards(state, other_player(inst.owner), 1)


def _opossum_place(state, unit, cr):
    """Roar: return an adjacent ally to your hand."""
    _push_choose(state, unit.owner, _adjacent_friendly_units(state, unit, cr), "return_ally")


def _andean_condor_place(state, unit, cr):
    o = unit.owner
    mine, theirs = state.decks[o], state.decks[other_player(o)]
    if not mine:
        return                                           # empty own deck: fizzle
    their_str = _base_int(state, theirs[-1]) if theirs else 0
    if _base_int(state, mine[-1]) > their_str:           # strictly greater printed base (F13)
        _push_draw(state, o, 1)


def _base_int(state, card_id):
    b = state.cards[card_id].base_strength
    return b if isinstance(b, int) else 0


# --- Reserve and test fixtures ----------------------------------------------------------------------------------

def _mock_saboteur_place(state, unit, cr):
    # Baseline yardstick card: bare random hand-disruption (Black Swan's seeded discard, so it stays honest).
    hand = state.hands[other_player(unit.owner)]
    if hand:
        remove_from_hand(state, other_player(unit.owner), state.rng.choice(hand))


OPS.update({
    "rat_discard": _op_rat_discard,
    "hornet_kill": _op_hornet_kill,
    "pestis_wipe": _op_pestis_wipe,
    "bounce_iid": _op_bounce_iid,
    "skunk_bounce": _op_skunk_bounce,
    "venom": _op_venom,
    "magpie_steal": _op_magpie_steal,
})


def _spikes_covered(state, covered, coverer, cr):
    # Spikes (Porcupine, Hedgehog, the legendary Honey Badger): the first time an enemy covers this, remove that enemy.
    # Once per instance (`retaliation_used` persists across turns, and the board's badge goes with it).
    if coverer.owner == covered.owner or covered.retaliation_used:
        return
    covered.retaliation_used = True
    if statics.can_be_removed(state, coverer, cr):
        state.effect_stack.append(remove_iid_step(coverer.iid, by_player=covered.owner, by_effect=True,
                                                  source_iid=None, by_card=covered.card_id))


def _poison_covered(state, covered, coverer):
    """Poison (keywords.md): an enemy that covers this is removed at the start of this animal's controller's next
    turn, every time. Like King Cobra's venom (overview.md §9.1) the poison belongs to the coverer: it is queued on the
    coverer's iid, ticks while the coverer is buried, resolves whether or not the Poison animal is still there, and is
    cancelled only if the coverer leaves the board first (a bounce or a return gives it a new iid). It's a remove, so
    Armor resists it. An Apex Predator landing here is poisoned and still eats."""
    if coverer.owner == covered.owner:
        return
    state.scheduled.append({"iid": coverer.iid, "owner": covered.owner, "remaining": 1, "while_buried": True,
                            "step": remove_iid_step(coverer.iid, by_player=covered.owner, by_effect=True,
                                                    source_iid=None, by_card=covered.card_id)})
    state.emit("poisoned", iid=coverer.iid, card=coverer.card_id, owner=coverer.owner, by=covered.iid)


_draw1 = _draws()
_draw_test = _draws("test_draw")


def _calib_removal(max_attr=None, min_attr=None):
    return {"on_place": _removes(max_attr, min_attr)}


EFFECTS: dict[str, dict[str, Callable]] = {
    # Aristocrats.
    "aristocrats_legend_cuckoo": {"on_place": _cuckoo_legend_place},
    "ember": {"on_remove": _ember_remove},
    "aristocrats_legend_opossum": {"on_ally_covered": _opossum_legend_ally_covered},
    "praying_mantis": {"on_place": _mantis_place},
    "tarantula": {"on_end_of_turn": _tarantula_eot},
    "sea_turtle": {"on_end_of_turn": _sea_turtle_eot},
    "raccoon": {"on_place": _raccoon_place},
    "piranha": {"on_place": _conditional(_removes())},
    "hyena": {"on_end_of_turn": _hyena_eot},
    "vulture": {"on_end_of_turn": _vulture_eot},
    "city_spider": {"on_animal_placed_adjacent": _city_spider_trap},
    "earthworm": {"on_remove": _earthworm_remove},
    "worm": {"on_remove": _worm_remove},
    "cockroach": {"on_remove": _cockroach_remove},
    # Canines (Clarion's free roam and Dhole's equal roams are statics).
    "lobo": {"on_friendly_roam": _lobo_friendly_roam},
    "canines_legend_wolf": {"on_roam": _wolf_legend_roam},
    "african_wild_dog": {"on_cover_enemy": _awd_cover},
    "gray_wolf": {"on_place": _jackal_place},
    "bush_dog": {"on_place": _bush_dog_place},
    "raccoon_dog": {"on_friendly_roam": _raccoon_dog_friendly_roam},
    "fox": {"on_end_of_turn": _fox_eot},
    "badger": {"on_place": _draws_filtered("keyword:Roam")},
    "dog": {"on_place": _stray_dog_place},
    # Cats (King Theron fires from _fire_cover_event; Leopard is a static).
    "prince_leo": {"on_place": _twin_place("princess_lea")},
    "princess_lea": {"on_place": _twin_place("prince_leo")},
    "queen_adira": {"on_remove_event": _queen_adira_remove_event},
    "jaguar": {"on_place": _removes("jaguar_max")},
    "serval": {"on_place": _serval_place},
    "lynx": {"on_place_onto_enemy": _draw1},
    "bobcat": {"on_place": _conditional(_draw1)},
    "house_cat": {"on_place": _house_cat_place},
    # Colony.
    "queen_marabunta": {"on_place": _queen_marabunta_place},
    "queen_honoria": {"on_friendly_play": _queen_honoria_friendly_play},
    "nurse_bee": {"on_place": _conditional(_draws("nurse_bee_draw"))},
    "nurse_bumblebee": {"on_place": _conditional(_draws("nurse_bumblebee_draw"))},
    "termite_king": {"on_place": _conditional(_draw1)},
    "termite_queen": {"on_place": lambda state, unit, cr: _push_play_extra(
        state, unit.owner, filter={"tags_all": ["Colony"], "tags_none": ["Queen"]}, optional=True)},
    "queen_bee": {"on_place": lambda state, unit, cr: _push_play_extra(state, unit.owner,
                                                                      filter={"tags_all": ["Worker"]})},
    "soldier_ant": {"on_place": _conditional(_removes())},
    "worker_ant": {"on_place": _gains("worker_ant_food")},
    "worker_wasp": {"on_end_of_turn": _gains("worker_wasp_food")},
    "worker_bee": {"on_place": _worker_bee_place},
    # Den Rush.
    "greywhisker": {"on_place": _greywhisker_place},
    "pestis": {"on_place": _pestis_place},
    "sirocco": {"on_place": _sirocco_place},
    "gale": {"on_place": _gale_place},
    "naked_mole_rat": {"on_place": _naked_mole_rat_place},
    "hornet": {"on_place": _hornet_place},
    "skunk": {"on_place": _skunk_place},
    "hare": {"on_place": _conditional(_draw1)},
    "cheetah": {"on_place": _hq_adjacent_draw},
    "rat": {"on_place": _rat_place},
    "falcon": {"on_place": _hq_adjacent_draw},
    "bat": {"on_place": _draw1},
    "mouse": {"on_place": _draws_filtered("tag:Rodent")},
    # Egg Control.
    "eon": {"on_end_of_turn": _eon_end_of_turn},
    "egg_control_legend_raven": {"on_place": _raven_legend_place},
    "aurum": {"on_start_of_turn": _aurum_start},
    "omen": {"on_draw": _omen_drawn},
    "stoop": {"on_place": _removes("stoop_max")},
    "king_cobra": {"on_place": _king_cobra_place},
    "magpie": {"on_place": _magpie_place},
    "black_mamba": {"on_place": _removes("black_mamba_max")},
    "mosquito": {"on_place": _mosquito_place},
    "raven": {"on_place": _raven_place},
    "bird_egg": {"on_place": _bird_egg_place},
    "snake_egg": {"on_place": _snake_egg_place},
    # Fish (Mackerel and Tuna are anthems; the legendary Jellyfish an aura; the legendary Piranha a static).
    "fish_legend_tuna": {"on_place": _tuna_legend_place},
    "fish_legend_manta_ray": {"on_end_of_turn": _manta_legend_eot},
    "swordfish": {"on_place": _swordfish_place},
    "barracuda": {"on_place": _barracuda_place},
    "manta_ray": {"on_ally_covered": _manta_ally_covered},
    "remora": {"on_place": _remora_place},
    "cod": {"on_place": _cod_place},
    "sardine": {"on_place": _fill},
    "mahi_mahi": {"on_place": _mahi_mahi_place},
    "sunfish": {"on_place": _sunfish_place},
    # Food Aggro.
    "food_aggro_legend_repeat": {"on_place": _repeat_legend_place},
    "food_aggro_legend_refill": {"on_place": _refill_legend_place},
    "rat_king": {"on_place": _rat_king_place},
    "scrooge": {"on_place": _scrooge_place},
    "flying_squirrel": {"on_place": _gains("flying_squirrel_food")},
    "meerkat": {"on_place": _draw1, "on_enemy_placed_adjacent": _meerkat_enemy_placed},
    "chipmunk": {"on_place": _chipmunk_place},
    "dormouse": {"on_end_of_turn": _dormouse_eot},
    "squirrel": {"on_place": _gains("squirrel_food")},
    "hamster": {"on_place": _hamster_place},
    "gopher": {"on_place": _conditional(_draws("gopher_draw"))},
    "muskrat": {"on_place": _conditional(_removes())},
    "groundhog": {"on_place": _conditional(_gains("groundhog_food"))},
    "mole": {"on_place": _mole_place},
    # Food OTK (the legendary Honey Badger is its keywords; Capybara an aura; Armadillo too).
    "fathom": {"on_place": _fathom_place},
    "food_otk_legend_squirrel": {"on_place": _otk_squirrel_place},
    "food_otk_legend_octopus": {"on_place": _mimic_place},
    "golden_orb_weaver": {"on_enemy_placed_adjacent": _orb_weaver_enemy_placed},
    "hedgehog": {"on_place": _gains("hedgehog_food")},
    "black_bear": {"on_place": _black_bear_place},
    "tortoise": {"on_place": _tortoise_place},
    "owl": {"on_place": _owl_place},
    # Giants (Hungry and Titan are keywords; the legendary Oxpecker feeds its neighbours in _eat).
    "bulwark": {"on_place": _remove_all_adjacent},
    "methuselah": {"on_end_of_turn": _methuselah_eot},
    "mocha": {"on_place": _mocha_place},
    "rhinoceros": {"on_place": _rhinoceros_place},
    "hippopotamus": {"on_enemy_placed_adjacent": _hippo_enemy_placed},
    "whale_shark": {"on_end_of_turn": _draws("whale_shark_draw")},
    "oxpecker": {"on_place": _oxpecker_place},
    "anteater": {"on_place": _anteater_place},
    "dung_beetle": {"on_end_of_turn": _dung_beetle_eot},
    "sloth": {"on_place": _sloth_place},
    # Handlock (Grizzly Bear is an anthem; the Eagles' sharing lives in _gain_in_hand, the mate in state.ensure_mates).
    "handlock_legend_baboon": {"on_end_of_turn": _baboon_legend_eot},
    "silverback": {"on_place": _silverback_place},
    "handlock_legend_butterfly": {"on_gain_in_hand": _butterfly_evolve},
    "handlock_legend_butterfly_2": {"on_place": _draw1, "on_gain_in_hand": _butterfly_evolve},
    "handlock_legend_butterfly_3": {"on_place": _draw_then_give_one, "on_gain_in_hand": _butterfly_evolve},
    "handlock_legend_butterfly_4": {"on_place": _butterfly_stage_place(None, "butterfly_legend_stage4_grant"),
                                    "on_gain_in_hand": _butterfly_evolve},
    "handlock_legend_butterfly_5": {"on_place": _butterfly_stage_place("butterfly_legend_stage5_draw",
                                                                       "butterfly_legend_stage5_grant")},
    "hummingbird": {"on_place": _draws("hummingbird_draw")},
    "macaque": {"on_place": _macaque_place},
    "orangutan": {"on_place": _orangutan_place},
    "tarsier": {"on_place": _tarsier_place},
    "chimpanzee": {"on_place": _chimpanzee_place},
    "baboon": {"on_place": _baboon_place},
    "stork": {"on_place": _stork_place},
    "caterpillar": {"on_gain_in_hand": _caterpillar_grows},
    "gorilla": {"on_place": _gorilla_place},
    # Hoofed (the legendary Wildebeest and Boar change region income; the legendary Giraffe reveals; Moose, Giraffe and
    # Boar are anthems).
    "hoofed_legend_zebra": {"on_place": _zebra_legend_place},
    "honey_badger": {"on_place": _removes(min_attr="honey_badger_min")},
    "okapi": {"on_end_of_turn": _okapi_eot},
    "zebra": {"on_flee": _zebra_flee},
    "cape_buffalo": {"on_place": _cape_buffalo_place},
    "gazelle": {"on_place": _gains("gazelle_food")},
    "wildebeest": {"on_end_of_turn": _wildebeest_eot},
    "deer": {"on_place": _draws_filtered("tag:Hoofed")},
    # The pool (Great White Shark's Reach is a static; Raksha, Verminus are anthems; Coyote, Cougar statics).
    "octopus": {"on_place": _octopus_ink_place},
    "macaw": {"on_place": _macaw_place},
    "sperm_whale": {"on_place": _remove_all_adjacent},
    "butterfly": {"on_place": _draw_then_give_one},
    "cuckoo": {"on_place": _cuckoo_place},
    "cuckoo_egg": {"on_draw": _cuckoo_egg_drawn},
    "opossum": {"on_place": _opossum_place},
    "alpha": {"on_place": _alpha_place},
    "viper": {"on_place": _viper_place},
    "lemming": {"on_place": _fill},
    "andean_condor": {"on_place": _andean_condor_place},
    "dingo": {"on_end_of_turn": _dingo_eot},
    # The tutorial's own cards, as they were when it was written.
    "tutorial_lynx": {"on_place": _conditional(_draw1)},
    "tutorial_chipmunk": {"on_place": _hamster_place},
    # Reserve designs and the sim tools' calibration bodies.
    "eon_food_engine": {"on_draw_event": _eon_event, "on_shuffle_event": _eon_event, "on_remove_event": _eon_event},
    "unnamed_canine": {"on_place": _unnamed_canine_place},
    "shuck": {"on_place": _shuck_place},
    "mock_scout": {"on_place": _draw1},
    "mock_courier": {"on_place": _draw1},
    "mock_saboteur": {"on_place": _mock_saboteur_place},
    "mock_draw2": {"on_place": _draw_test},
    "mock_skully": {"on_place": _draw_test},
    "mock_removal": {"on_place": _removes()},
    "mock_sentry": {"on_place": _removes("stoop_max")},
    "mock_hunter": {"on_place": _removes("calib_rm4_max")},
    **{f"mock_draw_{n}": {"on_place": _draw1} for n in (3, 4, 6, 7)},
    **{f"mock_flydraw_{n}": {"on_place": _draw1} for n in (2, 3, 4, 5)},
    **{f"calib_draw1_{n}": {"on_place": _draw1} for n in (1, 2)},
    **{f"calib_draw2_{n}": {"on_place": _draw_test} for n in (0, 1, 2, 3)},
    **{f"calib_rm3_{n}": _calib_removal("stoop_max") for n in (2, 3, 4, 5, 6)},
    **{f"calib_rm4_{n}": _calib_removal("calib_rm4_max") for n in (2, 3, 4, 5, 6)},
    **{f"calib_rm6_{n}": _calib_removal(min_attr="calib_rm6_min") for n in (1, 2, 3, 4, 5)},
    **{f"calib_rmany_{n}": _calib_removal() for n in (1, 2, 3, 4, 5)},
    **{f"calib_extra_{n}": {"on_place": lambda state, unit, cr: _push_play_extra(state, unit.owner)}
       for n in (1, 2, 3, 4, 5)},
    **{f"calib_food10_{n}": {"on_place": _gains("squirrel_food")} for n in (2, 3, 4, 5, 6)},
    **{f"calib_food3t_{n}": {"on_end_of_turn": _gains("worker_wasp_food")} for n in (2, 3, 4, 5, 6)},
}
