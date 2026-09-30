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


# ================================================================== mulligan

def _op_mulligan(state, step):
    """Gwent-style blacklist mulligan (overview.md §4.4): each returned card is replaced at once by
    the top deck card that is no copy of anything returned so far, up to `mulligan_max` returns
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
                hand.append(UnitInstance(deck.pop(i), player, state.new_iid()))
    if not done and hand and len(returned) < state.config.mulligan_max and _mulligan_replacement(deck, returned) is not None:
        return PendingRequest("choice", player, optional=True, kind="mulligan", options=[u.iid for u in hand])
    if returned:                      # a kept hand leaves the deck order (and the RNG) untouched
        deck.extend(returned)
        state.rng.shuffle(deck)
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
    state.hands[player].remove(unit)
    cost = state.cards[card_id].food_cost          # "Costs X food" (decision F): paid on placement
    if cost:
        state.food[player] -= cost
    state.units_placed_this_turn += 1
    kind, where = target
    if kind == "hq":
        state.result = Result(player, "hq_capture")
        return
    _land_unit(state, player, unit, where)


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


def _land_unit(state: GameState, player: str, unit: UnitInstance, cr: str) -> None:
    # The same hand instance lands on the board, carrying its strength counter.
    covered = state.top_unit(cr)
    is_apex = "Apex Predator" in state.cards[unit.card_id].keywords
    onto_enemy = covered is not None and covered.owner != player
    cover_enemy = covered if onto_enemy else None     # King Theron watches enemy covers

    unit.placed_on_turn = state.turn_counter
    state.board.setdefault(cr, []).append(unit)

    # Apex Predator: it covers the occupant like any placement, and eats it afterwards
    # (Martin, 2026-09-29): the roar, then every reaction to the cover (Porcupine's spines,
    # Gale), then the eat. The stack is LIFO, so the eat goes in first, at the bottom.
    if is_apex and covered is not None:
        state.effect_stack.append({"op": "apex_eat", "iid": unit.iid, "prey": covered.iid})

    # Reactive triggers resolve AFTER the placed unit's roar (decision 8). The stack
    # is LIFO, so push reactive first (lower) and the roar last (on top).
    _push_reactions(state, unit, cr, covered, onto_enemy)
    if cover_enemy is not None:
        _fire_cover_event(state, unit, cover_enemy)
    _fire_play_event(state, unit)        # Queen Honoria: gain food when you play a Colony unit
    _push_hook(state, unit, cr, "on_place")
    if onto_enemy:
        _push_hook(state, unit, cr, "on_place_onto_enemy")
    # Recorded last so a Rodent's own placement can't satisfy its own "last turn" check (Gopher).
    _track_rodent_play(state, unit)


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
    """Fire ON_FRIENDLY_PLAY reactors for a unit its controller just played or spawned
    (Queen Honoria's food, Dhole's on-enter buff). The played unit itself is skipped."""
    for st in state.board.values():
        top = st[-1] if st else None
        if not (top and top.owner == played.owner and top.iid != played.iid):
            continue
        hook = _hook(state, top.card_id, "on_friendly_play")
        if hook is not None:
            hook(state, top, played)


def _queen_honoria_friendly_play(state, watcher, played) -> None:
    if "Colony" in state.cards[played.card_id].tags and not _capped(state, "cap_queen_honoria", watcher):
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
    # Only the physics gate lives here (Armor blocks any effect-removal, whoever chose
    # it). Stealth is a *choice* restriction, enforced where enemy option lists are built
    # (and at the Apex eat), never at resolution - so mass/random/automatic removals
    # (Pestis, Rhino/Brutus, Grizzly, Hippo, King Theron, Pufferfish) hit Stealth units.
    if by_effect and not statics.can_be_removed(state, unit):
        return False
    was_top = stack[-1] is unit
    stack.remove(unit)
    # A unit uncovered by this very removal was buried when it happened, so it doesn't react to it.
    uncovered = stack[-1] if was_top and stack else None
    if not stack:
        del state.board[cr]
    entered_pile = _dispose(state, unit)
    if entered_pile:                        # the remove trigger fires first (F9), then...
        _fire_remove_event(state, unit.card_id, unit.owner, cr, by_player, by_card, uncovered)
    _fire_on_remove(state, unit)            # ...the unit's own Deathrattle (e.g. Ember relocates)
    return True


def remove_top(state, cr, *, by_player, by_effect=True, by_card=None) -> bool:
    top = state.top_unit(cr)
    if top is None:
        return False
    return _remove_specific(state, cr, top, by_player=by_player, by_effect=by_effect, by_card=by_card)


def _op_apex_eat(state, step):
    """An Apex eats what it covered, if both are still there, the prey is right beneath it,
    and it can be eaten (not Armor; not an enemy with Stealth, since the eat is a chosen single-out)."""
    cr, apex = _find_unit(state, step["iid"])
    if apex is None:
        return None
    stack = state.board[cr]
    i = stack.index(apex)
    prey = stack[i - 1] if i > 0 else None
    if prey is not None and prey.iid == step["prey"] and statics.can_be_chosen(state, prey, apex.owner):
        _remove_specific(state, cr, prey, by_player=apex.owner, by_card=apex.card_id)
    return None


def _find_unit(state, iid):
    for cr, stack in state.board.items():
        for u in stack:
            if u.iid == iid:
                return cr, u
    return None, None


def _fire_on_remove(state, unit) -> None:
    # A unit leaving the board: its own Deathrattle. (Board-wide reactors to removal events -
    # Vulture/Eon/Unnamed Scavenger/Egg Eater - are wired in Stage 2.2's event engine.)
    hook = _hook(state, unit.card_id, "on_remove")
    if hook:
        hook(state, unit)


def _food_gained_this_turn(state: GameState, player: str) -> int:
    """Food `player` has gained since the start of their current turn (turn_flags reset each
    turn end). Powers the food_otk signature cards: Scrooge / Hamster / Muskrat / Groundhog."""
    return state.turn_flags.get(f"food_gained_{player}", 0)


def _fed_this_turn(state: GameState, player: str) -> bool:
    return _food_gained_this_turn(state, player) >= state.config.fed_threshold


def _played_rodent_last_turn(state: GameState, player: str) -> bool:
    """True iff `player` placed a Rodent on their own turn immediately before this one
    (Rodent-last-turn payoff cards, e.g. Gopher). Turns alternate one `turn_counter` tick per
    single-player turn, so "my last turn" is always exactly turn_counter - 2. We check set
    membership rather than a single latest turn: in a go-wide Rodent deck the player usually
    places another Rodent *this* turn before Gopher, and a scalar "last turn placed" would be
    overwritten by that same-turn play and wrongly disarm Gopher. Tracked directly in
    `state.rodent_played_turns` (not state.scheduled/turn_flags): GreedyBot's eval credits *any*
    entry on state.scheduled as a generic future payoff, so routing this bookkeeping through the
    delayed-effect queue would silently overvalue every Rodent placement."""
    return (state.turn_counter - 2) in state.rodent_played_turns.get(player, ())


def _track_rodent_play(state: GameState, unit: UnitInstance) -> None:
    """Record the turn a Rodent was placed, for `_played_rodent_last_turn` above."""
    if "Rodent" in state.cards[unit.card_id].tags:
        state.rodent_played_turns.setdefault(unit.owner, set()).add(state.turn_counter)


def gain_food(state: GameState, player: str, amount: int, *, rider: bool = True) -> None:
    if amount <= 0:
        return
    state.food[player] += amount
    state.turn_flags[f"food_gained_{player}"] = _food_gained_this_turn(state, player) + amount
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
    if card_ids:
        state.turn_flags[f"shuffled_{player}"] = True     # King Cobra: "if you shuffled a card this turn"
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
    """
    kind, _, val = spec.partition(":")
    if kind == "tag":
        return val in card.tags
    if kind == "rarity":
        return card.rarity == val
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
    for card_id in sorted(best):
        placer = best[card_id]
        card = state.cards[card_id]
        if card.food_cost > state.food[player]:
            continue                                  # "Costs X food": only if affordable (dec. F)
        is_apex = "Apex Predator" in card.keywords
        flight = statics.ignores_connection(state, card_id)
        extra = statics.extra_placement_crossroads(state, card_id, player)
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
    an apex Cat land at equal strength. If the occupant is eat-eligible it gets eaten; if not (Armor / enemy
    Stealth) it is simply covered (see _land_unit)."""
    if top.owner == placer.owner:
        return True
    return statics.can_cover(state, placer, top)


# ============================================================= delayed scheduler

def schedule(state: GameState, unit, owner_turn_delay: int, step: dict) -> None:
    """Queue `step` to fire after `owner_turn_delay` more of `unit`'s owner's turns.

    The timer belongs to the **unit**, not the board (rules `overview.md` §9.1): it advances only
    while `unit` is the top of its crossroad, and is cancelled outright if `unit` leaves the board.
    A bounced unit re-enters play as a fresh instance with a new iid, so replaying it starts a new
    timer rather than resuming this one - "bounce resets".
    """
    state.scheduled.append({"iid": unit.iid, "owner": unit.owner,
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
        elif s["iid"] not in tops and not s.get("while_buried"):
            keep.append(s)                 # buried: suspended, does not tick (§9.1)
        else:
            s["remaining"] -= 1
            (fired if s["remaining"] <= 0 else keep).append(s)
    state.scheduled = keep
    for s in reversed(fired):  # earliest-scheduled ends on top of the stack -> resolves first
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
        return None  # egg already gone (removed before it hatched) - no payoff
    _remove_specific(state, cr, egg, by_player=egg.owner, by_effect=False)
    draw_filtered_random(state, egg.owner, step["n"], step["spec"])
    return None


def _op_raven_dig(state, step):
    player = step["player"]
    if "remaining" not in step:
        draw_cards(state, player, 3)                 # draw 3 (fires ON_DRAW), then...
        step["remaining"] = min(2, len(state.hands[player]))
        step["shuffled"] = []

    if "choice" in step:
        iid = step.pop("choice")
        inst = next((u for u in state.hands[player] if u.iid == iid), None)
        if inst is not None:
            state.hands[player].remove(inst)
            step["shuffled"].append(inst.card_id)
            step["remaining"] -= 1

    if step["remaining"] > 0 and state.hands[player]:
        options = [u.iid for u in state.hands[player]]
        if len(options) == 1:
            step["choice"] = options[0]
            return _op_raven_dig(state, step)
        return PendingRequest("choice", player, options=options, from_deck_reveal=True)

    if step["shuffled"]:
        shuffle_back(state, player, step["shuffled"])
    return None


def _op_scout(state, step):
    """Scout: look at `scout_count` cards of your deck, draw one (chosen), shuffle the rest back.
    Unfiltered (Owl) it looks at the top of the deck; with a `spec` (a Bird, a legendary unit) it
    looks at that many random matching cards. Nothing matching: nothing happens."""
    player = step["player"]
    if "pulled" not in step:
        deck = state.decks[player]
        n = state.config.scout_count
        if step.get("spec") is None:
            pulled = [deck.pop() for _ in range(min(n, len(deck)))]  # top of deck = end
        else:
            matching = [i for i, cid in enumerate(deck) if _matches(state.cards[cid], step["spec"])]
            picks = sorted(state.rng.sample(matching, min(n, len(matching))), reverse=True)
            pulled = [deck.pop(i) for i in picks]
        if not pulled:
            return None
        step["pulled"] = pulled
        if len(set(pulled)) == 1:
            step["choice"] = pulled[0]
        else:
            return PendingRequest("choice", player, options=sorted(set(pulled)),
                                  from_deck_reveal=True)
    pulled = list(step["pulled"])
    pulled.remove(step["choice"])
    inst = UnitInstance(step["choice"], player, state.new_iid())
    state.hands[player].append(inst)
    _fire_draw(state, [inst])
    shuffle_back(state, player, pulled)
    return None


def _op_bird_egg_hatch(state, step):
    cr, egg = _find_unit(state, step["iid"])
    if egg is None:
        return None  # removed before it hatched - no payoff
    _remove_specific(state, cr, egg, by_player=egg.owner, by_effect=False)
    state.effect_stack.append({"op": "scout", "player": egg.owner, "spec": "tag:Bird"})
    return None


def _op_remove_choice(state, step):
    """Remove the top unit at a chosen crossroad among `options`."""
    options = step["options"]
    if not options:
        return None
    if "choice" not in step:   # asked even with one target: the player clicks what the Roar hits
        return PendingRequest("choice", step["chooser"], optional=step.get("optional", False), options=options)
    chosen = step["choice"]
    if chosen == SKIP:
        return None
    remove_top(state, chosen, by_player=step["by_player"], by_card=step.get("by_card"))
    return None


def _op_remove_iid(state, step):
    # A reactive removal may name the unit that triggered it (`source_iid`). If that source
    # has since left the board - e.g. a fed Muskrat's roar removed the Hippo before the
    # Hippo's queued reaction resolves (decision: reactions fizzle when their source is gone) -
    # the removal fizzles rather than firing from a dead trigger.
    src = step.get("source_iid")
    if src is not None and _find_unit(state, src)[1] is None:
        return None
    cr, unit = _find_unit(state, step["iid"])
    if unit is not None:
        _remove_specific(state, cr, unit, by_player=step.get("by_player", unit.owner),
                         by_effect=step.get("by_effect", True), by_card=step.get("by_card"))
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
    allowed = _hand_allowed(state, step["chooser"], step.get("filter", {}))
    placements = legal_placements(state, step["chooser"], allowed)
    if not placements:
        return None
    return PendingRequest("place", step["chooser"], optional=step.get("optional", False),
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
        if amount > 0 and _crossroad_of(state, iid) is not None:
            _fire_on_gain_strength(state, inst)
    return None


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
    # The per-unit once-per-turn flag doubles as the grant->gain->grant loop guard for granting
    # reactors (Bush Dog). Fox only draws (no grant, so no loop) and now fires on every distinct
    # buff — its printed "once per turn" clause was dropped 2026-07-05 (config.fox_gain_once restores it).
    if not (unit.card_id == "fox" and not state.config.fox_gain_once):
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
    hides from its own controller; Armor blocks its own controller's sacrifices too
    (decision A2: that's the keyword's cost - e.g. Carmilla can't eat a Scrooge)."""
    out = []
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if (top and top.owner == unit.owner
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


def _unnamed_canine_place(state, unit, cr):
    if effective_strength(state, unit) >= state.config.unnamed_canine_draw_threshold:
        state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1})


