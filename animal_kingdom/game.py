"""The game as Python reaches it. The rules live once, in the Rust engine (`engine_rs/`, the module `ak_engine`); this
module holds none. It gives the server, the tools and the tests the engine's data as Python values (cards, the map, the
rules' numbers, the leaders), the actions as small classes, and a position (`GameState`) whose every question and every
move is answered by the engine.

A `GameState` keeps the position as plain Python data so a caller can read it and a test can set one up by hand; before
each question it hands that data to the engine (`_sync`), and after each move it takes the engine's back (`_load`).
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from importlib import resources
from types import SimpleNamespace
from typing import ClassVar, Optional, Union

try:
    import ak_engine
except ImportError as e:   # the compiled engine is not built for this Python
    raise ImportError("the game's rules engine is not built: run engine_rs/build.sh (it needs the Rust toolchain: brew install rust)") from e


class EngineError(Exception):
    """Raised on an illegal engine operation (bad action, unsupported state)."""


def other_player(player: str) -> str:
    return "B" if player == "A" else "A"


def _call(fn, *args):
    """Call into the engine: a broken rule (ValueError) or a panic it caught (RuntimeError) is an EngineError."""
    try:
        return fn(*args)
    except (ValueError, RuntimeError) as e:
        raise EngineError(str(e)) from None


def load_bundled_json(filename: str) -> dict:
    """A data file bundled inside the package (data/), whether run from source or installed."""
    resource = resources.files("animal_kingdom") / "data" / filename
    with resources.as_file(resource) as path:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)


# ------------------------------------------------------------------ actions

@dataclass(frozen=True)
class PlaceAction:
    """Play an animal from hand. `target` is ("cr", "<tile>") or ("hq", "<player>"): a raid on that player's den."""

    card_id: str
    target: tuple[str, str]
    kind: ClassVar[str] = "place"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "card_id": self.card_id, "target": list(self.target)}


@dataclass(frozen=True)
class LeaderAction:
    """Use your leader's power; it costs its price in mana."""

    kind: ClassVar[str] = "leader"

    def to_dict(self) -> dict:
        return {"kind": self.kind}


@dataclass(frozen=True)
class PassAction:
    """End the turn. Legal whenever nothing is resolving (`can_pass`); `legal_actions` lists it only when nothing else
    is legal."""

    kind: ClassVar[str] = "pass"

    def to_dict(self) -> dict:
        return {"kind": self.kind}


@dataclass(frozen=True)
class ChoiceAction:
    """A sub-decision while an effect resolves: a tile, a unit iid, or SKIP to decline an optional one."""

    choice: object
    kind: ClassVar[str] = "choice"

    def to_dict(self) -> dict:
        return {"kind": self.kind, "choice": self.choice}


SKIP = "__skip__"

Action = Union[PlaceAction, LeaderAction, PassAction, ChoiceAction]


def action_from_dict(d: dict) -> Action:
    kind = d["kind"]
    if kind == "place":
        return PlaceAction(card_id=d["card_id"], target=tuple(d["target"]))
    if kind == "leader":
        return LeaderAction()
    if kind == "choice":
        return ChoiceAction(choice=d["choice"])
    if kind == "pass":
        return PassAction()
    raise ValueError(f"unknown action kind {kind!r}")


def _adict(action) -> dict:
    return action if isinstance(action, dict) else action.to_dict()


# ------------------------------------------------------------------ the rules' numbers

class Config:
    """The rules' numbers, by name (their home, with what each is for: `engine_rs/src/data.rs`). `Config()` is the game's;
    `Config(mana_cap=5)` or `config.sweep(mana_cap=5)` changes some."""

    DEFAULTS: ClassVar[dict] = ak_engine.default_config()

    def __init__(self, **overrides):
        unknown = sorted(set(overrides) - set(self.DEFAULTS))
        if unknown:
            raise TypeError(f"the game has no number called {', '.join(unknown)}")
        self.__dict__.update(self.DEFAULTS)
        self.__dict__.update(overrides)

    def as_dict(self) -> dict:
        return dict(self.__dict__)

    def sweep(self, **overrides) -> "Config":
        return Config(**{**self.__dict__, **overrides})

    def __eq__(self, other) -> bool:
        return isinstance(other, Config) and self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.__dict__.items())))

    def __repr__(self) -> str:
        changed = {k: v for k, v in self.__dict__.items() if self.DEFAULTS[k] != v}
        return f"Config({', '.join(f'{k}={v!r}' for k, v in changed.items())})"


