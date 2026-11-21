"""The effect engine: the placement mechanic, the cover, removal, food, draws, and the effect-stack interpreter.

Effects resolve as declarative op-steps (plain dicts) on `state.effect_stack`, drained by `resolve()`. A step that needs a
choice surfaces as `state.pending`; the choice arrives as a normal action and resumes the paused step. Steps are plain
data, so a position clones, saves and replays.

Card behaviour: EFFECTS[card_id] -> {"on_place": fn} (a Roar), {"on_cover": fn} (when it covers an enemy), {"on_death": fn}
(when it is removed from the board), {"on_raid": fn} (after its raid), and OPS[op] -> fn(state, step) (the interpreter).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .actions import SKIP, ChoiceAction, PlaceAction
from .state import EngineError, GameState, Result, UnitInstance, other_player
from . import leaders as L
from . import statics
from .strength import count, effective_strength


# ============================================================== pending choices

@dataclass
class PendingRequest:
    """What an op returns when it needs a choice; becomes state.pending."""
    mode: str                       # "choice"
    chooser: str
    optional: bool
    options: list
    kind: Optional[str] = None      # "mulligan" for the opening hands

    def to_pending(self) -> dict:
        p = {"mode": self.mode, "chooser": self.chooser, "optional": self.optional, "options": list(self.options)}
        if self.kind:
            p["kind"] = self.kind
        return p


def legal_pending(state: GameState) -> list:
    p = state.pending
    assert p is not None
    acts: list = [ChoiceAction(o) for o in p["options"]]
    if p["optional"]:
        acts.append(ChoiceAction(SKIP))
    return acts


def apply_pending(state: GameState, action) -> None:
    """Record the choice on the paused step; the caller resolves on."""
    state.effect_stack[-1]["choice"] = action.choice
    state.pending = None


# ===================================================================== resolve loop

REQUIRE_SOURCE = False   # tests turn it on: every choice but the mulligan must name the card asking (`by_card`)


def resolve(state: GameState) -> None:
    """Drain the effect stack until it is empty, a choice is needed, or the game is decided. Each time it empties, every
    animal at 0 strength is removed (whatever that sets off resolves in turn)."""
    while True:
        _drain(state)
        if state.pending is not None or state.result is not None or state.effect_stack or not _remove_the_weak(state):
            return


def _remove_the_weak(state: GameState) -> bool:
    """The rule (Martin, 2026-11-21: "make it a general rule"): an animal at 0 strength is removed, by the rules, so
    Armor doesn't hold. Whether any was."""
    weak = [(cr, u) for cr, stack in state.board.items() for u in stack if effective_strength(state, u) <= 0]
    for cr, u in weak:
        _remove_specific(state, cr, u, by_player=None, by_effect=False)
    return bool(weak)


def _drain(state: GameState) -> None:
    while state.pending is None and state.result is None and state.effect_stack:
        step = state.effect_stack.pop()
        state.effect_steps_this_turn += 1
        if state.effect_steps_this_turn > state.config.max_effect_steps_per_turn:
            # The turn's effect cap: what is left is dropped, and the turn ends (rules.apply_action) once this returns.
            if state.effect_steps_this_turn == state.config.max_effect_steps_per_turn + 1:
                record_cap(state, "effect_steps", stack_cards(state, step.get("by_card")))
            state.effect_stack.clear()
            state.pending = None
            return
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
        if req is not None:           # the step needs a choice: put it back and pause
            if REQUIRE_SOURCE and step["op"] != "mulligan" and not step.get("by_card"):
                raise AssertionError(f"a {step['op']!r} choice with no source card")
            state.effect_stack.append(step)
            state.pending = req.to_pending()
            return


def record_cap(state: GameState, cap: str, cards) -> None:
    """A turn cap fired (Config.max_actions_per_turn, max_effect_steps_per_turn): the `turn_capped` event, kept on the
    state too (`caps`). `cards`: where the dropped steps came from."""
    rec = {"cap": cap, "player": state.current, "turn": state.turn_counter, "cards": sorted({c for c in cards if c})}
    state.caps.append(rec)
    state.emit("turn_capped", **rec)