def _clarion_place(state, unit, cr):
    # Give +2 to all OTHER friendly Canines on the board (board-only, 2026-07-05 rework).
    iids = [u.iid for st in state.board.values() for u in st
            if u.owner == unit.owner and u.iid != unit.iid and "Canine" in state.cards[u.card_id].tags]
    _grant(state, iids, state.config.clarion_grant)


def _red_wolf_friendly_play(state, watcher, played):
    # Whenever another Canine you control enters play (played or spawned), give it +2 strength.
    if "Canine" in state.cards[played.card_id].tags:
        _grant(state, [played.iid], state.config.red_wolf_grant)


def _spawn_pups(state, unit, cr, n, token_ids=("pup",)):
    """Land up to `n` tokens on random empty crossroads adjacent to `cr`, cycling through
    `token_ids`. They enter via the
    normal landing path (so Dhole's on-enter buff sees them) but carry no Roar, so there
    is no spawn recursion."""
    empty = [nb for nb in state.game_map.neighbors(cr) if not state.board.get(nb)]
    state.rng.shuffle(empty)
    for i, spot in enumerate(empty[:n]):
        pup = UnitInstance(token_ids[i % len(token_ids)], unit.owner, state.new_iid())
        _land_unit(state, unit.owner, pup, spot)


def _alpha_place(state, unit, cr):
    _spawn_pups(state, unit, cr, state.config.alpha_pups, ("poppy", "rusty"))