# ------------------------------------------------------------------ cards

_CARD_RULES = ak_engine.card_rules()
COPY_LIMITS: dict[str, int] = _CARD_RULES["copy_limits"]     # rarity -> the copies a deck may hold
DECK_SIZE: int = _CARD_RULES["deck_size"]
PLANNED: str = _CARD_RULES["planned"]                        # a "planned" record is no card yet: the loader skips it
KEYWORDS = frozenset(_CARD_RULES["keywords"])


class CardDataError(ValueError):
    """Raised when card data fails validation."""


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    status: str
    rarity: str
    base_strength: int | str       # an int, or "dynamic"
    cost: int
    keywords: frozenset[str] = field(default_factory=frozenset)
    dynamic_strength: Optional[str] = None
    text: str = ""
    makes: tuple = ()              # the cards it makes, which a card read large shows beside it
    weaken: Optional[int] = None   # the strength its Roar takes off an adjacent enemy

    @property
    def is_dynamic(self) -> bool:
        return self.base_strength == "dynamic"

    @property
    def collectible(self) -> bool:
        return self.status == "collectible"

    def record(self) -> dict:
        """The card as a record of the card table."""
        return {"id": self.id, "name": self.name, "status": self.status, "rarity": self.rarity,
                "base_strength": self.base_strength, "cost": self.cost, "keywords": sorted(self.keywords),
                **({"dynamic_strength": self.dynamic_strength} if self.dynamic_strength else {}), "text": self.text}


def validate_card_record(rec: dict) -> None:
    """Raise CardDataError on the first problem with a raw card record."""
    try:
        ak_engine.validate_card_record(rec)
    except ValueError as e:
        raise CardDataError(str(e)) from None


_MAPS_TEXT = json.dumps(load_bundled_json("maps.json"))
MAP_ID = os.environ.get("AK_MAP", "map_hex19")   # AK_MAP=map_sq16 plays the 4x4 test board
_engines: dict[tuple, "ak_engine.Engine"] = {}


def _engine_of(cards_text: str, config: Config, map_id: str = MAP_ID):
    key = (cards_text, tuple(sorted(config.as_dict().items())), map_id)
    if key not in _engines:
        try:
            _engines[key] = ak_engine.Engine(cards_text, _MAPS_TEXT, json.dumps(config.as_dict()), map_id)
        except ValueError as e:
            raise CardDataError(str(e)) from None
    return _engines[key]


def load_cards(raw: Optional[dict] = None) -> dict[str, Card]:
    """id -> Card in the card table's order, from the bundled data/cards.json or `raw` (a dict shaped like it), as the
    engine reads it: a record it refuses raises CardDataError."""
    if raw is None:
        raw = load_bundled_json("cards.json")
    if not isinstance(raw.get("cards"), list):
        raise CardDataError("cards.json must contain a non-empty 'cards' list")
    read = {c["id"]: c for c in _engine_of(json.dumps(raw), Config()).cards()}
    return {rec["id"]: Card(id=c["id"], name=c["name"], status=c["status"], rarity=c["rarity"], base_strength=c["base_strength"],
                            cost=c["cost"], keywords=frozenset(c["keywords"]), dynamic_strength=c["dynamic_strength"],
                            text=c["text"], makes=tuple(c.get("makes", ())), weaken=c.get("weaken"))
            for rec in raw["cards"] if rec.get("status") != PLANNED for c in [read[rec["id"]]]}


