"""Game state: the mutable position plus setup, cloning, serialization and per-seat views.

`apply_action` (rules.py) mutates a GameState in place; a caller that branches (a bot looking ahead) calls `clone()`
first. Effects resolve as plain-dict op-steps on `effect_stack`; a step that needs a choice surfaces as `pending`, and
the choice arrives as a normal action. Randomness is a seeded RNG carried on the state, so a game replays identically
from (seed, actions).
"""

from __future__ import annotations

import copy
import random
from collections import deque
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Optional

from .cards import Card, load_cards
from .config import Config
from .maps import GameMap, load_map


class EngineError(Exception):
    """Raised on an illegal engine operation (bad action, unsupported state)."""


def other_player(player: str) -> str:
    return "B" if player == "A" else "A"


class UnitInstance:
    """One card instance: a card id, its owner and a unique instance id. The same instance moves from hand to board."""

    __slots__ = ("card_id", "owner", "iid", "retaliation_used", "strength_mod")

    def __init__(self, card_id: str, owner: str, iid: int, retaliation_used: bool = False, strength_mod: int = 0):
        self.card_id = card_id
        self.owner = owner
        self.iid = iid
        self.retaliation_used = retaliation_used   # Spikes: spent on the first enemy that covers it
        self.strength_mod = strength_mod           # what effects have added to its strength, for good (the Hunters' -N)

    def to_dict(self) -> dict:
        return {"card_id": self.card_id, "owner": self.owner, "iid": self.iid, "retaliation_used": self.retaliation_used,
                "strength_mod": self.strength_mod}

    @staticmethod
    def from_dict(d: dict) -> "UnitInstance":
        return UnitInstance(d["card_id"], d["owner"], d["iid"], d.get("retaliation_used", False), d.get("strength_mod", 0))

    def __repr__(self) -> str:
        return f"UnitInstance({self.card_id!r}, {self.owner!r}, {self.iid})"


def _copy_unit(u: UnitInstance) -> UnitInstance:
    return UnitInstance(u.card_id, u.owner, u.iid, u.retaliation_used, u.strength_mod)


@dataclass(frozen=True)
class Result:
    """The game's outcome. winner is 'A'/'B', or None for a draw."""

    winner: Optional[str]
    reason: str  # "food" | "starved" | "max_turns" | "concede" | "timeout"

    def to_dict(self) -> dict:
        return {"winner": self.winner, "reason": self.reason}

    @staticmethod
    def from_dict(d: dict) -> "Result":
        return Result(d["winner"], d["reason"])


@dataclass(frozen=True)
class StateView:
    """What one seat may see: the opponent's hand and both decks as counts only. Immutable, so a bot can't touch the live
    game through it."""

    player: str
    to_act: str
    current: str
    turn_counter: int
    board: Mapping[str, tuple[tuple[str, str], ...]]  # tile -> ((card_id, owner) bottom->top)
    own_hand: tuple[str, ...]
    opponent_hand_count: int
    own_deck_count: int
    opponent_deck_count: int
    remove_pile: tuple[str, ...]
    food: Mapping[str, int]
    pending: Optional[Mapping[str, Any]]
    result: Optional[Result]


def _rng_to_dict(rng: random.Random) -> dict:
    version, internal, gauss = rng.getstate()
    return {"version": version, "state": list(internal), "gauss": gauss}


def _rng_from_dict(d: dict) -> random.Random:
    rng = random.Random()
    rng.setstate((d["version"], tuple(d["state"]), d["gauss"]))
    return rng


def _copy_rng(rng: random.Random) -> random.Random:
    new = random.Random()
    new.setstate(rng.getstate())
    return new


