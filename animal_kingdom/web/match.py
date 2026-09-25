"""A best-of-3 match over the engine: seats, series score, move history, and per-seat views.

Transport-free: the server feeds it actions and reads views; nothing here does I/O. A view
carries only what that seat may see (open decklists, public board and Remove Pile, its own
hand); the opponent's hand and both deck orders never leave this module.
"""

from __future__ import annotations

import random
import secrets
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..bots.greedy_bot import GreedyBot
from ..bots.referee_bot import RefereeBot
from ..bots.turn_bot import TurnBot
from ..decks import PREMADE_DECKS, load_premade_deck
from ..engine import rules
from ..engine.actions import DrawAction, PlaceAction, action_from_dict
from ..engine.cards import load_cards
from ..engine.maps import load_map
from ..engine.state import EngineError, GameState, new_game, other_player
from ..engine.strength import effective_strength, placement_strength

CARDS = load_cards()
MAP_ID = "map_b"
GAMES_TO_WIN = 2

# Menu labels for the premade decks (the design mockups' names).
DECK_NAMES = {"cats_midrange": "Cats", "canine_buff_tempo": "Canines", "aggro_hq_rush": "Aggro",
              "colony_food_swarm": "Colony", "egg_control": "Egg", "food_otk": "Food", "ramp": "Ramp"}

# Easy / Normal / Expert, as in the play screen.
BOT_LEVELS = {"easy": GreedyBot, "normal": TurnBot, "expert": RefereeBot}


def bot_for(level: str, seed: int):
    return BOT_LEVELS[level](seed=seed)


@dataclass
class Seat:
    token: str
    name: str
    bot: Optional[str] = None        # bot level, or None for a human
    deck: Optional[str] = None
    ready: bool = False

    @property
    def is_bot(self) -> bool:
        return self.bot is not None


@dataclass
class Move:
    """One top-level action and everything that resolved under it (choices included)."""
    round: int
    seat: str
    kind: str                        # "draw" | "place"
    card: Optional[str] = None
    target: Optional[list] = None
    fx: list = field(default_factory=list)
    pre: dict = field(default_factory=dict, repr=False)

    def public(self) -> dict:
        return {"round": self.round, "seat": self.seat, "kind": self.kind, "card": self.card,
                "target": self.target, "fx": self.fx}


def _snapshot(state: GameState) -> dict:
    return {
        "board": {cr: [(u.iid, u.card_id, u.owner) for u in st] for cr, st in state.board.items() if st},
        "hands": {p: {u.iid for u in state.hands[p]} for p in "AB"},
        "remove": len(state.remove_pile),
        "food": dict(state.food),
        "turn": state.turn_counter,
    }


def _effects(state: GameState, move: Move) -> list:
    """What a move did, by diffing the position before it against now (public facts only)."""
    pre, fx = move.pre, []
    if move.kind == "place" and move.target and move.target[0] == "cr":
        below = pre["board"].get(move.target[1])
        if below and below[-1][2] != move.seat:
            fx.append({"k": "cover", "card": below[-1][1], "owner": below[-1][2]})
    on_board_now = {u.iid for st in state.board.values() for u in st}
    in_hand_now = {p: {u.iid for u in state.hands[p]} for p in "AB"}
    vanished = {iid: (cid, owner) for st in pre["board"].values() for iid, cid, owner in st
                if iid not in on_board_now}
    for iid, (cid, owner) in vanished.items():
        if iid in in_hand_now[owner]:
            fx.append({"k": "bounce", "card": cid, "owner": owner})
    for cid in state.remove_pile[pre["remove"]:]:
        owner = next((o for iid, (c, o) in vanished.items() if c == cid), None)
        fx.append({"k": "remove", "card": cid, "owner": owner})
    pre_board_iids = {iid for st in pre["board"].values() for iid, _, _ in st}
    for p in "AB":
        drawn = len(in_hand_now[p] - pre["hands"][p] - pre_board_iids)
        if drawn:
            fx.append({"k": "draw", "seat": p, "n": drawn})
    for p in "AB":
        gain = state.food[p] - pre["food"][p]
        if state.turn_counter != pre["turn"] and p == move.seat:
            gain -= sum(r.food for r in rules.regions_controlled(state, p))  # end-of-turn income
        if gain:
            fx.append({"k": "food", "seat": p, "n": gain})
    return fx