CARDS: dict[str, Card] = load_cards()
_CARDS_TEXT = json.dumps(load_bundled_json("cards.json"))
ENGINE = _engine_of(_CARDS_TEXT, Config())     # the game as it ships: its cards, its map, its numbers

MAKES: dict[str, tuple] = {c.id: c.makes for c in CARDS.values() if c.makes}
WEAKENS: dict[str, int] = {c.id: c.weaken for c in CARDS.values() if c.weaken is not None}


def _engine_for(cards: Optional[dict[str, Card]], config: Optional[Config], map_id: str = MAP_ID):
    """The engine that plays `cards` under `config`: the game's own unless a caller (a test) brings others."""
    text = _CARDS_TEXT if cards is None or cards is CARDS else json.dumps({"cards": [c.record() for c in cards.values()]})
    return _engine_of(text, config or Config(), map_id)


# ------------------------------------------------------------------ leaders and decks

# card id -> (kind, the ability as the player reads it): a "power" is used for its mana once a turn, a "passive" is always on
LEADERS: dict[str, tuple[str, str]] = {lead["id"]: (lead["kind"], lead["text"]) for lead in ENGINE.leaders()}
WARLORD, RAIDER, SAGE, ELF, ASSASSIN = "warlord_legend", "raider_legend", "sage_legend", "elf_legend", "assassin_legend"


def power_price(leader_id: str, config: Optional[Config] = None) -> int:
    """What a leader's power costs before any discount."""
    config = config or Config()
    prices = {lead["id"]: lead.get("cost") for lead in _engine_for(None, config).leaders()}
    return prices.get(leader_id) or config.leader_power_cost


def deck_problems(decklist, leader: Optional[str], *, cards: Optional[dict[str, Card]] = None) -> list[str]:
    """What makes a deck illegal; empty when it's legal."""
    return _engine_for(cards, None).deck_problems([str(c) for c in decklist], leader)


# ------------------------------------------------------------------ the map

@dataclass(frozen=True)
class Region:
    id: str
    corners: tuple[str, ...]
    food: int


class GameMap:
    """The board's geometry, as the engine reads data/maps.json: tiles ("row,col"), edges, regions of three tiles, each
    player's base (the tiles in front of their den), the food that wins."""

    def __init__(self, d: dict):
        self.id: str = d["id"]
        self.name: str = d["name"]
        self.win_food: int = d["win_food"]
        self.crossroads = frozenset(d["crossroads"])
        self.edges = tuple((a, b) for a, b in d["edges"])
        self.hq_connects = {p: frozenset(t) for p, t in d["bases"].items()}
        self.regions = {r["id"]: Region(r["id"], tuple(r["corners"]), r["food"]) for r in d["regions"]}
        nb: dict[str, set] = {cr: set() for cr in self.crossroads}
        for a, b in self.edges:
            nb[a].add(b)
            nb[b].add(a)
        self._neighbors = {cr: tuple(sorted(ns)) for cr, ns in nb.items()}

    def neighbors(self, crossroad: str) -> tuple[str, ...]:
        return self._neighbors[crossroad]

    def adjacent(self, a: str, b: str) -> bool:
        return b in self._neighbors.get(a, ())

    def hq_front(self, player: str) -> frozenset[str]:
        return self.hq_connects[player]


_maps: dict[str, GameMap] = {}


def load_map(map_id: str = MAP_ID) -> GameMap:
    if map_id not in _maps:
        _maps[map_id] = GameMap(_call(_engine_of, _CARDS_TEXT, Config(), map_id).map())
    return _maps[map_id]


# ------------------------------------------------------------------ the position