def stack_cards(state: GameState, *extra) -> list:
    return [s.get("by_card") for s in state.effect_stack] + list(extra)


# ================================================================== mulligan

def _op_mulligan(state, step):
    """A blacklist mulligan: each returned card is replaced at once by the top deck card that is no copy of anything
    returned so far, up to the opening hand's size; SKIP keeps the rest. Returned cards are shuffled back at the end."""
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
                new = UnitInstance(deck.pop(_mulligan_replacement(deck, returned)), player, state.new_iid())
                hand.append(new)
                state.emit("mulligan", player=player, returned=inst.iid, drawn=[new.iid, new.card_id])   # hidden from the other
    if not done and hand and len(returned) < state.config.mulligan_cap(player, state.first_player) \
            and _mulligan_replacement(deck, returned) is not None:
        return PendingRequest("choice", player, optional=True, kind="mulligan", options=[u.iid for u in hand])
    if returned:                      # a kept hand leaves the deck order (and the RNG) untouched
        deck.extend(returned)
        state.rng.shuffle(deck)
    if not any(st.get("op") == "mulligan" for st in state.effect_stack):   # both done: the first turn begins
        state.emit("turn_start", player=state.current, turn=state.turn_counter)
        draw_cards(state, state.current, state.config.turn_draw_count)   # the first turn's card too (Martin, 2026-11-21)
    return None


def _mulligan_replacement(deck, blacklist):
    """Index of the topmost deck card (the end) that is no copy of a blacklisted card, or None."""
    banned = set(blacklist)
    return next((i for i in range(len(deck) - 1, -1, -1) if deck[i] not in banned), None)


# ============================================================== mana

# The Djinn: "Costs 1 less for each ...": card id -> what it counts (strength.count).
DJINN = {"djinn_hand": "hand", "djinn_ally": "ally", "djinn_enemy": "enemy", "djinn_region": "region"}


def mana_cost(state: GameState, card_id: str, player: Optional[str] = None) -> int:
    """What playing `card_id` from hand costs `player` (the current player by default): its card's cost, a Djinn's less
    its count, never below 0."""
    cost = state.cards[card_id].cost
    if card_id in DJINN:
        return max(0, cost - count(state, player or state.current, DJINN[card_id]))
    return cost


# ============================================================ placement

def playable_copy(state: GameState, player: str, card_id: str) -> Optional[UnitInstance]:
    """The hand instance a PlaceAction for `card_id` plays: the first copy in hand."""
    return next((u for u in state.hands[player] if u.card_id == card_id), None)


def legal_placements(state: GameState, player: str) -> list:
    """Every placement `player` could make from hand now, whatever it costs (rules filters by mana). Sorted, so a game
    replays identically. A card lands on an empty tile, on its owner's animal, or on an enemy it is stronger than; Flight
    lands anywhere; Hungry only on an enemy it is stronger than. A connected animal (or a flier) may raid the enemy den,
    reached through their base."""
    gm = state.game_map
    occ = state.connected_occupied(player)
    enemy = other_player(player)
    reach_den = any(cr in occ for cr in gm.hq_front(enemy))
    tiles = sorted(gm.crossroads)
    connectable = {cr for cr in tiles if state.is_connected(player, cr, occ)}
    out = []
    for card_id in sorted({u.card_id for u in state.hands[player]}):
        placer = playable_copy(state, player, card_id)
        keywords = state.cards[card_id].keywords
        hungry, flight = "Hungry" in keywords, "Flight" in keywords
        for cr in tiles:
            if not (flight or cr in connectable):
                continue
            top = state.top_unit(cr)
            if hungry:
                if top is not None and top.owner != player and statics.can_cover(state, placer, top):
                    out.append(PlaceAction(card_id, ("cr", cr)))
            elif top is None or top.owner == player or statics.can_cover(state, placer, top):
                out.append(PlaceAction(card_id, ("cr", cr)))
        if (reach_den or flight) and not hungry:
            out.append(PlaceAction(card_id, ("hq", enemy)))
    return out


