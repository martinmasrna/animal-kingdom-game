"""Game state: the mutable position plus setup, cloning, serialization, and per-seat views.

State model (plan decision 4): **mutate-in-place + explicit clone()**. `apply_action`
(rules.py) mutates a GameState; callers that need to branch (sims, lookahead) call
`clone()` first. Guardrails against aliasing bugs:
  (a) UnitInstance is immutable-by-convention (set at creation, never mutated);
  (b) view_for(player) returns a genuinely read-only projection;
  (c) a clone-independence test (tests/).

Choice model (plan decision 6 - extensive form): a turn is a sequence of decision
points. M1 has no mid-turn choices, but the *seams* are built in now so M2 slots in
without reworking the action/bot contract:
  - `effect_stack`  : declarative effect steps still to resolve (empty in M1);
  - `pending`       : the choice currently awaiting an action, or None (None in M1);
  - turn advancement is gated on "stack empty & nothing pending" (see rules.py).

Randomness is a **carried seeded RNG** (`rng`): used by setup and by chance effects
(e.g. Black Swan's random discard, filtered random draws). It is serialized and cloned,
so games replay identically from (seed, action sequence) even with chance events.
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
    """One card instance: a card id + owner + unique instance id. Lives in a hand and then
    on the board - the *same* instance moves hand->board on placement, carrying its counter.

    Mostly set-once, but `strength_counter` and `placed_on_turn` are mutated during play
    (decision E: "give +X" counters are stored on the instance, including hand instances).
    Because instances are now mutable, `GameState.clone()` deep-copies them (it no longer
    shares them by reference). Base/dynamic strength is NOT stored here - it is derived from
    the Card registry and board state via strength.effective_strength; the counter is added.
    """

    __slots__ = ("card_id", "owner", "iid", "placed_on_turn", "strength_counter", "locked_until_turn",
                 "retaliation_used")

    def __init__(self, card_id: str, owner: str, iid: int, placed_on_turn: int = 0,
                 strength_counter: int = 0, locked_until_turn: int = 0, retaliation_used: bool = False):
        self.card_id = card_id
        self.owner = owner
        self.iid = iid
        self.placed_on_turn = placed_on_turn  # turn_counter at placement (Egg timing); 0 in hand
        self.strength_counter = strength_counter  # stored "give +X" buffs (signed); travels hand->board
        self.locked_until_turn = locked_until_turn  # Skunk: unplayable from hand while turn < this
        self.retaliation_used = retaliation_used  # Gale: "first time covered" fires once per instance

    def to_dict(self) -> dict:
        return {"card_id": self.card_id, "owner": self.owner, "iid": self.iid,
                "placed_on_turn": self.placed_on_turn, "strength_counter": self.strength_counter,
                "locked_until_turn": self.locked_until_turn, "retaliation_used": self.retaliation_used}

    @staticmethod
    def from_dict(d: dict) -> "UnitInstance":
        return UnitInstance(d["card_id"], d["owner"], d["iid"], d.get("placed_on_turn", 0),
                            d.get("strength_counter", 0), d.get("locked_until_turn", 0),
                            d.get("retaliation_used", False))

    def __repr__(self) -> str:
        c = f", +{self.strength_counter}" if self.strength_counter else ""
        return f"UnitInstance({self.card_id!r}, {self.owner!r}, {self.iid}{c})"


def _copy_unit(u: UnitInstance) -> UnitInstance:
    """An independent copy of a unit instance (used by clone, now that instances mutate)."""
    return UnitInstance(u.card_id, u.owner, u.iid, u.placed_on_turn, u.strength_counter,
                        u.locked_until_turn, u.retaliation_used)


def _plain_copy(v):
    """A deep copy specialised for the effect-model containers (effect_stack, pending,
    scheduled, turn_flags, card_strength_counters). Those hold only JSON-shaped plain data
    - nested dict/list/tuple of str/int/float/bool/None - so a typed recursive copy is
    exactly equivalent to `copy.deepcopy` here, but skips deepcopy's generic memo/id
    bookkeeping (the search clones states millions of times; deepcopy dominated the profile).
    Anything unexpected falls back to `copy.deepcopy`, so correctness never depends on the
    plain-data assumption holding."""
    t = type(v)
    if t is dict:
        return {k: _plain_copy(x) for k, x in v.items()}
    if t is list:
        return [_plain_copy(x) for x in v]
    if t is tuple:
        return tuple(_plain_copy(x) for x in v)
    if v is None or t is str or t is int or t is float or t is bool:
        return v
    return copy.deepcopy(v)


def _copy_rng(rng: random.Random) -> random.Random:
    """An independent RNG at the same position. `random.Random()` reads OS entropy on
    construction only to have it immediately overwritten by `setstate`; bypass __init__ via
    __new__ so the throwaway seed (a top profile entry) is never drawn."""
    new = random.Random.__new__(random.Random)
    new.setstate(rng.getstate())
    return new


@dataclass(frozen=True)
class Result:
    """Terminal game outcome. winner is 'A'/'B', or None for a draw."""

    winner: Optional[str]
    reason: str  # "hq_capture" | "food" | "exhaustion" | "max_turns"

    def to_dict(self) -> dict:
        return {"winner": self.winner, "reason": self.reason}

    @staticmethod
    def from_dict(d: dict) -> "Result":
        return Result(d["winner"], d["reason"])


@dataclass(frozen=True)
class StateView:
    """Read-only, per-seat projection of the state (guardrail b, handoff §4.5).

    Hidden information is stripped: the opponent's hand contents and both decks'
    order/contents become counts only. Board, the Remove Pile, and food totals are public.
    All containers are immutable (tuples / MappingProxy) so a bot cannot mutate the
    live game through its view. `pending` (when present) is what this seat must decide.
    """

    player: str
    to_act: str
    current: str
    turn_counter: int
    board: Mapping[str, tuple[tuple[str, str], ...]]  # cr -> ((card_id, owner) bottom->top)
    own_hand: tuple[str, ...]
    opponent_hand_count: int
    own_deck_count: int
    opponent_deck_count: int
    remove_pile: tuple[str, ...]
    food: Mapping[str, int]
    card_strength_counters: Mapping[str, Mapping[str, int]]
    pending: Optional[Mapping[str, Any]]
    result: Optional[Result]

    def to_dict(self) -> dict:
        """Return a JSON-safe snapshot of exactly what this player may observe."""
        return {
            "player": self.player,
            "to_act": self.to_act,
            "current": self.current,
            "turn_counter": self.turn_counter,
            "board": {
                cr: [list(unit) for unit in stack]
                for cr, stack in self.board.items()
            },
            "own_hand": list(self.own_hand),
            "opponent_hand_count": self.opponent_hand_count,
            "own_deck_count": self.own_deck_count,
            "opponent_deck_count": self.opponent_deck_count,
            "remove_pile": list(self.remove_pile),
            "food": dict(self.food),
            "card_strength_counters": {
                player: dict(counters)
                for player, counters in self.card_strength_counters.items()
            },
            "pending": copy.deepcopy(dict(self.pending)) if self.pending else None,
            "result": self.result.to_dict() if self.result else None,
        }


def _rng_to_dict(rng: random.Random) -> dict:
    version, internal, gauss = rng.getstate()
    return {"version": version, "state": list(internal), "gauss": gauss}


def _rng_from_dict(d: dict) -> random.Random:
    rng = random.Random()
    rng.setstate((d["version"], tuple(d["state"]), d["gauss"]))
    return rng


class GameState:
    """The full mutable position. Construct via new_game() or from_dict().

    `game_map`, `cards`, and `config` are shared immutable singletons - referenced, never
    cloned or serialized (rebuilt on load). Everything else is per-game state.
    """

    def __init__(
        self,
        game_map: GameMap,
        cards: dict[str, Card],
        config: Config,
        *,
        board: dict[str, list[UnitInstance]],
        hands: dict[str, list[UnitInstance]],
        decks: dict[str, list[str]],
        remove_pile: list[str],
        food: dict[str, int],
        current: str,
        first_player: str,
        rng: Optional[random.Random] = None,
        starting_decks: Optional[dict[str, tuple]] = None,
        turn_counter: int = 0,
        units_placed_this_turn: int = 0,
        actions_taken_this_turn: int = 0,
        next_iid: int = 0,
        effect_stack: Optional[list[dict]] = None,
        pending: Optional[dict] = None,
        scheduled: Optional[list[dict]] = None,
        turn_flags: Optional[dict] = None,
        card_strength_counters: Optional[dict[str, dict[str, int]]] = None,
        rodent_played_turn: Optional[dict[str, int]] = None,
        result: Optional[Result] = None,
    ):
        self.game_map = game_map
        self.cards = cards
        self.config = config
        self.board = board                 # cr -> stack (bottom..top); top = visible/controls
        self.hands = hands                 # player -> list of UnitInstance (carry counters)
        self.decks = decks                 # player -> list of card ids (top = last, O(1) pop)
        # The fixed 30-card starting decklists (immutable tuples), read by Oxpecker (F12).
        self.starting_decks = starting_decks if starting_decks is not None else {"A": (), "B": ()}
        self.remove_pile = remove_pile     # shared, public (formerly "discard")
        self.food = food
        self.current = current
        self.first_player = first_player
        self.rng = rng if rng is not None else random.Random()
        self.turn_counter = turn_counter
        self.units_placed_this_turn = units_placed_this_turn
        self.actions_taken_this_turn = actions_taken_this_turn
        self._next_iid = next_iid
        # Decision-point + effect machinery (decision 6).
        self.effect_stack = effect_stack if effect_stack is not None else []  # op-steps to resolve
        self.pending = pending                                   # current choice awaiting an action
        self.scheduled = scheduled if scheduled is not None else []  # delayed effects (Egg/Bear/Rabbit)
        self.turn_flags = turn_flags if turn_flags is not None else {}  # once-per-turn trigger flags
        # Persistent per-player/card growth that applies in every zone (Rattlesnake).
        self.card_strength_counters = (
            card_strength_counters if card_strength_counters is not None else {"A": {}, "B": {}}
        )
        # player -> turn_counter they last placed a Rodent (Gopher's "last turn" payoff).
        self.rodent_played_turn = rodent_played_turn if rodent_played_turn is not None else {}
        self.result = result

    # --- instance ids ---
    def new_iid(self) -> int:
        iid = self._next_iid
        self._next_iid += 1
        return iid

    # --- card movement ---
    def draw(self, player: str, n: int) -> list["UnitInstance"]:
        """Move up to n cards from the top of `player`'s deck (its end) into their hand.

        Each drawn card becomes a fresh UnitInstance (counter 0), so a future "give +X" in
        hand attaches to it. Returns the instances drawn (so on-draw triggers can see them).
        """
        deck, hand = self.decks[player], self.hands[player]
        drawn: list[UnitInstance] = []
        for _ in range(min(n, len(deck))):
            inst = UnitInstance(deck.pop(), player, self.new_iid())
            hand.append(inst)
            drawn.append(inst)
        return drawn

    def add_to_hand(self, player: str, card_id: str, *, strength_counter: int = 0) -> "UnitInstance":
        """Create a fresh hand instance of `card_id` for `player` (test setup, Opossum return)."""
        inst = UnitInstance(card_id, player, self.new_iid(), strength_counter=strength_counter)
        self.hands[player].append(inst)
        return inst

    # --- board queries (shared by rules and effects, hence here on the state) ---
    def top_unit(self, cr: str) -> Optional["UnitInstance"]:
        """The visible (top) unit on a crossroad, or None if empty."""
        stack = self.board.get(cr)
        return stack[-1] if stack else None

    def owner_of(self, cr: str) -> Optional[str]:
        """The player controlling a crossroad (owner of its top unit), or None."""
        u = self.top_unit(cr)
        return u.owner if u else None

    def connected_occupied(self, player: str) -> set:
        """Player-occupied crossroads connected to the player's HQ (overview.md §8)."""
        gm = self.game_map
        board = self.board
        # owner_of(cr) == player, inlined: this BFS is the top search hot path, so skip the
        # owner_of -> top_unit -> board.get call chain per node (empty stack is falsy = None).
        seeds = [cr for cr in gm.hq_front(player)
                 if (st := board.get(cr)) and st[-1].owner == player]
        seen, queue = set(seeds), deque(seeds)
        while queue:
            cr = queue.popleft()
            for nb in gm.neighbors(cr):
                if nb not in seen and (st := board.get(nb)) and st[-1].owner == player:
                    seen.add(nb)
                    queue.append(nb)
        return seen

    def is_connected(self, player: str, cr: str, occ: Optional[set] = None) -> bool:
        """Whether `cr` is a connection-legal placement for `player` (HQ graph only).

        Static bypasses (Flight, Cougar) are layered on top in legal_actions, not here.
        """
        gm = self.game_map
        if cr in gm.hq_front(player):
            return True
        if occ is None:
            occ = self.connected_occupied(player)
        return cr in occ or any(nb in occ for nb in gm.neighbors(cr))

    # --- whose decision is it ---
    def player_to_act(self) -> str:
        """The seat that must act next: the pending chooser if mid-resolution, else current."""
        if self.pending is not None:
            return self.pending["chooser"]
        return self.current

    # --- branching ---
    def clone(self) -> "GameState":
        """An independent copy: mutating the clone never touches the original.

        Containers are freshly built; the map/card/config singletons are shared by
        reference (immutable). UnitInstances are now mutable (strength counters), so they
        are **copied** - board and hand instances in the clone are independent of the
        original. The RNG is copied to its own independent stream at the same position.
        """
        new = GameState.__new__(GameState)
        new.game_map = self.game_map
        new.cards = self.cards
        new.config = self.config
        new.board = {cr: [_copy_unit(u) for u in stack] for cr, stack in self.board.items()}
        new.hands = {p: [_copy_unit(u) for u in h] for p, h in self.hands.items()}
        new.decks = {p: list(d) for p, d in self.decks.items()}
        new.starting_decks = self.starting_decks   # immutable tuples - safe to share
        new.remove_pile = list(self.remove_pile)
        new.food = dict(self.food)
        new.current = self.current
        new.first_player = self.first_player
        new.rng = _copy_rng(self.rng)  # independent RNG, same position
        new.turn_counter = self.turn_counter
        new.units_placed_this_turn = self.units_placed_this_turn
        new.actions_taken_this_turn = self.actions_taken_this_turn
        new._next_iid = self._next_iid
        new.effect_stack = _plain_copy(self.effect_stack)
        new.pending = _plain_copy(self.pending)
        new.scheduled = _plain_copy(self.scheduled)
        new.turn_flags = _plain_copy(self.turn_flags)
        new.card_strength_counters = _plain_copy(self.card_strength_counters)
        new.rodent_played_turn = dict(self.rodent_played_turn)
        new.result = self.result  # Result is frozen/immutable - safe to share
        return new

    # --- per-seat view ---
    def view_for(self, player: str) -> StateView:
        opp = other_player(player)
        board = {
            cr: tuple((u.card_id, u.owner) for u in stack)
            for cr, stack in self.board.items()
        }
        return StateView(
            player=player,
            to_act=self.player_to_act(),
            current=self.current,
            turn_counter=self.turn_counter,
            board=MappingProxyType(board),
            own_hand=tuple(u.card_id for u in self.hands[player]),
            opponent_hand_count=len(self.hands[opp]),
            own_deck_count=len(self.decks[player]),
            opponent_deck_count=len(self.decks[opp]),
            remove_pile=tuple(self.remove_pile),
            food=MappingProxyType(dict(self.food)),
            card_strength_counters=MappingProxyType({
                p: MappingProxyType(dict(counters))
                for p, counters in self.card_strength_counters.items()
            }),
            pending=MappingProxyType(copy.deepcopy(self.pending)) if self.pending else None,
            result=self.result,
        )

    # --- serialization ---
    def to_dict(self) -> dict:
        return {
            "map_id": self.game_map.id,
            "board": {cr: [u.to_dict() for u in stack] for cr, stack in self.board.items()},
            "hands": {p: [u.to_dict() for u in h] for p, h in self.hands.items()},
            "decks": {p: list(d) for p, d in self.decks.items()},
            "starting_decks": {p: list(d) for p, d in self.starting_decks.items()},
            "remove_pile": list(self.remove_pile),
            "food": dict(self.food),
            "current": self.current,
            "first_player": self.first_player,
            "rng": _rng_to_dict(self.rng),
            "turn_counter": self.turn_counter,
            "units_placed_this_turn": self.units_placed_this_turn,
            "actions_taken_this_turn": self.actions_taken_this_turn,
            "next_iid": self._next_iid,
            "effect_stack": copy.deepcopy(self.effect_stack),
            "pending": copy.deepcopy(self.pending),
            "scheduled": copy.deepcopy(self.scheduled),
            "turn_flags": copy.deepcopy(self.turn_flags),
            "card_strength_counters": copy.deepcopy(self.card_strength_counters),
            "rodent_played_turn": dict(self.rodent_played_turn),
            "result": self.result.to_dict() if self.result else None,
        }

    @staticmethod
    def from_dict(
        d: dict,
        *,
        cards: Optional[dict[str, Card]] = None,
        config: Optional[Config] = None,
    ) -> "GameState":
        cards = cards or load_cards()
        config = config or Config.default()
        game_map = load_map(d["map_id"])
        board = {
            cr: [UnitInstance.from_dict(u) for u in stack]
            for cr, stack in d["board"].items()
        }
        return GameState(
            game_map,
            cards,
            config,
            board=board,
            hands={p: [UnitInstance.from_dict(u) for u in h] for p, h in d["hands"].items()},
            decks={p: list(dk) for p, dk in d["decks"].items()},
            starting_decks={p: tuple(dk) for p, dk in d.get("starting_decks", {}).items()},
            remove_pile=list(d["remove_pile"]),
            food=dict(d["food"]),
            current=d["current"],
            first_player=d["first_player"],
            rng=_rng_from_dict(d["rng"]),
            turn_counter=d["turn_counter"],
            units_placed_this_turn=d["units_placed_this_turn"],
            actions_taken_this_turn=d.get("actions_taken_this_turn", 0),
            next_iid=d["next_iid"],
            effect_stack=copy.deepcopy(d.get("effect_stack") or []),
            pending=copy.deepcopy(d.get("pending")),
            scheduled=copy.deepcopy(d.get("scheduled") or []),
            turn_flags=copy.deepcopy(d.get("turn_flags") or {}),
            card_strength_counters=copy.deepcopy(
                d.get("card_strength_counters") or {"A": {}, "B": {}}
            ),
            rodent_played_turn=copy.deepcopy(d.get("rodent_played_turn") or {}),
            result=Result.from_dict(d["result"]) if d["result"] else None,
        )