class UnitInstance:
    """One card instance: a card id, its owner and a unique instance id. The same instance moves from hand to board."""

    __slots__ = ("card_id", "owner", "iid", "retaliation_used", "strength_mod", "cost_mod", "made")

    def __init__(self, card_id: str, owner: str, iid: int, retaliation_used: bool = False, strength_mod: int = 0,
                 cost_mod: int = 0, made: bool = False):
        self.card_id = card_id
        self.owner = owner
        self.iid = iid
        self.retaliation_used = retaliation_used   # Spikes: spent on the first enemy that covers it
        self.strength_mod = strength_mod           # what effects have added to its strength, for good (the Hunters' -N)
        self.cost_mod = cost_mod                   # what effects have added to its mana cost while in hand (the Assassin's -1)
        self.made = made                           # made into its owner's hand by an effect both players watched

    def to_dict(self) -> dict:
        return {"card_id": self.card_id, "owner": self.owner, "iid": self.iid, "retaliation_used": self.retaliation_used,
                "strength_mod": self.strength_mod, "cost_mod": self.cost_mod, "made": self.made}

    def _take(self, d: dict) -> "UnitInstance":
        self.card_id, self.owner, self.iid = d["card_id"], d["owner"], d["iid"]
        self.retaliation_used, self.strength_mod, self.cost_mod = d.get("retaliation_used", False), d.get("strength_mod", 0), d.get("cost_mod", 0)
        self.made = d.get("made", False)
        return self

    @staticmethod
    def from_dict(d: dict) -> "UnitInstance":
        return UnitInstance(d["card_id"], d["owner"], d["iid"])._take(d)

    def __repr__(self) -> str:
        return f"UnitInstance({self.card_id!r}, {self.owner!r}, {self.iid})"


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


def _fresh_rng() -> dict:
    version, internal, gauss = random.Random(0).getstate()
    return {"version": version, "state": list(internal), "gauss": gauss}