def _african_wild_dog_place(state, unit, cr):
    _spawn_pups(state, unit, cr, state.config.awd_pups)


def _hyena_place(state, unit, cr):
    # Remove an adjacent enemy of strength <= the number of Canines you control (Hyena included).
    cap = _control_tag_count(state, unit.owner, "Canine")
    targets = _adjacent_enemy_targets(state, unit, cr, max_strength=cap)
    if targets:
        _push_remove_choice(state, unit.owner, "hyena", targets)


def _dingo_end_of_turn(state, unit, cr):
    # Give +1 to every friendly adjacent Canine.
    iids = _friendly_adjacent_canine_iids(state, unit, cr)
    if iids:
        _grant(state, iids, state.config.dingo_grant)


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
    # Remove the coverer, then the pufferfish (both pushed; coverer resolves first). Draw
    # added 2026-07-04 OTK-lean pass (the trap so rarely fires against a competent opponent
    # that its payoff needed raising, not its trigger rate) - pushed first, resolves last.
    state.effect_stack.append({"op": "draw", "player": covered.owner, "n": 1})
    state.effect_stack.append(
        {"op": "remove_iid", "iid": covered.iid, "by_player": covered.owner, "by_effect": False})
    state.effect_stack.append(
        {"op": "remove_iid", "iid": coverer.iid, "by_player": covered.owner, "by_effect": True})