class GameState:
    """The full mutable position. Construct via new_game() or from_dict(). `game_map`, `cards` and `config` are shared
    immutable singletons, never cloned or serialized."""

    def __init__(self, game_map: GameMap, cards: dict[str, Card], config: Config, *,
                 board: dict[str, list[UnitInstance]], hands: dict[str, list[UnitInstance]], decks: dict[str, list[str]],
                 remove_pile: list[str], food: dict[str, int], current: str, first_player: str,
                 rng: Optional[random.Random] = None, starting_decks: Optional[dict[str, tuple]] = None,
                 turn_counter: int = 0, mana_spent: int = 0, applied_this_turn: int = 0, effect_steps_this_turn: int = 0,
                 played_this_turn: int = 0,
                 caps: Optional[list] = None, next_iid: int = 0, effect_stack: Optional[list[dict]] = None,
                 pending: Optional[dict] = None, scheduled: Optional[list[dict]] = None, result: Optional[Result] = None,
                 pile_owners: Optional[list] = None, leaders: Optional[dict[str, dict]] = None,
                 food_gained: Optional[dict[str, int]] = None):
        self.game_map = game_map
        self.cards = cards
        self.config = config
        self.board = board                 # tile -> stack (bottom..top); the top unit holds the tile
        self.hands = hands                 # player -> list of UnitInstance
        self.decks = decks                 # player -> list of card ids (the top is the end)
        self.starting_decks = starting_decks if starting_decks is not None else {"A": (), "B": ()}
        self.remove_pile = remove_pile     # shared and public
        self.pile_owners = pile_owners if pile_owners is not None else [None] * len(remove_pile)   # in step with remove_pile
        self.leaders = leaders if leaders is not None else {}   # player -> {"id": card id}
        self.food = food
        self.food_gained = food_gained if food_gained is not None else {"A": 0, "B": 0}   # every gain this game, start excluded
        self.current = current
        self.first_player = first_player
        self.rng = rng if rng is not None else random.Random()
        self.turn_counter = turn_counter
        self.mana_spent = mana_spent       # this turn's mana spent so far
        self.applied_this_turn = applied_this_turn   # every apply_action of the turn, choices included (Config.max_actions_per_turn)
        self.played_this_turn = played_this_turn     # the cards its player has played from hand this turn (the Assassin)
        self.effect_steps_this_turn = effect_steps_this_turn   # effect steps resolved this turn (Config.max_effect_steps_per_turn)
        self.caps: list = caps if caps is not None else []     # every turn a cap ended: {cap, player, turn, cards}
        self._next_iid = next_iid
        self.effect_stack = effect_stack if effect_stack is not None else []
        self.pending = pending
        self.scheduled = scheduled if scheduled is not None else []   # delayed steps: Poison's removal
        self.result = result
        # What happened, in order: the server hands these to the players. Never saved, and a clone starts empty. `cause`
        # is the card whose effect is running, `cause_iid` the very unit when known; both are stamped on each event.
        self.events: list[dict] = []
        self.cause: Optional[str] = None
        self.cause_iid: Optional[int] = None

    def emit(self, e: str, **fields) -> None:
        self.events.append({"e": e, **fields, **({"cause": self.cause} if self.cause else {}),
                            **({"cause_iid": self.cause_iid} if self.cause and self.cause_iid is not None else {})})

    def pile_add(self, card_id: str, owner: Optional[str]) -> None:
        self.remove_pile.append(card_id)
        self.pile_owners.append(owner)

    def new_iid(self) -> int:
        iid = self._next_iid
        self._next_iid += 1
        return iid

    def draw(self, player: str, n: int) -> list[UnitInstance]:
        """Move up to n cards from the top of `player`'s deck into their hand; returns the instances drawn."""
        deck, hand = self.decks[player], self.hands[player]
        drawn: list[UnitInstance] = []
        for _ in range(min(n, len(deck))):
            inst = UnitInstance(deck.pop(), player, self.new_iid())
            hand.append(inst)
            drawn.append(inst)
        return drawn

    def top_unit(self, cr: str) -> Optional[UnitInstance]:
        stack = self.board.get(cr)
        return stack[-1] if stack else None

    def owner_of(self, cr: str) -> Optional[str]:
        u = self.top_unit(cr)
        return u.owner if u else None

    def connected_occupied(self, player: str) -> set:
        """The tiles `player` holds that are connected to their base through their own animals."""
        board, adjacency = self.board, self.game_map._sorted_adjacency
        seeds = [cr for cr in self.game_map.hq_front(player) if (st := board.get(cr)) and st[-1].owner == player]
        seen, queue = set(seeds), deque(seeds)
        while queue:
            for nb in adjacency.get(queue.popleft(), ()):
                if nb not in seen and (st := board.get(nb)) and st[-1].owner == player:
                    seen.add(nb)
                    queue.append(nb)
        return seen

    def is_connected(self, player: str, cr: str, occ: Optional[set] = None) -> bool:
        """Whether `player` may place on `cr` without Flight: a tile of their base, or one held or touched by their
        connected animals."""
        gm = self.game_map
        if cr in gm.hq_front(player):
            return True
        if occ is None:
            occ = self.connected_occupied(player)
        return cr in occ or any(nb in occ for nb in gm.neighbors(cr))

    def player_to_act(self) -> str:
        """The seat that must act next: the pending chooser mid-resolution, else the current player."""
        return self.pending["chooser"] if self.pending is not None else self.current

    def clone(self) -> "GameState":
        """An independent copy: mutating it never touches the original."""
        new = GameState.__new__(GameState)
        new.game_map, new.cards, new.config = self.game_map, self.cards, self.config
        new.board = {cr: [_copy_unit(u) for u in stack] for cr, stack in self.board.items()}
        new.hands = {p: [_copy_unit(u) for u in h] for p, h in self.hands.items()}
        new.decks = {p: list(d) for p, d in self.decks.items()}
        new.starting_decks = self.starting_decks
        new.remove_pile = list(self.remove_pile)
        new.pile_owners = list(self.pile_owners)
        new.leaders = {p: dict(lead) for p, lead in self.leaders.items()}
        new.food = dict(self.food)
        new.food_gained = dict(self.food_gained)
        new.current, new.first_player = self.current, self.first_player
        new.rng = _copy_rng(self.rng)
        new.turn_counter = self.turn_counter
        new.mana_spent = self.mana_spent
        new.applied_this_turn = self.applied_this_turn
        new.played_this_turn = self.played_this_turn
        new.effect_steps_this_turn = self.effect_steps_this_turn
        new.caps = list(self.caps)
        new._next_iid = self._next_iid
        new.effect_stack = copy.deepcopy(self.effect_stack)
        new.pending = copy.deepcopy(self.pending)
        new.scheduled = copy.deepcopy(self.scheduled)
        new.result = self.result
        new.events, new.cause, new.cause_iid = [], None, None
        return new

    def view_for(self, player: str) -> StateView:
        opp = other_player(player)
        return StateView(
            player=player, to_act=self.player_to_act(), current=self.current, turn_counter=self.turn_counter,
            board=MappingProxyType({cr: tuple((u.card_id, u.owner) for u in stack) for cr, stack in self.board.items()}),
            own_hand=tuple(u.card_id for u in self.hands[player]), opponent_hand_count=len(self.hands[opp]),
            own_deck_count=len(self.decks[player]), opponent_deck_count=len(self.decks[opp]),
            remove_pile=tuple(self.remove_pile), food=MappingProxyType(dict(self.food)),
            pending=MappingProxyType(copy.deepcopy(self.pending)) if self.pending else None, result=self.result)

    def to_dict(self) -> dict:
        return {
            "map_id": self.game_map.id,
            "board": {cr: [u.to_dict() for u in stack] for cr, stack in self.board.items()},
            "hands": {p: [u.to_dict() for u in h] for p, h in self.hands.items()},
            "decks": {p: list(d) for p, d in self.decks.items()},
            "starting_decks": {p: list(d) for p, d in self.starting_decks.items()},
            "remove_pile": list(self.remove_pile),
            "pile_owners": list(self.pile_owners),
            "leaders": {p: dict(lead) for p, lead in sorted(self.leaders.items())},
            "food": dict(self.food),
            "food_gained": dict(self.food_gained),
            "current": self.current,
            "first_player": self.first_player,
            "rng": _rng_to_dict(self.rng),
            "turn_counter": self.turn_counter,
            "mana_spent": self.mana_spent,
            "applied_this_turn": self.applied_this_turn,
            "played_this_turn": self.played_this_turn,
            "effect_steps_this_turn": self.effect_steps_this_turn,
            "caps": [dict(c) for c in self.caps],
            "next_iid": self._next_iid,
            "effect_stack": copy.deepcopy(self.effect_stack),
            "pending": copy.deepcopy(self.pending),
            "scheduled": copy.deepcopy(self.scheduled),
            "result": self.result.to_dict() if self.result else None,
        }

    @staticmethod
    def from_dict(d: dict, *, cards: Optional[dict[str, Card]] = None, config: Optional[Config] = None) -> "GameState":
        return GameState(
            load_map(d["map_id"]), cards or load_cards(), config or Config(),
            board={cr: [UnitInstance.from_dict(u) for u in stack] for cr, stack in d["board"].items()},
            hands={p: [UnitInstance.from_dict(u) for u in h] for p, h in d["hands"].items()},
            decks={p: list(dk) for p, dk in d["decks"].items()},
            starting_decks={p: tuple(dk) for p, dk in d.get("starting_decks", {}).items()},
            remove_pile=list(d["remove_pile"]),
            pile_owners=list(d["pile_owners"]) if "pile_owners" in d else None,
            leaders={p: {"id": lead["id"]} for p, lead in (d.get("leaders") or {}).items()},
            food=dict(d["food"]), food_gained=dict(d.get("food_gained") or {"A": 0, "B": 0}), current=d["current"], first_player=d["first_player"], rng=_rng_from_dict(d["rng"]),
            turn_counter=d["turn_counter"], mana_spent=d.get("mana_spent", 0),
            applied_this_turn=d.get("applied_this_turn", 0), effect_steps_this_turn=d.get("effect_steps_this_turn", 0),
            played_this_turn=d.get("played_this_turn", 0),
            caps=[dict(c) for c in d.get("caps", [])], next_iid=d["next_iid"],
            effect_stack=copy.deepcopy(d.get("effect_stack") or []), pending=copy.deepcopy(d.get("pending")),
            scheduled=copy.deepcopy(d.get("scheduled") or []),
            result=Result.from_dict(d["result"]) if d["result"] else None)