class GameState:
    """A position. Construct via new_game() or from_dict(), or by hand (a test's bare position). `game_map`, `cards` and
    `config` say which engine plays it and are never saved."""

    def __init__(self, game_map: GameMap, cards: dict[str, Card], config: Config, *,
                 board: dict[str, list[UnitInstance]], hands: dict[str, list[UnitInstance]], decks: dict[str, list[str]],
                 remove_pile: list[str], food: dict[str, int], current: str, first_player: str,
                 rng: Optional[dict] = None, starting_decks: Optional[dict] = None,
                 turn_counter: int = 0, mana_spent: int = 0, applied_this_turn: int = 0, effect_steps_this_turn: int = 0,
                 played_this_turn: int = 0, power_used: bool = False, power_discount: Optional[dict] = None,
                 fatigue: Optional[dict] = None, food_lost: Optional[dict] = None, food_produced: Optional[dict] = None,
                 caps: Optional[list] = None, next_iid: int = 0, effect_stack: Optional[list[dict]] = None,
                 pending: Optional[dict] = None, scheduled: Optional[list[dict]] = None, result: Optional[Result] = None,
                 pile_owners: Optional[list] = None, leaders: Optional[dict[str, dict]] = None):
        self.game_map = game_map
        self.cards = cards
        self.config = config
        self.board = board                 # tile -> stack (bottom..top); the top unit holds the tile
        self.hands = hands                 # player -> list of UnitInstance
        self.decks = decks                 # player -> list of card ids (the top is the end)
        self.starting_decks = starting_decks if starting_decks is not None else {"A": (), "B": ()}
        self.made = {"A": [], "B": []}     # player -> every card an effect made into their hand (public)
        self.remove_pile = remove_pile     # shared and public
        self.pile_owners = pile_owners if pile_owners is not None else [None] * len(remove_pile)   # in step with remove_pile
        self.leaders = leaders if leaders is not None else {}   # player -> {"id": card id}
        self.food = food
        self.current = current
        self.first_player = first_player
        self._rng = rng if rng is not None else _fresh_rng()   # the random stream, as CPython's random.Random saves it
        self.turn_counter = turn_counter
        self.mana_spent = mana_spent       # this turn's mana spent so far
        self.applied_this_turn = applied_this_turn   # every action applied this turn, choices included (the turn's cap)
        self.played_this_turn = played_this_turn     # the cards its player has played from hand this turn (the Assassin)
        self.power_used = power_used                 # its player has used their leader's power this turn (once a turn)
        self.power_discount = power_discount if power_discount is not None else {"A": 0, "B": 0}   # off each player's power, for good (the Sage)
        self.fatigue = fatigue if fatigue is not None else {"A": 0, "B": 0}   # the cards each player tried to draw from their empty deck; the next costs one more food
        self.food_lost = food_lost if food_lost is not None else {"A": 0, "B": 0}   # the food each player has lost this game (the Burn Djinn)
        self.food_produced = food_produced if food_produced is not None else {"A": 0, "B": 0}   # the food each player's regions produced this game (the Food Djinn)
        self.effect_steps_this_turn = effect_steps_this_turn
        self.caps: list = caps if caps is not None else []     # every turn a cap ended: {cap, player, turn, cards}
        self._next_iid = next_iid
        self.effect_stack = effect_stack if effect_stack is not None else []
        self.pending = pending
        self.scheduled = scheduled if scheduled is not None else []   # delayed steps: Poison's removal
        self.result = result
        # What happened, in order: the server hands these to the players. Never saved, and a clone starts empty.
        self.events: list[dict] = []
        self._engine = _engine_for(cards, config, game_map.id)
        self._rs = None        # the engine's position of what this object held at `_rs_dict`
        self._rs_dict = None

    # ---- the position as data
    def new_iid(self) -> int:
        iid = self._next_iid
        self._next_iid += 1
        return iid

    def top_unit(self, cr: str) -> Optional[UnitInstance]:
        stack = self.board.get(cr)
        return stack[-1] if stack else None

    def owner_of(self, cr: str) -> Optional[str]:
        u = self.top_unit(cr)
        return u.owner if u else None

    def player_to_act(self) -> str:
        """The seat that must act next: the pending chooser mid-resolution, else the current player."""
        return self.pending["chooser"] if self.pending is not None else self.current

    def to_dict(self) -> dict:
        return {
            "map_id": self.game_map.id,
            "board": {cr: [u.to_dict() for u in stack] for cr, stack in self.board.items() if stack},
            "hands": {p: [u.to_dict() for u in h] for p, h in self.hands.items()},
            "decks": {p: list(d) for p, d in self.decks.items()},
            "starting_decks": {p: list(d) for p, d in self.starting_decks.items()},
            "made": {p: list(m) for p, m in self.made.items()},
            "remove_pile": list(self.remove_pile),
            "pile_owners": list(self.pile_owners),
            "leaders": {p: dict(lead) for p, lead in sorted(self.leaders.items())},
            "food": dict(self.food),
            "current": self.current,
            "first_player": self.first_player,
            "rng": {**self._rng, "state": list(self._rng["state"])},
            "turn_counter": self.turn_counter,
            "mana_spent": self.mana_spent,
            "applied_this_turn": self.applied_this_turn,
            "played_this_turn": self.played_this_turn,
            "power_used": self.power_used,
            "power_discount": dict(self.power_discount),
            "fatigue": dict(self.fatigue),
            "food_lost": dict(self.food_lost),
            "food_produced": dict(self.food_produced),
            "effect_steps_this_turn": self.effect_steps_this_turn,
            "caps": [dict(c) for c in self.caps],
            "next_iid": self._next_iid,
            "effect_stack": json.loads(json.dumps(self.effect_stack)),
            "pending": json.loads(json.dumps(self.pending)),
            "scheduled": json.loads(json.dumps(self.scheduled)),
            "result": self.result.to_dict() if self.result else None,
        }

    @staticmethod
    def from_dict(d: dict, *, cards: Optional[dict[str, Card]] = None, config: Optional[Config] = None) -> "GameState":
        """A saved position. Raises EngineError when the engine can't read it (a card that no longer exists)."""
        s = GameState(load_map(d["map_id"]), cards if cards is not None else CARDS, config or Config(), board={},
                      hands={"A": [], "B": []}, decks={"A": [], "B": []}, remove_pile=[], food={"A": 0, "B": 0},
                      current="A", first_player="A")
        rs = _call(s._engine.from_dict, d)
        s._load(rs.to_dict())
        s._rs = rs
        return s

    def clone(self) -> "GameState":
        """An independent copy: mutating it never touches the original."""
        return GameState.from_dict(self.to_dict(), cards=self.cards, config=self.config)

    def view_for(self, player: str) -> SimpleNamespace:
        """What one seat may see: the opponent's hand and both decks as counts only."""
        return SimpleNamespace(**self._sync().view_for(player))

    # ---- the engine's side
    def _sync(self):
        """The engine's position of what this object holds now."""
        d = self.to_dict()
        if self._rs is None or d != self._rs_dict:
            self._rs = _call(self._engine.from_dict, d)
            self._rs_dict = d
        return self._rs

    def _load(self, d: dict) -> None:
        """Take the position `d` (the engine's, after a move), keeping the unit objects a caller may hold."""
        known = {u.iid: u for stack in self.board.values() for u in stack}
        known.update((u.iid, u) for h in self.hands.values() for u in h)

        def unit(x: dict) -> UnitInstance:
            u = known.get(x["iid"])
            return u._take(x) if u is not None else UnitInstance.from_dict(x)

        board = {cr: [unit(x) for x in stack] for cr, stack in d["board"].items()}
        self.board.clear()
        self.board.update(board)
        for p in "AB":
            self.hands.setdefault(p, [])[:] = [unit(x) for x in d["hands"][p]]
            self.decks.setdefault(p, [])[:] = d["decks"][p]
        self.starting_decks = {p: tuple(dk) for p, dk in d["starting_decks"].items()}
        self.made = {p: list(m) for p, m in d.get("made", {"A": [], "B": []}).items()}
        self.remove_pile[:] = d["remove_pile"]
        self.pile_owners[:] = d["pile_owners"]
        self.leaders.clear()
        self.leaders.update({p: {"id": lead["id"]} for p, lead in d["leaders"].items()})
        self.food.update(d["food"])
        self.current, self.first_player, self._rng = d["current"], d["first_player"], d["rng"]
        self.turn_counter, self.mana_spent, self.applied_this_turn = d["turn_counter"], d["mana_spent"], d["applied_this_turn"]
        self.played_this_turn, self.power_used = d["played_this_turn"], d["power_used"]
        self.power_discount.update(d["power_discount"])
        self.fatigue.update(d["fatigue"])
        self.food_lost.update(d.get("food_lost", {"A": 0, "B": 0}))
        self.food_produced.update(d.get("food_produced", {"A": 0, "B": 0}))
        self.effect_steps_this_turn, self._next_iid = d["effect_steps_this_turn"], d["next_iid"]
        self.caps[:] = d["caps"]
        self.effect_stack[:] = d["effect_stack"]
        self.pending = d["pending"]
        self.scheduled[:] = d["scheduled"]
        self.result = Result.from_dict(d["result"]) if d["result"] else None
        self._rs_dict = self.to_dict()

    def _move(self, do) -> None:
        """Run one change of the position in the engine, and take what it left: the position and its events."""
        rs = self._sync()
        rs.record_events(True)
        try:
            do(rs)
        except (ValueError, RuntimeError) as e:
            self._rs = None      # whatever the engine did before it refused is dropped: this object still holds the position
            raise EngineError(str(e)) from None
        self.events += rs.take_events()
        rs.record_events(False)
        self._load(rs.to_dict())