# --- Egg Control deck: draw/shuffle/remove food engine + filtered draws (Stage 2.2) ---

def _eon_event(state, unit, cr, event):           # any draw/shuffle/remove -> +1
    if not _capped(state, "cap_eon", unit):
        gain_food(state, unit.owner, state.config.eon_food)


def _vulture_remove_event(state, unit, cr, event):  # any card removed -> +5
    if not _capped(state, "cap_vulture", unit):
        gain_food(state, unit.owner, state.config.vulture_food)


def _rattlesnake_shuffle_event(state, event):
    """Each copy grows on its owner's shuffle, including copies still in the deck."""
    player = event["player"]
    if _owns_copy(state, player, "rattlesnake"):
        counters = state.card_strength_counters.setdefault(player, {})
        counters["rattlesnake"] = counters.get("rattlesnake", 0) + 1


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
    # Hard, printed-text cap (not a Config dial - card-balance-todo's legendary redesign):
    # "the first time each turn you draw Black Swan". Keyed by owner, not iid: a reshuffled
    # redraw gets a fresh UnitInstance/iid, so the cap must survive across instances.
    key = f"omen_turn_cap_{inst.owner}"
    if state.turn_flags.get(key):
        return
    state.turn_flags[key] = True
    # The opponent removes a random card (seeded; a remove, not a Deathrattle).
    opponent = other_player(inst.owner)
    hand = state.hands[opponent]
    if hand:
        remove_from_hand(state, opponent, state.rng.choice(hand))


def _owl_place(state, unit, cr):
    state.effect_stack.append({"op": "scout", "player": unit.owner})


def _raven_place(state, unit, cr):
    state.effect_stack.append({"op": "raven_dig", "player": unit.owner})


def _ember_remove(state, unit):
    # Deathrattle: shuffle Ember back into its owner's deck (it is already in the Remove Pile).
    if "ember" in state.remove_pile:
        state.remove_pile.remove("ember")
        shuffle_back(state, unit.owner, ["ember"])


def _enemy_neighbors(state, unit, cr):
    """Adjacent crossroads topped by an enemy unit this player may choose (Stealth hides)."""
    return [nb for nb in sorted(state.game_map.neighbors(cr))
            if (top := state.top_unit(nb)) and top.owner != unit.owner
            and statics.can_be_chosen(state, top, unit.owner)]


def _viper_place(state, unit, cr):
    targets = _enemy_neighbors(state, unit, cr)
    if targets:
        state.effect_stack.append({"op": "venom", "kind": "viper", "chooser": unit.owner,
                                   "options": targets})


def _taipan_place(state, unit, cr):
    targets = _adjacent_enemy_targets(state, unit, cr)
    if targets:
        state.effect_stack.append({"op": "venom", "kind": "taipan", "chooser": unit.owner,
                                   "options": targets})


def _op_venom(state, step):
    """Viper: the chosen adjacent enemy gets -3 strength, permanently. Taipan: the chosen
    adjacent enemy is removed at the start of the Taipan owner's next turn. The venom is on the
    bitten unit, not on the snake (rules §9.1 exception): it resolves even if the Taipan is gone
    or the bitten unit is buried, and is cancelled only if the bitten unit leaves the board."""
    options = step["options"]
    if "choice" not in step:   # asked even with one target
        return PendingRequest("choice", step["chooser"], options=options)
    target = state.top_unit(step["choice"])
    if target is None:
        return None
    if step["kind"] == "viper":
        target.strength_counter -= state.config.viper_poison
    else:
        state.scheduled.append({"iid": target.iid, "owner": step["chooser"], "remaining": 1,
                                "while_buried": True,
                                "step": {"op": "remove_iid", "iid": target.iid,
                                         "by_player": step["chooser"], "by_card": "taipan"}})
    return None


def _black_mamba_place(state, unit, cr):
    _push_remove_choice(state, unit.owner, "black_mamba",
                        _adjacent_enemy_targets(state, unit, cr, max_strength=state.config.black_mamba_max))


def _eon_end_of_turn(state, unit, cr):
    # The Ouroboros: it leaves the board (a return, not a remove - no Deathrattle, nothing to
    # the Remove Pile) and shuffles into its owner's deck, a little smaller each cycle. The loss
    # is kept per card id, like Rattlesnake's growth, so it survives the trip through the deck.
    state.board[cr].remove(unit)
    if not state.board[cr]:
        del state.board[cr]
    counters = state.card_strength_counters.setdefault(unit.owner, {})
    counters["eon"] = counters.get("eon", 0) - state.config.eon_decay
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
            state.hands[player].append(UnitInstance(inst.card_id, player, state.new_iid()))
    hand = state.hands[player]
    if not hand:
        return None
    if "choice" not in step:
        if len(hand) == 1:
            step["choice"] = hand[0].iid
        else:
            return PendingRequest("choice", player, options=[u.iid for u in hand], from_deck_reveal=True)
    inst = next((u for u in hand if u.iid == step["choice"]), None)
    if inst is not None:
        remove_from_hand(state, player, inst)
    return None


def _mouse_place(state, unit, cr):
    state.effect_stack.append({"op": "draw_filtered", "player": unit.owner, "n": 1, "spec": "tag:Rodent"})


def _fathom_place(state, unit, cr):
    state.effect_stack.append({"op": "scout", "player": unit.owner, "spec": "rarity:legendary"})