MAP_ID = "map_hex19"


def new_game(deck_a: list[str], deck_b: list[str], seed: int, *, cards: Optional[dict[str, Card]] = None,
             config: Optional[Config] = None, first_player: Optional[str] = None,
             leaders: Optional[dict] = None, map_id: str = MAP_ID) -> GameState:
    """A fresh game: both decks shuffled, the first player by coin flip (or `first_player`), the opening hands dealt and
    the mulligan waiting. `leaders`: player -> their deck's leader's card id."""
    rng = random.Random(seed)
    cards = cards or load_cards()
    config = config or Config()
    unknown = sorted({c for c in (*deck_a, *deck_b) if c not in cards})
    if unknown:
        raise EngineError(f"unknown card {', '.join(unknown)}")
    decks = {"A": list(deck_a), "B": list(deck_b)}
    starting_decks = {"A": tuple(deck_a), "B": tuple(deck_b)}
    rng.shuffle(decks["A"])
    rng.shuffle(decks["B"])
    coin_flip = "A" if rng.random() < 0.5 else "B"
    first = first_player if first_player is not None else coin_flip
    second = other_player(first)
    state = GameState(load_map(map_id), cards, config, board={}, hands={"A": [], "B": []}, decks=decks, remove_pile=[],
                      food={"A": config.start_food, "B": config.start_food}, current=first, first_player=first, rng=rng,
                      starting_decks=starting_decks)
    from .leaders import leader_problem
    for p, lid in sorted((leaders or {}).items()):
        if lid is None:
            continue
        bad = leader_problem(lid, decks[p])
        if bad:
            raise EngineError(bad)
        state.leaders[p] = {"id": lid}
    state.draw(first, config.first_player_opening_draw)
    state.draw(second, config.second_player_opening_draw)
    if config.mulligan:
        for player in (second, first):
            if state.hands[player]:
                state.effect_stack.append({"op": "mulligan", "player": player, "returned": []})
        if state.effect_stack:
            chooser = state.effect_stack[-1]["player"]
            state.pending = {"mode": "choice", "chooser": chooser, "optional": True, "kind": "mulligan",
                             "options": [u.iid for u in state.hands[chooser]]}
    return state