def new_game(deck_a: list[str], deck_b: list[str], seed: int, *, cards: Optional[dict[str, Card]] = None,
             config: Optional[Config] = None, first_player: Optional[str] = None,
             leaders: Optional[dict] = None, map_id: str = MAP_ID) -> GameState:
    """A fresh game: both decks shuffled, the first player by coin flip (or `first_player`), the opening hands dealt and
    the mulligan waiting. `leaders`: player -> their deck's leader's card id."""
    cards = cards if cards is not None else CARDS
    config = config or Config()
    rs = _call(_engine_for(cards, config, map_id).new_game, list(deck_a), list(deck_b), seed, first_player, leaders)
    return GameState.from_dict(rs.to_dict(), cards=cards, config=config)


# ------------------------------------------------------------------ the rules, asked of the engine

def legal_actions(state: GameState) -> list[Action]:
    """Every legal action for the player to act; ending the turn only when nothing else is. Empty once the game is over."""
    return [action_from_dict(a) for a in state._sync().legal_actions()]


def can_pass(state: GameState) -> bool:
    """Ending the turn is legal whenever nothing is resolving."""
    return state._sync().can_pass()


def apply_action(state: GameState, action, *, validate: bool = True) -> GameState:
    """Apply one action (a play, the leader's power, ending the turn, or a pending choice). Raises EngineError unless it
    is legal."""
    state._move(lambda rs: rs.apply_action(_adict(action), validate))
    return state