def _bird_egg_place(state, unit, cr):
    state.effect_stack.append({"op": "scout", "player": unit.owner, "spec": "tag:Bird"})
    schedule(state, unit, state.config.bird_egg_hatch_delay,
             {"op": "bird_egg_hatch", "iid": unit.iid})


def _snake_egg_place(state, unit, cr):
    state.effect_stack.append({"op": "draw_filtered", "player": unit.owner,
                               "n": state.config.snake_egg_draw, "spec": "tag:Snake"})
    schedule(state, unit, state.config.egg_hatch_delay,
             {"op": "egg_hatch", "iid": unit.iid, "n": state.config.egg_hatch_draw, "spec": "tag:Snake"})


def _opossum_place(state, unit, cr):
    # Roar (its Deathrattle return is in _dispose); food added 2026-07-04 OTK-lean pass.
    _push_draw(state, unit.owner, 1)
    _push_gain(state, unit.owner, state.config.opossum_food)


def _gazelle_remove(state, unit):
    gain_food(state, unit.owner, state.config.gazelle_food)


def _impala_remove(state, unit):
    draw_cards(state, unit.owner, 2)


# --- Extra placements / HQ-adjacency / start-of-turn (Stage 2.3) ---

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
    # May chain into another House Cat now (self-exclusion dropped 2026-07-05).
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_play_extra(state, unit.owner, filter={"tags_all": ["Cat"]})


def _dog_place(state, unit, cr):
    # May chain into another Dog now (self-exclusion dropped 2026-07-05).
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_play_extra(state, unit.owner, filter={"tags_all": ["Canine"]})


def _queen_bee_place(state, unit, cr):
    _push_play_extra(state, unit.owner, filter={"tags_all": ["Worker"]})


def _termite_queen_place(state, unit, cr):
    _push_play_extra(state, unit.owner, filter={"tags_all": ["Colony"], "tags_none": ["Queen"]}, optional=True)


def _twin_place(twin_id):
    def handler(state, unit, cr):
        state.effect_stack.append({"op": "play_named", "chooser": unit.owner, "card_id": twin_id})
    return handler


def _gale_place(state, unit, cr):
    # "Roar: draw a card for each unit you control next to the opponent's den" (Gale included).
    front = state.game_map.hq_front(other_player(unit.owner))
    n = sum(1 for c in front if (top := state.top_unit(c)) and top.owner == unit.owner)
    if n:
        state.effect_stack.append({"op": "draw", "player": unit.owner, "n": n})


def _hq_adjacent_draw(state, unit, cr):
    if cr in state.game_map.hq_front(other_player(unit.owner)):  # next to the enemy base (F6)
        state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1})


def _aurum_start(state, unit, cr):
    state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1})


def _sloth_place(state, unit, cr):
    """"In 2 turns, gain 30 food." Deliberately NOT Armor.

    Its counterplay is the timed-effect rule (overview.md 9.1), not a keyword: cover the Sloth and
    the timer suspends for as long as the cover holds. Armor would make the payout
    unanswerable AND shadow Methuselah.
    """
    schedule(state, unit, state.config.sloth_delay,
             {"op": "gain_food", "player": unit.owner, "amount": state.config.sloth_food})


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
    Armor can't be moved by anyone; Stealth only hides from a `chosen` pick (Skunk),
    not from a mass bounce (Sirocco, `chosen=False`) - keyword-review decision B."""
    out = []
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if not (top and top.owner != unit.owner
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


def roar_condition(state, player, card_id, unit=None):
    """Whether the "if ..." of `card_id`'s Roar holds: None for a card with no such
    condition, or one that depends on where it lands (Caracal, Cheetah, Falcon). `unit` is the
    placed unit while its Roar resolves; None asks about the card in hand, as if it were
    played now (the client lights such cards up). The Roars below call this too, so the
    two can't disagree."""
    on_top = unit is not None and any(st and st[-1].iid == unit.iid for st in state.board.values())

    def others(*tags):          # friendly tops carrying `tags`, not counting this card
        n = _control_tag_count(state, player, *tags)
        return n - 1 if on_top and all(t in state.cards[card_id].tags for t in tags) else n
    colony_min = state.config.colony_synergy_threshold
    check = {
        "hamster": lambda: _fed_this_turn(state, player),
        "muskrat": lambda: _fed_this_turn(state, player),
        "groundhog": lambda: _fed_this_turn(state, player),
        "gopher": lambda: _played_rodent_last_turn(state, player),
        "lynx": lambda: others("Cat") >= 1,
        "house_cat": lambda: others("Cat") >= 1,
        "dog": lambda: others("Canine") >= 1,
        "worker_bee": lambda: others("Worker") >= 1,
        "termite_king": lambda: _control_tag_count(state, player, "Colony", "Queen") >= 1,
        "nurse_bumblebee": lambda: others("Colony") + 1 >= colony_min,
        "soldier_ant": lambda: others("Colony") + 1 >= colony_min,
        "nurse_bee": lambda: _controls_two_same_colony(state, player) or (unit is None and any(
            st and st[-1].owner == player and st[-1].card_id == card_id for st in state.board.values())),
    }.get(card_id)
    return check() if check else None


def _bounce(state, cr, top, *, lock_until=0):
    """Return a board unit to its owner's hand (not a removal: no Remove Pile, no triggers)."""
    state.board[cr].remove(top)
    if not state.board[cr]:
        del state.board[cr]
    state.add_to_hand(top.owner, top.card_id).locked_until_turn = lock_until


# --- Removal roars (Cats / Colony / Ramp) ---

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
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_remove_choice(state, unit.owner, "soldier_ant", _adjacent_enemy_targets(state, unit, cr))