def new_game(
    deck_a: list[str],
    deck_b: list[str],
    seed: int,
    *,
    map_id: str = "map_b",
    cards: Optional[dict[str, Card]] = None,
    config: Optional[Config] = None,
    first_player: Optional[str] = None,
) -> GameState:
    """Set up a fresh game: shuffle decks, pick first player, deal opening hands.

    The seeded RNG created here is carried on the state, so later chance effects stay
    reproducible. `deck_a`/`deck_b` are lists of card ids (order is irrelevant - shuffled).
    `first_player`, if given ("A"/"B"), forces who goes first instead of the coin flip below -
    the RNG is still drawn from so the rest of the stream (shuffles already happened, later
    chance effects) is identical either way.
    """
    rng = random.Random(seed)
    cards = cards or load_cards()
    config = config or Config.default()
    game_map = load_map(map_id)

    decks = {"A": list(deck_a), "B": list(deck_b)}
    starting_decks = {"A": tuple(deck_a), "B": tuple(deck_b)}  # the fixed lists, for Oxpecker (F12)
    rng.shuffle(decks["A"])
    rng.shuffle(decks["B"])

    coin_flip = "A" if rng.random() < 0.5 else "B"  # coin flip via injected seed
    first = first_player if first_player is not None else coin_flip
    second = other_player(first)

    state = GameState(
        game_map,
        cards,
        config,
        board={},
        hands={"A": [], "B": []},
        decks=decks,
        remove_pile=[],
        food={"A": 0, "B": 0},
        current=first,
        first_player=first,
        rng=rng,
        starting_decks=starting_decks,
    )
    state.draw(first, config.first_player_opening_draw)
    state.draw(second, config.second_player_opening_draw)
    return state