def apply_logged(state: GameState, adict: dict) -> None:
    """Apply one action as a game log records it: one marked "by" a player is their mulligan choice made while the other
    was choosing theirs."""
    state._move(lambda rs: rs.apply_logged(adict))


def early_mulligan(state: GameState, player: str) -> Optional[int]:
    """Where `player`'s mulligan waits under the one being chosen now (its index on the effect stack), else None: both
    players mulligan at once."""
    return state._sync().early_mulligan(player)


def apply_early_mulligan(state: GameState, player: str, action) -> None:
    state._move(lambda rs: rs.apply_early_mulligan(player, _adict(action)))


def is_terminal(state: GameState) -> Optional[Result]:
    r = state._sync().is_terminal()
    return Result.from_dict(r) if r else None


def own_turn_number(state: GameState, player: str) -> int:
    return state._sync().own_turn_number(player)


def mana_total(state: GameState, player: str) -> int:
    return state._sync().mana_total(player)


def mana_left(state: GameState, player: str) -> int:
    return state._sync().mana_left(player)


def region_income(state: GameState, player: str) -> int:
    return state._sync().region_income(player)


def mulligan_cap(state: GameState, player: str) -> int:
    """The cards `player` may return in the mulligan."""
    return state._sync().mulligan_cap(player)


def mana_cost(state: GameState, card_id: str, player: Optional[str] = None) -> int:
    """What playing `card_id` from hand costs `player` (the current player by default)."""
    return _call(state._sync().mana_cost, card_id, player)


def unit_cost(state: GameState, unit: UnitInstance) -> int:
    """What playing this copy from hand costs."""
    return _unit(state, unit)["cost"]


def power_cost(state: GameState, player: str) -> int:
    return state._sync().power_cost(player)


def leader_usable(state: GameState, player: str) -> bool:
    return state._sync().leader_usable(player)


def card_strength(state: GameState, card_id: str, owner: str) -> int:
    """The strength a unit of `card_id` has for `owner` now: on the board, or as it would be played from hand."""
    return _call(state._sync().card_strength, card_id, owner)


def _unit(state: GameState, unit: UnitInstance) -> dict:
    v = state._sync().unit_view(unit.iid)
    if v is None:
        raise EngineError(f"{unit!r} is neither on the board nor in a hand")
    return v


def effective_strength(state: GameState, unit: UnitInstance) -> int:
    return _unit(state, unit)["str"]


def has_keyword(state: GameState, unit: UnitInstance, kw: str) -> bool:
    return kw in state.cards[unit.card_id].keywords


def can_be_removed(state: GameState, unit: UnitInstance) -> bool:
    """Armor: no ability removes it."""
    return not _unit(state, unit)["armor"]


def can_be_chosen(state: GameState, unit: UnitInstance, by_player: str) -> bool:
    """Stealth: an enemy's ability can't choose it."""
    return by_player == unit.owner or not _unit(state, unit)["hidden"]


def unit_marks(state: GameState, unit: UnitInstance) -> dict:
    """How a unit stands: {"str", "cost", "hidden", "spikes", "poison", "armor"}."""
    return _unit(state, unit)