def _rhinoceros_place(state, unit, cr):
    for nb in _adjacent_enemy_targets(state, unit, cr, max_strength=state.config.rhinoceros_max,
                                      chosen=False):        # mass AoE hits Stealth
        state.effect_stack.append({"op": "remove_iid", "iid": state.top_unit(nb).iid,
                                   "by_player": unit.owner, "by_card": "rhinoceros"})


def _bulwark_place(state, unit, cr):
    # Remove ALL adjacent units, friend and foe (2026-07-05 nerf: was enemies only). Automatic
    # mass effect, so it hits Stealth; Armor neighbours survive (can_be_removed).
    for nb in sorted(state.game_map.neighbors(cr)):
        top = state.top_unit(nb)
        if top and statics.can_be_removed(state, top):
            state.effect_stack.append({"op": "remove_iid", "iid": top.iid,
                                       "by_player": unit.owner, "by_card": "bulwark"})


def _hippo_enemy_placed(state, hippo, placed, cr):
    # Automatic trigger, nobody "chose" the target: Stealth doesn't hide (decision B).
    if (effective_strength(state, placed) <= state.config.hippopotamus_max
            and statics.can_be_removed(state, placed)):
        state.effect_stack.append({"op": "remove_iid", "iid": placed.iid,
                                   "by_player": hippo.owner, "by_card": "hippopotamus",
                                   "source_iid": hippo.iid})


# --- Hand-cost / friendly-sacrifice removal (Aggro / Food OTK) ---

def _rat_place(state, unit, cr):
    # "Remove an adjacent enemy unit, then remove a random card from your hand." The hand card
    # goes whether or not there was a target; an empty hand pays nothing (Doomguard-style).
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
    state.remove_pile.append(card_id)
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
    # Own sacrifices: Stealth never hides from its controller; Armor still refuses
    # (decision A2 - Carmilla/Black Widow can't eat a Tortoise or Scrooge).
    return sorted(
        c for c, st in state.board.items()
        if st[-1].owner == player
        and statics.can_be_removed(state, st[-1]))


# --- Mass effects (Aggro) ---

def _pestis_place(state, unit, cr):
    # "Remove an adjacent enemy and every unit buried under it": the target is a chosen enemy
    # (so Stealth and Armor tops are off limits, as for any removal), the whole stack goes.
    options = _adjacent_enemy_unit_crossroads(state, unit, cr)
    if options:
        state.effect_stack.append({"op": "pestis_wipe", "chooser": unit.owner, "options": options})


def _op_pestis_wipe(state, step):
    if "choice" not in step:   # asked even with one target
        return PendingRequest("choice", step["chooser"], options=step["options"])
    target = step["choice"]
    # Remove the entire stack under the enemy, both players' units, top-down. A buried
    # Armor unit is skipped in place, not a shield: everything else is still wiped around it.
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


def _spines_covered(state, covered, coverer, cr):
    # Porcupine, Hedgehog: "The first time an enemy covers this, remove that enemy." Once per
    # instance (`retaliation_used` persists across turns); after that it's an ordinary unit.
    if coverer.owner == covered.owner or covered.retaliation_used:
        return
    covered.retaliation_used = True
    if statics.can_be_removed(state, coverer):
        state.effect_stack.append({"op": "remove_iid", "iid": coverer.iid, "by_player": covered.owner,
                                   "by_card": covered.card_id})


def _skunk_place(state, unit, cr):
    options = _adjacent_enemy_unit_crossroads(state, unit, cr)
    if options:
        state.effect_stack.append({"op": "skunk_bounce", "chooser": unit.owner, "options": options})


def _op_skunk_bounce(state, step):
    if "choice" not in step:   # asked even with one target
        return PendingRequest("choice", step["chooser"], options=step["options"])
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
    for (kind, inst), spot in zip(sources, empty):       # auto-placed copies' Roars fizzle (F8)
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
    if roar_condition(state, unit.owner, unit.card_id, unit):   # another Worker besides itself
        amount += state.config.worker_bee_extra
    _push_gain(state, unit.owner, amount)


def _flying_squirrel_place(state, unit, cr):
    _push_gain(state, unit.owner, state.config.flying_squirrel_food)


def _squirrel_place(state, unit, cr):
    _push_gain(state, unit.owner, state.config.squirrel_food)


def _chipmunk_place(state, unit, cr):
    _push_gain(state, unit.owner, state.config.chipmunk_food_now)
    schedule(state, unit, 1, {"op": "gain_food", "player": unit.owner, "amount": state.config.chipmunk_food_later})


def _queen_marabunta_place(state, unit, cr):
    others = _control_tag_count(state, unit.owner, "Colony") - 1   # other friendly Colony units
    _push_gain(state, unit.owner, state.config.queen_marabunta_per_colony * max(0, others))


def _worker_wasp_eot(state, unit, cr):
    _push_gain(state, unit.owner, state.config.worker_wasp_food)


def _methuselah_eot(state, unit, cr):
    _push_gain(state, unit.owner, state.config.methuselah_food)


# --- Conditional draws (Cats / Colony / Aggro) ---

def _lynx_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_draw(state, unit.owner, 1)


def _caracal_onto_enemy(state, unit, cr):
    _push_draw(state, unit.owner, 1)


def _bat_place(state, unit, cr):
    _push_draw(state, unit.owner, 1)


def _mock_scout_place(state, unit, cr):
    # Baseline yardstick card: bare "draw 1" rider on a vanilla body (docs/balance/benchmark-set).
    _push_draw(state, unit.owner, 1)


def _mock_draw2_place(state, unit, cr):
    # Baseline yardstick legendary: bare "draw 2" on a tiny body - prices raw card draw.
    _push_draw(state, unit.owner, 2)


