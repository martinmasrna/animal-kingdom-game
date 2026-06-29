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

Randomness is a **carried seeded RNG** (`rng`): used by setup and by future chance
effects (e.g. Raccoon's random discard). It is serialized and cloned, so games replay
identically from (seed, action sequence) even with chance events.
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
    """One unit in play: a card id + owner + unique instance id.

    Immutable-by-convention (guardrail a): fields are set once and never mutated, so
    sharing instances across cloned states is safe. Strength is NOT stored here - it is
    derived from the Card registry (and, in M2, from board state) via effective_strength.
    """

    __slots__ = ("card_id", "owner", "iid", "placed_on_turn")

    def __init__(self, card_id: str, owner: str, iid: int, placed_on_turn: int = 0):
        self.card_id = card_id
        self.owner = owner
        self.iid = iid
        self.placed_on_turn = placed_on_turn  # turn_counter at placement (Armadillo/Egg timing)

    def to_dict(self) -> dict:
        return {"card_id": self.card_id, "owner": self.owner, "iid": self.iid,
                "placed_on_turn": self.placed_on_turn}

    @staticmethod
    def from_dict(d: dict) -> "UnitInstance":
        return UnitInstance(d["card_id"], d["owner"], d["iid"], d.get("placed_on_turn", 0))

    def __repr__(self) -> str:
        return f"UnitInstance({self.card_id!r}, {self.owner!r}, {self.iid})"


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
    order/contents become counts only. Board, discard, and food totals are public.
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
    discard: tuple[str, ...]
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
        hands: dict[str, list[str]],
        decks: dict[str, list[str]],
        discard: list[str],
        food: dict[str, int],
        current: str,
        first_player: str,
        rng: Optional[random.Random] = None,
        turn_counter: int = 0,
        units_placed_this_turn: int = 0,
        next_iid: int = 0,
        effect_stack: Optional[list[dict]] = None,
        pending: Optional[dict] = None,
        scheduled: Optional[list[dict]] = None,
        turn_flags: Optional[dict] = None,
        result: Optional[Result] = None,
    ):
        self.game_map = game_map
        self.cards = cards
        self.config = config
        self.board = board                 # cr -> stack (bottom..top); top = visible/controls
        self.hands = hands                 # player -> list of card ids
        self.decks = decks                 # player -> list of card ids (top = last, O(1) pop)
        self.discard = discard             # shared, public
        self.food = food
        self.current = current
        self.first_player = first_player
        self.rng = rng if rng is not None else random.Random()
        self.turn_counter = turn_counter
        self.units_placed_this_turn = units_placed_this_turn
        self._next_iid = next_iid
        # Decision-point + effect machinery (decision 6).
        self.effect_stack = effect_stack if effect_stack is not None else []  # op-steps to resolve
        self.pending = pending                                   # current choice awaiting an action
        self.scheduled = scheduled if scheduled is not None else []  # delayed effects (Egg/Bear/Rabbit)
        self.turn_flags = turn_flags if turn_flags is not None else {}  # once-per-turn trigger flags
        self.result = result

    # --- instance ids ---
    def new_iid(self) -> int:
        iid = self._next_iid
        self._next_iid += 1
        return iid

    # --- card movement ---
    def draw(self, player: str, n: int) -> None:
        """Move up to n cards from the top of `player`'s deck (its end) into their hand."""
        deck, hand = self.decks[player], self.hands[player]
        for _ in range(min(n, len(deck))):
            hand.append(deck.pop())

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
        seeds = [cr for cr in gm.hq_front(player) if self.owner_of(cr) == player]
        seen, queue = set(seeds), deque(seeds)
        while queue:
            cr = queue.popleft()
            for nb in gm.neighbors(cr):
                if nb not in seen and self.owner_of(nb) == player:
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

        Containers are freshly built; UnitInstances and the map/card/config singletons
        are shared by reference (all immutable-by-convention, so sharing is safe). The
        RNG is copied to its own independent stream at the same position.
        """
        new = GameState.__new__(GameState)
        new.game_map = self.game_map
        new.cards = self.cards
        new.config = self.config
        new.board = {cr: list(stack) for cr, stack in self.board.items()}
        new.hands = {p: list(h) for p, h in self.hands.items()}
        new.decks = {p: list(d) for p, d in self.decks.items()}
        new.discard = list(self.discard)
        new.food = dict(self.food)
        new.current = self.current
        new.first_player = self.first_player
        new.rng = random.Random()
        new.rng.setstate(self.rng.getstate())  # independent RNG, same position
        new.turn_counter = self.turn_counter
        new.units_placed_this_turn = self.units_placed_this_turn
        new._next_iid = self._next_iid
        new.effect_stack = copy.deepcopy(self.effect_stack)
        new.pending = copy.deepcopy(self.pending)
        new.scheduled = copy.deepcopy(self.scheduled)
        new.turn_flags = copy.deepcopy(self.turn_flags)
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
            own_hand=tuple(self.hands[player]),
            opponent_hand_count=len(self.hands[opp]),
            own_deck_count=len(self.decks[player]),
            opponent_deck_count=len(self.decks[opp]),
            discard=tuple(self.discard),
            food=MappingProxyType(dict(self.food)),
            pending=MappingProxyType(copy.deepcopy(self.pending)) if self.pending else None,
            result=self.result,
        )

    # --- serialization ---
    def to_dict(self) -> dict:
        return {
            "map_id": self.game_map.id,
            "board": {cr: [u.to_dict() for u in stack] for cr, stack in self.board.items()},
            "hands": {p: list(h) for p, h in self.hands.items()},
            "decks": {p: list(d) for p, d in self.decks.items()},
            "discard": list(self.discard),
            "food": dict(self.food),
            "current": self.current,
            "first_player": self.first_player,
            "rng": _rng_to_dict(self.rng),
            "turn_counter": self.turn_counter,
            "units_placed_this_turn": self.units_placed_this_turn,
            "next_iid": self._next_iid,
            "effect_stack": copy.deepcopy(self.effect_stack),
            "pending": copy.deepcopy(self.pending),
            "scheduled": copy.deepcopy(self.scheduled),
            "turn_flags": copy.deepcopy(self.turn_flags),
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
            hands={p: list(h) for p, h in d["hands"].items()},
            decks={p: list(dk) for p, dk in d["decks"].items()},
            discard=list(d["discard"]),
            food=dict(d["food"]),
            current=d["current"],
            first_player=d["first_player"],
            rng=_rng_from_dict(d["rng"]),
            turn_counter=d["turn_counter"],
            units_placed_this_turn=d["units_placed_this_turn"],
            next_iid=d["next_iid"],
            effect_stack=copy.deepcopy(d.get("effect_stack") or []),
            pending=copy.deepcopy(d.get("pending")),
            scheduled=copy.deepcopy(d.get("scheduled") or []),
            turn_flags=copy.deepcopy(d.get("turn_flags") or {}),
            result=Result.from_dict(d["result"]) if d["result"] else None,
        )


def new_game(
    deck_a: list[str],
    deck_b: list[str],
    seed: int,
    *,
    map_id: str = "map_a",
    cards: Optional[dict[str, Card]] = None,
    config: Optional[Config] = None,
) -> GameState:
    """Set up a fresh game: shuffle decks, pick first player, deal opening hands.

    The seeded RNG created here is carried on the state, so later chance effects stay
    reproducible. `deck_a`/`deck_b` are lists of card ids (order is irrelevant - shuffled).
    """
    rng = random.Random(seed)
    cards = cards or load_cards()
    config = config or Config.default()
    game_map = load_map(map_id)

    decks = {"A": list(deck_a), "B": list(deck_b)}
    rng.shuffle(decks["A"])
    rng.shuffle(decks["B"])

    first = "A" if rng.random() < 0.5 else "B"  # coin flip via injected seed
    second = other_player(first)

    state = GameState(
        game_map,
        cards,
        config,
        board={},
        hands={"A": [], "B": []},
        decks=decks,
        discard=[],
        food={"A": 0, "B": 0},
        current=first,
        first_player=first,
        rng=rng,
    )
    state.draw(first, config.first_player_opening_draw)
    state.draw(second, config.second_player_opening_draw)
    return state