def do_placement(state: GameState, player: str, card_id: str, target) -> None:
    unit = playable_copy(state, player, card_id)
    if unit is None:
        raise EngineError(f"{player} has no {card_id!r} in hand")
    strength = effective_strength(state, unit)   # as it is played
    state.hands[player].remove(unit)
    state.played_this_turn += 1
    if state.played_this_turn == state.config.assassin_nth_card and _leads(state, player, L.ASSASSIN):
        state.effect_stack.append({"op": "draw", "player": player, "n": 1, "by_card": L.ASSASSIN})
    kind, where = target
    if kind == "hq":
        _raid(state, player, unit, where, strength)
    else:
        _land_unit(state, player, unit, where)


def _raid(state: GameState, player: str, unit: UnitInstance, enemy: str, strength: int) -> None:
    """The den raid (Martin, 2026-11-20): an animal that enters the enemy den destroys food equal to its strength, at most
    what they have ("instead of stealing it destroys"), and is spent to the Remove Pile without landing (no Roar). A den
    emptied loses the game."""
    bonus = state.config.raider_leader_bonus if _leads(state, player, L.RAIDER) else 0
    factor = state.config.double_raid_factor if unit.card_id in DOUBLE_RAIDERS else 1
    n = min(max(strength, 0) * factor + bonus, state.food[enemy])
    state.emit("raid", player=player, iid=unit.iid, card=unit.card_id, den=enemy, str=strength, n=n)
    state.pile_add(unit.card_id, unit.owner)
    state.food[enemy] -= n
    if state.result is None and state.food[enemy] <= 0:
        state.result = Result(player, "starved")
    on_raid = EFFECTS.get(unit.card_id, {}).get("on_raid")
    if on_raid and state.result is None:
        on_raid(state, unit)


def _land_unit(state: GameState, player: str, unit: UnitInstance, cr: str) -> None:
    """The played animal lands on `cr`. What it covered is removed once its Roar and every reaction to the cover have
    resolved (the stack is last in, first out: that removal goes in first)."""
    covered = state.top_unit(cr)
    onto_enemy = covered is not None and covered.owner != player
    state.board.setdefault(cr, []).append(unit)
    state.emit("place", player=player, iid=unit.iid, card=unit.card_id, cr=cr, from_hand=True)
    if covered is not None:
        state.emit("cover", cr=cr, iid=covered.iid, card=covered.card_id, owner=covered.owner, by=unit.iid)
        if onto_enemy and "Hungry" in state.cards[unit.card_id].keywords:
            state.effect_stack.append({"op": "hungry_food", "player": player, "prey": covered.iid, "by_card": unit.card_id})
        on_cover = EFFECTS.get(unit.card_id, {}).get("on_cover")
        if onto_enemy and on_cover:
            on_cover(state, unit, covered)
        state.effect_stack.append({"op": "cover_remove", "cr": cr})
    if onto_enemy and _leads(state, player, L.WARLORD):
        state.effect_stack.append({"op": "gain_food", "player": player, "amount": state.config.warlord_leader_food,
                                   "by_card": L.WARLORD})
    if onto_enemy:
        if statics.has_keyword(state, covered, "Spikes"):
            _spikes_covered(state, covered, unit, cr)
        if statics.has_keyword(state, covered, "Poison"):
            _poison_covered(state, covered, unit)
    roar = EFFECTS.get(unit.card_id, {}).get("on_place")
    if roar:
        n = len(state.effect_stack)
        prev, state.cause, state.cause_iid = (state.cause, state.cause_iid), unit.card_id, unit.iid
        try:
            roar(state, unit, cr)
        finally:
            state.cause, state.cause_iid = prev
        for step in state.effect_stack[n:]:     # every step a Roar pushes names its card and unit as the source
            step.setdefault("by_card", unit.card_id)
            if step["by_card"] == unit.card_id:
                step.setdefault("by_iid", unit.iid)


def _spikes_covered(state, covered, coverer, cr):
    """Spikes: the first time an enemy covers it, that enemy is removed. Once per animal."""
    if covered.retaliation_used:
        return
    covered.retaliation_used = True
    if statics.can_be_removed(state, coverer):
        state.effect_stack.append(remove_iid_step(coverer.iid, by_player=covered.owner, by_card=covered.card_id))