class Match:
    def __init__(self, match_id: str, host: Seat):
        self.id = match_id
        self.seats: dict[str, Seat] = {"A": host}
        self.phase = "lobby"             # lobby -> prematch -> playing -> game_over -> match_over
        self.results: list[dict] = []    # one {winner, reason, turns} per finished game
        self.state: Optional[GameState] = None
        self.history: list[Move] = []
        self.bots: dict[str, object] = {}
        self.version = 0                 # bumped on every change; the server pushes on bumps
        self.seed: Optional[int] = None
        self.actions: list[dict] = []    # the current game's actions, for the replayable log
        self.on_game_end = None          # callback(match, log record); the server saves human games
        self.rng = random.Random(secrets.randbits(32))
        self.created = datetime.now(timezone.utc)

    # ----------------------------------------------------------------- seats
    def seat_of(self, token: str) -> Optional[str]:
        return next((s for s, seat in self.seats.items() if seat.token == token), None)

    def join(self, seat: Seat) -> str:
        if "B" in self.seats:
            raise EngineError("match is full")
        self.seats["B"] = seat
        self._maybe_prematch()
        return "B"

    def set_deck(self, s: str, deck: str) -> None:
        if deck not in PREMADE_DECKS:
            raise EngineError(f"unknown deck {deck!r}")
        if self.phase not in ("lobby", "prematch"):
            raise EngineError("decks are fixed for the whole match")
        self.seats[s].deck = deck
        self.seats[s].ready = False
        self._maybe_prematch()

    def _maybe_prematch(self) -> None:
        if len(self.seats) == 2 and all(seat.deck for seat in self.seats.values()):
            self.phase = "prematch"
            for s, seat in self.seats.items():
                if seat.is_bot:
                    seat.ready = True
            if all(seat.ready for seat in self.seats.values()):
                self._start_game()
        self.version += 1

    def ready(self, s: str) -> None:
        if self.phase != "prematch":
            raise EngineError("not in pre-match")
        self.seats[s].ready = True
        if all(seat.ready for seat in self.seats.values()):
            self._start_game()
        self.version += 1

    # ----------------------------------------------------------------- games
    def score(self) -> dict:
        return {p: sum(1 for r in self.results if r["winner"] == p) for p in "AB"}

    def _start_game(self) -> None:
        # Game 1 is a coin flip; afterwards the loser of the previous game goes first
        # (Martin, 2026-09-26). A drawn game keeps the previous first player.
        first = None
        if self.results:
            last = self.results[-1]
            first = other_player(last["winner"]) if last["winner"] else last["first"]
        seed = self.seed = self.rng.randrange(1 << 30)
        self.actions = []
        self.state = new_game(load_premade_deck(self.seats["A"].deck),
                              load_premade_deck(self.seats["B"].deck), seed,
                              map_id=MAP_ID, first_player=first)
        self.bots = {s: bot_for(seat.bot, seed + i) for i, (s, seat) in enumerate(self.seats.items())
                     if seat.is_bot}
        self.history = []
        self.phase = "playing"

    def next_game(self) -> None:
        if self.phase != "game_over":
            raise EngineError("no game to continue from")
        self._start_game()
        self.version += 1

    def rematch(self) -> None:
        if self.phase != "match_over":
            raise EngineError("the match is still on")
        self.results = []
        self.state = None
        self.history = []
        self.phase = "prematch"
        for seat in self.seats.values():
            seat.ready = seat.is_bot
        self.version += 1

    def to_act(self) -> Optional[str]:
        if self.phase != "playing":
            return None
        return self.state.player_to_act()

    def act(self, s: str, action) -> None:
        """Apply one action for seat `s`: a top-level move or a pending sub-choice."""
        if self.phase != "playing":
            raise EngineError("no game in progress")
        state = self.state
        if state.player_to_act() != s:
            raise EngineError("not your decision")
        if isinstance(action, dict):
            action = action_from_dict(action)
        # A placement starts a history entry, including a free extra play inside a Battlecry;
        # draws and sub-choices fold into the entry they belong to.
        starts_move = state.pending is None or isinstance(action, PlaceAction)
        pre = _snapshot(state) if starts_move else None
        rules.apply_action(state, action)    # validates; raises EngineError if illegal
        self.actions.append(action.to_dict())
        if starts_move:
            placed = isinstance(action, PlaceAction)
            self.history.append(Move(
                round=pre["turn"] // 2 + 1, seat=s, kind="place" if placed else "draw", pre=pre,
                card=action.card_id if placed else None,
                target=list(action.target) if placed else None))
        if self.history:
            self.history[-1].fx = _effects(state, self.history[-1])
        self._check_end()
        self.version += 1

    def _check_end(self) -> None:
        result = rules.is_terminal(self.state)
        if result is None:
            return
        self.state.result = result
        self.results.append({"winner": result.winner, "reason": result.reason,
                             "turns": self.state.turn_counter // 2 + 1,
                             "first": self.state.first_player})
        if self.on_game_end:
            self.on_game_end(self, self.game_log())
        score = self.score()
        over = max(score.values()) >= GAMES_TO_WIN or len(self.results) >= 2 * GAMES_TO_WIN - 1
        self.phase = "match_over" if over else "game_over"

    def game_log(self) -> dict:
        """The finished game in the sim.replay log format (replayable with no bot compute)."""
        r = self.results[-1]
        return {"deck_a": self.seats["A"].deck, "deck_b": self.seats["B"].deck, "seed": self.seed,
                "map_id": MAP_ID, "first_player": r["first"],
                "bots": [self.seats[p].bot or "human" for p in "AB"],
                "winner": r["winner"], "reason": r["reason"], "turns": self.state.turn_counter,
                "actions": list(self.actions),
                "match_id": self.id, "game_no": len(self.results)}

    def bot_move(self):
        """The action the bot to act would take (pure: call off the event loop, apply after)."""
        s = self.to_act()
        state = self.state.clone()
        return self.bots[s].choose(state.view_for(s), rules.legal_actions(state), state)

    # ----------------------------------------------------------------- views
    def view(self, s: str) -> dict:
        opp = other_player(s)
        v = {
            "id": self.id, "you": s, "phase": self.phase, "version": self.version,
            "seats": {p: {"name": seat.name, "bot": seat.bot, "deck": seat.deck, "ready": seat.ready,
                          "deckName": DECK_NAMES.get(seat.deck, seat.deck)}
                      for p, seat in self.seats.items()},
            "results": [{k: r[k] for k in ("winner", "reason", "turns")} for r in self.results],
            "score": self.score(),
            "lists": {p: dict(Counter(load_premade_deck(seat.deck)))
                      for p, seat in self.seats.items() if seat.deck},
            "game": None,
        }
        if self.state is not None:
            v["game"] = self._game_view(s, opp)
        return v

    def _game_view(self, s: str, opp: str) -> dict:
        st = self.state
        to_act = st.player_to_act() if st.result is None else None
        bonus = st.turn_flags.get(f"bonus_actions_{st.current}", 0)
        timers = {x["iid"]: x["remaining"] for x in st.scheduled}
        board = {}
        for cr, stack in st.board.items():
            if not stack:
                continue
            board[cr] = [{"id": u.card_id, "owner": u.owner, "str": effective_strength(st, u),
                          **({"timer": timers[u.iid]} if u.iid in timers else {})} for u in stack]
        g = {
            "round": st.turn_counter // 2 + 1,
            "current": st.current,
            "toAct": to_act,
            "first": st.first_player,
            "actionsLeft": st.config.actions_per_turn + bonus - st.actions_taken_this_turn,
            "actionsTotal": st.config.actions_per_turn + bonus,
            "food": dict(st.food),
            "income": {p: sum(r.food for r in rules.regions_controlled(st, p)) for p in "AB"},
            "winFood": st.game_map.win_food,
            "board": board,
            "hand": [{"iid": u.iid, "id": u.card_id, "str": placement_strength(st, u)}
                     for u in st.hands[s]],
            "handCount": {p: len(st.hands[p]) for p in "AB"},
            "handLimit": st.config.hand_limit,
            "deckCount": {p: len(st.decks[p]) for p in "AB"},
            "deckLeft": dict(Counter(st.decks[s])),
            "unseen": dict(Counter(st.decks[opp]) + Counter(u.card_id for u in st.hands[opp])),
            "removed": list(st.remove_pile),
            "result": st.result.to_dict() if st.result else None,
            "history": [m.public() for m in self.history],
            "legal": None,
            "pending": None,
        }
        if to_act == s:
            g["legal"], g["pending"] = self._decision(s)
        elif st.pending is not None and to_act == opp:
            g["opponentChoosing"] = True
        return g

    def _decision(self, s: str):
        st = self.state
        legal = rules.legal_actions(st)
        places: dict[str, list] = {}
        for a in legal:
            if isinstance(a, PlaceAction):
                places.setdefault(a.card_id, []).append(list(a.target))
        out = {"draw": any(isinstance(a, DrawAction) for a in legal), "place": places}
        if st.pending is None:
            return out, None
        p = st.pending
        pending = {"mode": p["mode"], "optional": bool(p.get("optional")), "source": self._source(),
                   "options": []}
        if p["mode"] == "choice":
            pending["options"] = [self._describe_option(o) for o in p["options"]]
        return out, pending

    def _source(self) -> Optional[str]:
        """The card whose effect is asking: named on the paused step, else the last card played."""
        step = self.state.effect_stack[-1] if self.state.effect_stack else {}
        if step.get("by_card") in CARDS:
            return step["by_card"]
        op = step.get("op", "")
        for cid in sorted(CARDS, key=len, reverse=True):
            if op.startswith(cid + "_"):
                return cid
        for m in reversed(self.history):
            if m.kind == "place":
                return m.card
        return None

    def _describe_option(self, o) -> dict:
        st = self.state
        if isinstance(o, str) and o in st.game_map.crossroads:
            return {"v": o, "kind": "cr"}
        if isinstance(o, int):
            for p in "AB":
                for u in st.hands[p]:
                    if u.iid == o:
                        return {"v": o, "kind": "hand", "id": u.card_id}
            for cr, stack in st.board.items():
                for u in stack:
                    if u.iid == o:
                        return {"v": o, "kind": "cr", "cr": cr, "id": u.card_id}
        if isinstance(o, str) and o in CARDS:
            return {"v": o, "kind": "card", "id": o}
        return {"v": o, "kind": "other", "label": str(o)}


def map_info() -> dict:
    gm = load_map(MAP_ID)
    cols = max(int(c.split(",")[0]) for c in gm.crossroads)
    rows = max(int(c.split(",")[1]) for c in gm.crossroads)
    regions = []
    for r in gm.regions.values():
        cs = [tuple(map(int, c.split(","))) for c in r.corners]
        regions.append({"id": r.id, "c": list(min(cs)), "food": r.food})
    return {"id": gm.id, "name": gm.name, "cols": cols, "rows": rows, "regions": regions,
            "winFood": gm.win_food}


def card_pool() -> list[dict]:
    return [{"id": c.id, "name": c.name, "deck": c.deck, "rarity": c.rarity, "tags": sorted(c.tags),
             "str": "*" if c.is_dynamic else c.base_strength, "text": c.text,
             "kw": sorted(c.keywords), "cost": c.food_cost}
            for c in CARDS.values()]