def _mock_removal_place(state, unit, cr):
    # Baseline yardstick legendary: bare UNCONDITIONAL removal of one adjacent enemy (any
    # strength) - prices the basic "remove a unit" primitive at a scarce legendary slot.
    targets = _adjacent_enemy_targets(state, unit, cr)
    if targets:
        state.effect_stack.append(
            {"op": "remove_choice", "chooser": unit.owner, "by_player": unit.owner,
             "by_card": "mock_removal", "options": targets})


def _mock_saboteur_place(state, unit, cr):
    # Baseline yardstick card: bare random hand-disruption (reuses Black Swan's seeded discard,
    # so it stays honest re: hidden info). No once-per-turn cap - it fires on placement.
    opponent = other_player(unit.owner)
    hand = state.hands[opponent]
    if hand:
        remove_from_hand(state, opponent, state.rng.choice(hand))


def _nurse_bee_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_draw(state, unit.owner, 2)


def _nurse_bumblebee_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_draw(state, unit.owner, 2)


def _termite_king_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_draw(state, unit.owner, 1)


# --- Delayed (Ramp / Food OTK) ---

def _black_bear_place(state, unit, cr):
    schedule(state, unit, state.config.black_bear_delay,
             {"op": "draw", "player": unit.owner, "n": state.config.black_bear_draw})


def _grizzly_place(state, unit, cr):
    schedule(state, unit, state.config.grizzly_bear_delay,
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
    # Roar: double this turn's haul (reworked 2026-07-05 - the old bank-and-double-in-2-turns
    # was the food_otk coin-flip). Snapshot now; the gain step resolves as a literal amount.
    haul = _food_gained_this_turn(state, unit.owner)
    _push_gain(state, unit.owner, haul * state.config.scrooge_gain_multiplier)


# --- Food OTK: "food gained this turn" signature cards (pure-OTK overhaul 2026-07-05) ---

def _rat_king_place(state, unit, cr):
    others = _control_tag_count(state, unit.owner, "Rodent") - 1     # exclude Rat King itself
    _push_draw(state, unit.owner, 1)
    _push_gain(state, unit.owner, state.config.rat_king_per_rodent * max(0, others))


def _hedgehog_place(state, unit, cr):                                # spiny body that feeds
    _push_gain(state, unit.owner, state.config.hedgehog_food)


def _chinchilla_place(state, unit, cr):                             # +1 action NEXT turn
    schedule(state, unit, 1,
             {"op": "grant_action", "player": unit.owner, "n": state.config.chinchilla_bonus_actions})


def _hamster_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_draw(state, unit.owner, state.config.hamster_draw)


def _muskrat_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_remove_choice(state, unit.owner, "muskrat",
                            _adjacent_enemy_targets(state, unit, cr))


def _groundhog_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_gain(state, unit.owner, state.config.groundhog_food)


def _gopher_place(state, unit, cr):
    if roar_condition(state, unit.owner, unit.card_id, unit):
        _push_gain(state, unit.owner, state.config.rodent_last_turn_food)


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
    "rat_discard": _op_rat_discard,
    "hornet_kill": _op_hornet_kill,
    "carmilla_sac": _op_carmilla_sac,
    "black_widow_sac": _op_black_widow_sac,
    "pestis_wipe": _op_pestis_wipe,
    "bounce_iid": _op_bounce_iid,
    "skunk_bounce": _op_skunk_bounce,
    "grizzly_strike": _op_grizzly_strike,
    "venom": _op_venom,
    "magpie_steal": _op_magpie_steal,
})