def _poison_covered(state, covered, coverer):
    """Poison: the enemy that covers it is removed at the start of the Poison animal's owner's next turn, wherever it is
    by then, unless it has left the board first. It is a removal, so Armor resists it."""
    state.scheduled.append({"iid": coverer.iid, "owner": covered.owner, "remaining": 1,
                            "step": remove_iid_step(coverer.iid, by_player=covered.owner, by_card=covered.card_id)})
    state.emit("poisoned", iid=coverer.iid, card=coverer.card_id, owner=coverer.owner, by=covered.iid)


# ================================================================= removal & food

def _find_unit(state, iid):
    for cr, stack in state.board.items():
        for u in stack:
            if u.iid == iid:
                return cr, u
    return None, None


def _remove_specific(state, cr, unit, *, by_player, by_effect=True) -> bool:
    """Remove a unit from its stack (mid-stack too) to the Remove Pile. Armor stops any removal by an ability
    (`by_effect`); the rules' own removals pass it."""
    stack = state.board.get(cr)
    if not stack or unit not in stack:
        return False
    if by_effect and not statics.can_be_removed(state, unit):
        return False
    state.emit("remove", cr=cr, iid=unit.iid, card=unit.card_id, owner=unit.owner, by=by_player)
    stack.remove(unit)
    if not stack:
        del state.board[cr]
    state.pile_add(unit.card_id, unit.owner)
    on_death = EFFECTS.get(unit.card_id, {}).get("on_death")
    if on_death:
        on_death(state, unit)
    return True


def _op_cover_remove(state, step):
    """Every animal still beneath the top of `cr` is removed (Martin, 2026-11-20: "covered units don't get shuffled back
    into the deck, they just get removed"), by the rules, so Armor doesn't hold. If the coverer is gone, what it covered
    is the top again and stays."""
    stack = state.board.get(step["cr"])
    if not stack or len(stack) < 2:
        return None
    top = stack[-1]
    for unit in list(stack[:-1]):
        _remove_specific(state, step["cr"], unit, by_player=top.owner, by_effect=False)
    return None


def _op_hungry_food(state, step):
    """Hungry: once its prey is gone from the board, its player gains the food. A prey still standing (the eater died to
    Spikes first) gives nothing."""
    if _find_unit(state, step["prey"])[1] is None:
        gain_food(state, step["player"], state.config.hungry_food)
    return None


def gain_food(state: GameState, player: str, amount: int, *, income: bool = False) -> None:
    if amount <= 0:
        return
    state.food[player] += amount
    state.emit("food", player=player, n=amount, **({"income": True} if income else {}))
    if state.food[player] >= state.game_map.win_food:
        state.result = Result(player, "food")


def draw_cards(state: GameState, player: str, n: int) -> list:
    """Draw n cards; the newest past the hand limit burn to the Remove Pile."""
    drawn = state.draw(player, n)
    if drawn:
        state.emit("draw", player=player, cards=[[u.iid, u.card_id] for u in drawn])
        over = len(state.hands[player]) - state.config.hand_limit
        for inst in drawn[-over:] if over > 0 else []:
            state.hands[player].remove(inst)
            state.pile_add(inst.card_id, inst.owner)
            state.emit("remove", zone="hand", iid=inst.iid, card=inst.card_id, owner=inst.owner)
    return drawn


# ============================================================= turn start

def start_of_turn(state: GameState, player: str) -> None:
    """Advance `player`'s timers (Poison) and push those that come due; a timer on a unit gone from the board is
    cancelled. The caller resolves."""
    on_board = {u.iid for stack in state.board.values() for u in stack}
    fired, keep = [], []
    for s in state.scheduled:
        if s["owner"] != player:
            keep.append(s)
        elif s["iid"] in on_board:
            s["remaining"] -= 1
            (fired if s["remaining"] <= 0 else keep).append(s)
    state.scheduled = keep
    for s in fired[::-1]:      # the earliest scheduled ends on top of the stack and resolves first
        state.effect_stack.append(s["step"])


# ===================================================================== ops

def _op_draw_if_gone(state, step):
    """Draw once `prey` is gone from the board (it was removed), else nothing."""
    if _find_unit(state, step["prey"])[1] is None:
        draw_cards(state, step["player"], step["n"])
    return None


def _op_place_token(state, step):
    """Put a token into play on the tile its player chooses (free, as anything an effect puts into play): it lands as a
    placed animal does, so it may cover, and it has no Roar."""
    if not step["options"]:
        return None
    if "choice" not in step:
        return PendingRequest("choice", step["player"], optional=False, options=step["options"])
    _land_unit(state, step["player"], UnitInstance(step["card"], step["player"], state.new_iid()), step["choice"])
    return None


def _op_to_hand(state, step):
    """Put `n` new copies of a card into a player's hand; past the hand limit they burn, as a draw does."""
    player, made = step["player"], []
    for _ in range(step["n"]):
        inst = UnitInstance(step["card"], player, state.new_iid())
        state.hands[player].append(inst); made.append(inst)
    state.emit("draw", player=player, cards=[[u.iid, u.card_id] for u in made])
    over = len(state.hands[player]) - state.config.hand_limit
    for inst in made[-over:] if over > 0 else []:
        state.hands[player].remove(inst); state.pile_add(inst.card_id, inst.owner)
        state.emit("remove", zone="hand", iid=inst.iid, card=inst.card_id, owner=inst.owner)
    return None


def _op_scout(state, step):
    """Scout: look at the top cards of your deck (Config.scout_look), put the one you choose into your hand and shuffle
    the rest back. The options are "deck:K", the Kth card from the top; only the chooser sees them."""
    deck, player = state.decks[step["player"]], step["player"]
    n = min(state.config.scout_look, len(deck))
    if not n:
        return None
    if "choice" not in step:
        return PendingRequest("choice", player, optional=False, options=[f"deck:{k}" for k in range(n)])
    k = int(str(step["choice"]).split(":")[1])
    inst = UnitInstance(deck.pop(len(deck) - 1 - k), player, state.new_iid())
    state.hands[player].append(inst)
    state.emit("draw", player=player, cards=[[inst.iid, inst.card_id]])
    if len(state.hands[player]) > state.config.hand_limit:          # past the hand limit it burns, as a draw does
        state.hands[player].remove(inst); state.pile_add(inst.card_id, inst.owner)
        state.emit("remove", zone="hand", iid=inst.iid, card=inst.card_id, owner=inst.owner)
    state.rng.shuffle(deck)
    return None


def _op_gain_food(state, step):
    gain_food(state, step["player"], step["amount"])
    return None


def _op_draw(state, step):
    draw_cards(state, step["player"], step["n"])
    return None


def remove_iid_step(iid, *, by_player, by_card) -> dict:
    return {"op": "remove_iid", "iid": iid, "by_player": by_player, "by_card": by_card}


def _op_remove_iid(state, step):
    cr, unit = _find_unit(state, step["iid"])
    if unit is not None:
        _remove_specific(state, cr, unit, by_player=step["by_player"])
    return None


def _op_weaken_choice(state, step):
    """The player picks the enemy a Roar gives -N strength, for good, even when there is one (at 0 the rule removes it)."""
    if not step["options"]:
        return None
    if "choice" not in step:
        return PendingRequest("choice", step["chooser"], optional=False, options=step["options"])
    top = state.top_unit(step["choice"])
    if top is not None:
        top.strength_mod -= step["amount"]
        state.emit("strength", iid=top.iid, card=top.card_id, owner=top.owner, n=-step["amount"])
    return None


def _op_remove_choice(state, step):
    """The player picks the enemy a Roar removes, even when there is one: they click what it hits."""
    if not step["options"]:
        return None
    if "choice" not in step:
        return PendingRequest("choice", step["chooser"], optional=step["optional"], options=step["options"])
    if step["choice"] != SKIP:
        cr = step["choice"]
        top = state.top_unit(cr)
        if top is not None:
            _remove_specific(state, cr, top, by_player=step["chooser"])
    return None


OPS: dict[str, Callable] = {
    "mulligan": _op_mulligan,
    "cover_remove": _op_cover_remove,
    "hungry_food": _op_hungry_food,
    "gain_food": _op_gain_food,
    "draw": _op_draw,
    "draw_if_gone": _op_draw_if_gone,
    "scout": _op_scout,
    "place_token": _op_place_token,
    "to_hand": _op_to_hand,
    "remove_iid": _op_remove_iid,
    "remove_choice": _op_remove_choice,
    "weaken_choice": _op_weaken_choice,
}