EFFECTS: dict[str, dict[str, Callable]] = {
    # Canine buff/tempo (anthems Raksha/Lobo/Verminus + Coyote's placement static live in
    # strength.py / statics.py - no handler needed here).
    "gray_wolf": {"on_place": _gray_wolf_place},
    "hyena": {"on_place": _hyena_place},
    "alpha": {"on_place": _alpha_place},
    "african_wild_dog": {"on_place": _african_wild_dog_place},
    "clarion": {"on_place": _clarion_place},
    "red_wolf": {"on_friendly_play": _red_wolf_friendly_play},
    "queen_honoria": {"on_friendly_play": _queen_honoria_friendly_play},
    "dingo": {"on_end_of_turn": _dingo_end_of_turn},
    "fox": {"on_gain_strength": _fox_gain_strength},
    "bush_dog": {"on_gain_strength": _bush_dog_gain_strength},
    # Reserve designs (not in any playable deck; kept for the future hand-buff deck / fixtures).
    "unnamed_canine": {"on_place": _unnamed_canine_place},
    "shuck": {"on_place": _shuck_place},
    # Egg Control: draw/shuffle/remove food engine + filtered random draws.
    "eon": {"on_end_of_turn": _eon_end_of_turn},
    "eon_food_engine": {"on_draw_event": _eon_event, "on_shuffle_event": _eon_event,
                        "on_remove_event": _eon_event},
    "vulture": {"on_remove_event": _vulture_remove_event},
    "omen": {"on_draw": _omen_drawn},
    "owl": {"on_place": _owl_place},
    "raven": {"on_place": _raven_place},
    "ember": {"on_remove": _ember_remove},
    "mouse": {"on_place": _mouse_place},
    "viper": {"on_place": _viper_place},
    "black_mamba": {"on_place": _black_mamba_place},
    "magpie": {"on_place": _magpie_place},
    "taipan": {"on_place": _taipan_place},
    "bird_egg": {"on_place": _bird_egg_place},
    "snake_egg": {"on_place": _snake_egg_place},
    # Food OTK: filtered draw + Deathrattle payoffs (Opossum's return lives in _dispose).
    "fathom": {"on_place": _fathom_place},
    "opossum": {"on_place": _opossum_place},
    "gazelle": {"on_remove": _gazelle_remove},
    "impala": {"on_remove": _impala_remove},
    # Stage 2.3: extra placements (F1), HQ-adjacency draws (F6), start-of-turn.
    # Apex Predator (tiger/polar_bear/borealis/unnamed_giant/eon) and "Costs X food"
    # (bulwark/elephant/cairn) are handled in _land_unit / legal_placements.
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
    "sloth": {"on_place": _sloth_place},
    # Stage 2.4: removal roars (King Theron's cover trigger fires from _fire_cover_event).
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
    "mock_scout": {"on_place": _mock_scout_place},
    "mock_draw_3": {"on_place": _mock_scout_place},
    "mock_draw_4": {"on_place": _mock_scout_place},
    "mock_draw_6": {"on_place": _mock_scout_place},
    "mock_draw_7": {"on_place": _mock_scout_place},
    "mock_flydraw_2": {"on_place": _mock_scout_place},
    "mock_flydraw_3": {"on_place": _mock_scout_place},
    "mock_flydraw_4": {"on_place": _mock_scout_place},
    "mock_flydraw_5": {"on_place": _mock_scout_place},
    "mock_saboteur": {"on_place": _mock_saboteur_place},
    "mock_draw2": {"on_place": _mock_draw2_place},
    "mock_removal": {"on_place": _mock_removal_place},
    "mock_courier": {"on_place": _mock_scout_place},
    "mock_skully": {"on_place": _mock_draw2_place},
    "mock_sentry": {"on_place": _stoop_place},
    "mock_hunter": {"on_place": _jaguar_place},
    # Calibration bodies (reserve): one bare effect on a ladder of strengths, for pricing anchors.
    "calib_draw1_1": {"on_place": _mock_scout_place},
    "calib_draw1_2": {"on_place": _mock_scout_place},
    "calib_draw2_0": {"on_place": _mock_draw2_place},
    "calib_draw2_1": {"on_place": _mock_draw2_place},
    "calib_draw2_2": {"on_place": _mock_draw2_place},
    "calib_draw2_3": {"on_place": _mock_draw2_place},
    "calib_rm3_2": {"on_place": _stoop_place},
    "calib_rm3_3": {"on_place": _stoop_place},
    "calib_rm3_4": {"on_place": _stoop_place},
    "calib_rm3_5": {"on_place": _stoop_place},
    "calib_rm3_6": {"on_place": _stoop_place},
    "calib_rm4_2": {"on_place": _jaguar_place},
    "calib_rm4_3": {"on_place": _jaguar_place},
    "calib_rm4_4": {"on_place": _jaguar_place},
    "calib_rm4_5": {"on_place": _jaguar_place},
    "calib_rm4_6": {"on_place": _jaguar_place},
    "calib_rm6_1": {"on_place": _serval_place},
    "calib_rm6_2": {"on_place": _serval_place},
    "calib_rm6_3": {"on_place": _serval_place},
    "calib_rm6_4": {"on_place": _serval_place},
    "calib_rm6_5": {"on_place": _serval_place},
    "calib_rmany_1": {"on_place": _mock_removal_place},
    "calib_rmany_2": {"on_place": _mock_removal_place},
    "calib_rmany_3": {"on_place": _mock_removal_place},
    "calib_rmany_4": {"on_place": _mock_removal_place},
    "calib_rmany_5": {"on_place": _mock_removal_place},
    "calib_extra_1": {"on_place": _jerboa_place},
    "calib_extra_2": {"on_place": _jerboa_place},
    "calib_extra_3": {"on_place": _jerboa_place},
    "calib_extra_4": {"on_place": _jerboa_place},
    "calib_extra_5": {"on_place": _jerboa_place},
    "calib_food10_2": {"on_place": _squirrel_place},
    "calib_food10_3": {"on_place": _squirrel_place},
    "calib_food10_4": {"on_place": _squirrel_place},
    "calib_food10_5": {"on_place": _squirrel_place},
    "calib_food10_6": {"on_place": _squirrel_place},
    "calib_food3t_2": {"on_end_of_turn": _worker_wasp_eot},
    "calib_food3t_3": {"on_end_of_turn": _worker_wasp_eot},
    "calib_food3t_4": {"on_end_of_turn": _worker_wasp_eot},
    "calib_food3t_5": {"on_end_of_turn": _worker_wasp_eot},
    "calib_food3t_6": {"on_end_of_turn": _worker_wasp_eot},
    "nurse_bee": {"on_place": _nurse_bee_place},
    "nurse_bumblebee": {"on_place": _nurse_bumblebee_place},
    "termite_king": {"on_place": _termite_king_place},
    # Delayed.
    "black_bear": {"on_place": _black_bear_place},
    "grizzly_bear": {"on_place": _grizzly_place},
    # Food OTK: "food gained this turn" signature + go-wide rodent payoff (2026-07-05 overhaul).
    "scrooge": {"on_place": _scrooge_place},
    "rat_king": {"on_place": _rat_king_place},
    "hedgehog": {"on_place": _hedgehog_place, "on_covered": _spines_covered},
    "porcupine": {"on_covered": _spines_covered},
    "chinchilla": {"on_place": _chinchilla_place},
    "hamster": {"on_place": _hamster_place},
    "muskrat": {"on_place": _muskrat_place},
    "groundhog": {"on_place": _groundhog_place},
    "gopher": {"on_place": _gopher_place},
    # Reveal.
    "andean_condor": {"on_place": _andean_condor_place},
    "oxpecker": {"on_place": _oxpecker_place},
    # Shared.
    "pufferfish": {"on_covered": _pufferfish_covered},
    "gale": {"on_place": _gale_place},
}