# ============================================================== the cards' Roars

def _adjacent_enemy_targets(state, unit, cr, max_strength=None) -> list:
    """The adjacent enemies `unit`'s player may choose to remove: removable (no Armor), choosable (no Stealth), and of
    strength `max_strength` or less when given."""
    out = []
    for nb in state.game_map.neighbors(cr):
        top = state.top_unit(nb)
        if top is None or top.owner == unit.owner or not statics.can_be_removed(state, top) \
                or not statics.can_be_chosen(state, top, unit.owner):
            continue
        if max_strength is None or effective_strength(state, top) <= max_strength:
            out.append(nb)
    return out


def _crush(limit: str):
    """"Roar: remove all adjacent enemies with strength N or less." (the Rhinos, the Albatrosses; N the config's `limit`):
    every one at once, no choice, so Stealth doesn't hide; a removal by an ability, so Armor holds."""
    def roar(state, unit, cr):
        for nb in sorted(state.game_map.neighbors(cr)):
            top = state.top_unit(nb)
            if top is not None and top.owner != unit.owner and effective_strength(state, top) <= getattr(state.config, limit):
                state.effect_stack.append(remove_iid_step(top.iid, by_player=unit.owner, by_card=unit.card_id))
    return roar


def _remove_adjacent(state, unit, cr):
    """"Roar: remove an adjacent enemy." (the Big Game Hunter)."""
    targets = _adjacent_enemy_targets(state, unit, cr)
    if targets:
        state.effect_stack.append({"op": "remove_choice", "chooser": unit.owner, "by_card": unit.card_id,
                                   "options": targets, "optional": False})


def _weaken(n: int):
    """"Roar: give an adjacent enemy -N strength.": for good; at 0 the rule removes it. Stealth hides from it."""
    def roar(state, unit, cr):
        targets = [nb for nb in state.game_map.neighbors(cr)
                   if (top := state.top_unit(nb)) is not None and top.owner != unit.owner
                   and statics.can_be_chosen(state, top, unit.owner)]
        if targets:
            state.effect_stack.append({"op": "weaken_choice", "chooser": unit.owner, "by_card": unit.card_id,
                                       "options": targets, "amount": n})
    return roar


def _draw_a_card(state, unit, cr):
    """"Roar: draw a card."."""
    state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1})


def _scout(state, unit, cr):
    """"Roar: Scout a card."."""
    state.effect_stack.append({"op": "scout", "player": unit.owner})


SPORE = "spore"   # the Spores' token: a 1-mana 1, in no deck (status reserve), made by the cards below


def _duplicate(state, unit, cr):
    """"Roar: place a Spore on an adjacent tile.": wherever a card could be placed (Martin, 2026-11-21: "any tile, not
    just empty"): empty, yours (covered, so removed), or an enemy the Spore is stronger than."""
    spore = UnitInstance(SPORE, unit.owner, -1)
    tiles = [nb for nb in state.game_map.neighbors(cr)
             if (top := state.top_unit(nb)) is None or top.owner == unit.owner or statics.can_cover(state, spore, top)]
    if tiles:
        state.effect_stack.append({"op": "place_token", "player": unit.owner, "card": SPORE, "options": sorted(tiles)})


def _mama_spore(state, unit, cr):
    """"Roar: put 2 Spores into your hand."."""
    state.effect_stack.append({"op": "to_hand", "player": unit.owner, "card": SPORE, "n": state.config.mama_spores})


def _raid_draw(state, unit):
    """"After it raids, draw a card.": once its raid has destroyed the food, its owner draws."""
    state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1, "by_card": unit.card_id, "by_iid": unit.iid})


def _death_draw(state, unit):
    """"Death: draw a card.": when it is removed from the board, by anything, its owner draws."""
    state.effect_stack.append({"op": "draw", "player": unit.owner, "n": 1, "by_card": unit.card_id, "by_iid": unit.iid})


def _draw_if_it_removes(state, unit, covered):
    """"Roar: if this removes an enemy, draw a card.": it removes an enemy by covering it, so the draw waits below the
    cover's removal and happens only if the covered enemy is gone (Spikes removing this first leaves it standing)."""
    state.effect_stack.append({"op": "draw_if_gone", "player": unit.owner, "prey": covered.iid, "n": 1,
                               "by_card": unit.card_id, "by_iid": unit.iid})


# The Hunters' -N, as their text says (Martin, 2026-11-21: "change Bite back"). Hunters 1 to 6, each a step down from
# the ids they were made under (Martin, 2026-11-21: "move each one 1 step down"; the ids stay, so saved decks keep them).
WEAKENS = {"hunter_2": 1, "hunter_3": 2, "hunter_4": 3, "hunter_5": 4, "hunter_6": 5, "hunter_7": 6}
CANTRIPS = ("cantrip_2", "cantrip_3", "cantrip_4")
DEATH_DRAWS = ("death_draw_1",)
KILL_DRAWS = ("kill_draw_2",)
DOUBLE_RAIDERS = ("double_raid_2", "double_raid_4")
RAID_DRAWS = ("raid_draw_5",)
SCOUTS = ("scout_3",)

EFFECTS: dict[str, dict[str, Callable]] = {
    **{cid: {"on_place": _weaken(n)} for cid, n in WEAKENS.items()},
    "giant_hunter": {"on_place": _remove_adjacent},
    **{cid: {"on_place": _draw_a_card} for cid in CANTRIPS},
    **{cid: {"on_death": _death_draw} for cid in DEATH_DRAWS},
    **{cid: {"on_raid": _raid_draw} for cid in RAID_DRAWS},
    **{cid: {"on_place": _scout} for cid in SCOUTS},
    "duplicating_spore": {"on_place": _duplicate},
    "rhino": {"on_place": _crush("crush_max")},
    "albatross": {"on_place": _crush("crush_albatross_max")},
    "young_rhino": {"on_place": _crush("crush_young_max")},
    "young_albatross": {"on_place": _crush("crush_young_albatross_max")},
    "mama_spore": {"on_place": _mama_spore},
    **{cid: {"on_cover": _draw_if_it_removes} for cid in KILL_DRAWS},
}

# The cards a card makes, which a card read large shows beside it (Martin, 2026-11-21: "same way it was in the original game").
MAKES: dict[str, tuple] = {"duplicating_spore": (SPORE,), "mama_spore": (SPORE,)}


# ===================================================================== leaders

def _leads(state: GameState, player: str, leader_id: str) -> bool:
    lead = state.leaders.get(player)
    return lead is not None and lead["id"] == leader_id


def power_cost(state: GameState, player: str) -> int:
    """What `player`'s leader's power costs: the Elf's its own, every other the config's."""
    lead = state.leaders.get(player)
    return state.config.elf_power_cost if lead and lead["id"] == L.ELF else state.config.leader_power_cost


def leader_usable(state: GameState, player: str) -> bool:
    """Whether `player`'s leader has a power that would do something now, not used yet this turn (Martin, 2026-11-21:
    "only be used once a turn"); the caller checks the mana."""
    lead = state.leaders.get(player)
    if lead is None or L.kind_of(lead["id"]) != "power" or state.power_used:
        return False
    if lead["id"] == L.ELF:
        return count(state, player, "region") > 0   # food for each region you control: none, nothing to gain
    return bool(state.decks[player])        # the Sage draws


def do_leader(state: GameState, player: str) -> None:
    """`player` uses their leader's power (the caller has paid for it)."""
    lead = state.leaders.get(player)
    if lead is None:
        raise EngineError(f"{player} has no leader")
    state.emit("leader_power", player=player, card=lead["id"])
    state.power_used = True
    if lead["id"] == L.SAGE:
        state.effect_stack.append({"op": "draw", "player": player, "n": 1, "by_card": L.SAGE})
    elif lead["id"] == L.ELF:   # "Gain 1 food for each region you control."
        state.effect_stack.append({"op": "gain_food", "player": player, "by_card": L.ELF,
                                   "amount": state.config.elf_food_per_region * count(state, player, "region")})
    else:
        raise EngineError(f"{lead['id']!r} has no power to use")
