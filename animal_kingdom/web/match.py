"""One match as the web server holds it: its seats, the game, the turn clock, its history, and each seat's view.

A match is one game; Rematch starts another in the same match, the loser of the last going first."""

from __future__ import annotations

import logging
import random
import secrets
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..bots.greedy import GreedyBot
from ..decks import DECK_LEADERS, load_deck
from ..engine import rules, statics
from ..engine.actions import SKIP, ChoiceAction, LeaderAction, PassAction, PlaceAction, action_from_dict
from ..engine import leaders as L
from ..engine.cards import load_cards
from ..engine.effects import MAKES, leader_usable, mana_cost, power_cost
from ..engine.maps import load_map
from ..engine.state import MAP_ID, EngineError, GameState, Result, new_game, other_player
from ..engine.strength import card_strength, effective_strength

log = logging.getLogger(__name__)
CARDS = load_cards()
ASKS = {"mulligan": "mulligan"}   # what a pending choice asks, by the step asking: the mulligan; anything else is "effect"
# The turn clock, for matches between two people: whoever must act gets a free window each time the decision comes to
# them (unused time is lost), then spends their bank for the game. At zero, the engine acts for them.
CLOCK_FREE = 30.0
CLOCK_BANK = 180.0
CLOCK_CATCHUP_MAX = 8.0      # at most this long, a turn's clock waits for its player's screen to show the opponent's moves
CLOCK_MULLIGAN = 30.0        # one window for both players' mulligans at once; what's left is kept
EVENTS_KEPT = 200            # a view carries the game's last events: enough for a client that missed a few views
TIMEOUTS_TO_LOSE = 3         # turns in a row a player's clock ran out: they have left, and lose (Martin, 2026-10-01)

DECK_NAMES: dict[str, str] = {}   # deck slug -> the name its builder gave it (web/custom_decks.py)


@dataclass
class Seat:
    token: str
    name: str
    bot: bool = False
    deck: Optional[str] = None
    ready: bool = False
    profile: Optional[str] = None    # the player's profile id, when they have one

    @property
    def is_bot(self) -> bool:
        return self.bot


@dataclass
class Move:
    """One top-level action and everything that resolved under it (choices included)."""
    round: int
    seat: str
    kind: str                        # "place" | "leader"
    card: Optional[str] = None
    target: Optional[list] = None
    fx: list = field(default_factory=list)
    pre: dict = field(default_factory=dict, repr=False)
    events: list = field(default_factory=list, repr=False)   # the engine's events under this move, in order

    def public(self) -> dict:
        return {"round": self.round, "seat": self.seat, "kind": self.kind, "card": self.card,
                "target": self.target, "fx": self.fx}


def _snapshot(state: GameState) -> dict:
    return {"board": {cr: [(u.iid, u.card_id, u.owner) for u in st] for cr, st in state.board.items() if st},
            "hands": {p: sorted(u.iid for u in state.hands[p]) for p in "AB"}, "remove": len(state.remove_pile),
            "food": dict(state.food), "turn": state.turn_counter}


def _effects(events: list, move: Move) -> list:
    """What a move did, read from the engine's events in order (public facts only): an enemy covered, each removal, cards
    drawn, food from cards (a turn's region income is not the move's), what a raid destroyed."""
    fx = []
    for e in events:
        if e["e"] == "cover" and e["owner"] != move.seat:
            fx.append({"k": "cover", "card": e["card"], "owner": e["owner"]})
        elif e["e"] == "remove" and e.get("cr"):
            fx.append({"k": "remove", "card": e["card"], "owner": e["owner"]})
        elif e["e"] == "draw":
            fx.append({"k": "draw", "seat": e["player"], "n": len(e["cards"])})
        elif e["e"] == "food" and not e.get("income"):
            fx.append({"k": "food", "seat": e["player"], "n": e["n"]})
        elif e["e"] == "raid" and e["n"]:
            fx.append({"k": "lose", "seat": e["den"], "n": e["n"]})
    merged = []   # several draws or food gains by one player in a row read as one
    for f in fx:
        if merged and f["k"] in ("draw", "food") and merged[-1]["k"] == f["k"] and merged[-1]["seat"] == f["seat"]:
            merged[-1] = {**merged[-1], "n": merged[-1]["n"] + f["n"]}
        else:
            merged.append(f)
    return merged


def public_event(e: dict, viewer: str) -> dict:
    """An event as `viewer` may see it: the cards drawn into the other player's hand stay hidden (only how many)."""
    if e["e"] == "draw" and e["player"] != viewer:
        return {**{k: v for k, v in e.items() if k != "cards"}, "n": len(e["cards"])}
    return e


def leader_view(st: GameState, p: str) -> Optional[dict]:
    """A player's leader as both players see it: which card, its kind, its ability, whether its power can be used now, and
    what the power costs."""
    lead = st.leaders.get(p)
    if lead is None:
        return None
    lid = lead["id"]
    kind, text = L.LEADERS[lid]
    cost = power_cost(st, p)
    usable = st.current == p and st.pending is None and st.result is None and rules.mana_left(st, p) >= cost \
        and leader_usable(st, p)
    spent = kind == "power" and st.current == p and st.power_used   # once a turn: "Used" until their next
    return {"id": lid, "kind": kind, "text": text, "usable": usable, **({"cost": cost, "spent": spent} if kind == "power" else {})}


class Match:
    def __init__(self, match_id: str, host: Seat):
        self.id = match_id
        self.seats: dict[str, Seat] = {"A": host}
        self.events: list[dict] = []     # the game's engine events, numbered (`seq`); see _take_events
        self.seq = 0
        self.played: dict[str, int] = {}   # seat -> the last event its screen has played out (server._watched); not saved
        self.phase = "lobby"             # lobby -> playing -> match_over
        self.result: Optional[dict] = None   # {winner, reason, turns, first} once the game is over
        self.last_result: Optional[dict] = None   # the previous game's, so a rematch's loser goes first
        self.state: Optional[GameState] = None
        self.history: list[Move] = []
        self.bots: dict[str, GreedyBot] = {}
        self.version = 0                 # bumped on every change; the server pushes on bumps
        self.seed: Optional[int] = None
        self.actions: list[dict] = []    # the game's actions, for the replayable log
        self.action_times: list[float] = []   # seconds since the game started, one per action
        self.started_at = 0.0
        self.on_game_end = None          # callback(match, log record): the server saves a game with a person in it
        self.rematches = 0
        self.rematch_offer: Optional[str] = None     # between two people: the seat that offered a rematch
        self.rematch_declined: Optional[str] = None  # ...and the seat that declined it
        self.clock: Optional[dict] = None   # {bank: {A, B}, holder, turn, free, since}; None when a bot plays
        self.rng = random.Random(secrets.randbits(32))
        self.created = datetime.now(timezone.utc)

    # ----------------------------------------------------------------- seats
    def seat_of(self, token: str) -> Optional[str]:
        return next((s for s, seat in self.seats.items() if seat.token == token), None)

    def join(self, seat: Seat) -> str:
        if "B" in self.seats:
            raise EngineError("match is full")
        self.seats["B"] = seat
        if all(s.deck for s in self.seats.values()):
            for s in self.seats.values():
                s.ready = True
            self._start_game()
        self.version += 1
        return "B"

    # ----------------------------------------------------------------- the game
    def _start_game(self) -> None:
        # Game 1 is a coin flip; in a rematch the loser of the last game goes first. A draw keeps the first player.
        last = self.last_result
        first = (other_player(last["winner"]) if last["winner"] else last["first"]) if last else None
        seed = self.seed = self.rng.randrange(1 << 30)
        self.actions, self.action_times, self.started_at = [], [], time.time()
        decks = {p: self.seats[p].deck for p in "AB"}
        self.state = new_game(load_deck(decks["A"]), load_deck(decks["B"]), seed, first_player=first,
                              leaders={p: DECK_LEADERS.get(d) for p, d in decks.items()})
        self.bots = {s: GreedyBot(seed + i) for i, (s, seat) in enumerate(self.seats.items()) if seat.is_bot}
        self.history, self.events, self.seq, self.result = [], [], 0, None
        self.phase = "playing"
        self.clock = None if any(seat.is_bot for seat in self.seats.values()) else \
            {"bank": {"A": CLOCK_BANK, "B": CLOCK_BANK}, "holder": None, "turn": -1, "free": 0.0, "since": time.time(),
             "mull_until": time.time() + CLOCK_MULLIGAN, "out": {"A": 0, "B": 0}}
        self._clock_update()

    def friendly(self) -> bool:
        """Two people: a rematch is an offer the other accepts or declines."""
        return "B" in self.seats and not any(s.is_bot for s in self.seats.values())

    def offer_rematch(self, s: str) -> None:
        """A seat's Rematch: against a bot it starts one; between two people it offers one, and the other's accepts."""
        if self.phase != "match_over":
            raise EngineError("the match is still on")
        if not self.friendly() or self.rematch_offer == other_player(s):
            self.rematch()
        elif self.rematch_declined is not None:
            raise EngineError("the rematch was declined")
        elif self.rematch_offer is None:
            self.rematch_offer = s
            self.version += 1

    def decline_rematch(self, s: str) -> None:
        if self.phase != "match_over" or self.rematch_offer != other_player(s):
            raise EngineError("no rematch to decline")
        self.rematch_offer, self.rematch_declined = None, s
        self.version += 1

    def rematch(self) -> None:
        if self.phase != "match_over":
            raise EngineError("the match is still on")
        self.rematch_offer = self.rematch_declined = None
        self.last_result = self.result
        self.rematches += 1
        self._start_game()
        self.version += 1

    def to_act(self) -> Optional[str]:
        return self.state.player_to_act() if self.phase == "playing" else None

    def _take_events(self) -> list:
        """The engine's new events, numbered for the game (the view sends them; a client plays what it hasn't seen)."""
        new, self.state.events = self.state.events, []
        for e in new:
            self.seq += 1
            e["seq"] = self.seq
        self.events = (self.events + new)[-EVENTS_KEPT:]
        return new

    def mulliganing(self) -> bool:
        """The opening mulligans are under way (both at once, on one shared clock window)."""
        st = self.state
        return bool(st and st.result is None and st.pending and st.pending.get("kind") == "mulligan")

    def act(self, s: str, action, auto: bool = False) -> None:
        """Apply one action for seat `s`: a top-level move or a pending choice. `auto`: the clock acted for them."""
        if not auto and self.clock and "out" in self.clock:
            self.clock["out"][s] = 0
        if self.phase != "playing":
            raise EngineError("no game in progress")
        state = self.state
        if isinstance(action, dict):
            action = action_from_dict({k: v for k, v in action.items() if k != "by"})
        if state.player_to_act() != s and rules.early_mulligan(state, s) is not None:   # both mulligan at once
            rules.apply_early_mulligan(state, s, action)
            self._take_events()
            self.actions.append({**action.to_dict(), "by": s})   # a replay applies it the same way (rules.apply_logged)
            self.action_times.append(round(time.time() - self.started_at, 1))
            self.version += 1
            return
        if state.player_to_act() != s:
            raise EngineError("not your decision")
        starts_move = state.pending is None and isinstance(action, (PlaceAction, LeaderAction))
        pre = _snapshot(state) if starts_move else None
        rules.apply_action(state, action)    # validates; raises EngineError if illegal
        new = self._take_events()
        self.actions.append(action.to_dict())
        self.action_times.append(round(time.time() - self.started_at, 1))
        if starts_move:
            placed = isinstance(action, PlaceAction)
            self.history.append(Move(round=pre["turn"] // 2 + 1, seat=s, kind="place" if placed else "leader", pre=pre,
                                     card=action.card_id if placed else state.leaders[s]["id"],
                                     target=list(action.target) if placed else None))
        if self.history:
            self.history[-1].events += new
            self.history[-1].fx = _effects(self.history[-1].events, self.history[-1])
        self._check_end()
        self._clock_update()
        self.version += 1

    # ----------------------------------------------------------------- turn clock
    def _clock_update(self, now: Optional[float] = None) -> None:
        """Charge the time since the last update to whoever held the decision, then hand the clock to whoever must act
        now: a fresh free window if it changed hands or a new turn began."""
        c = self.clock
        if c is None:
            return
        now = time.time() if now is None else now
        if c["holder"] and c.get("mull_until") and c["turn"] == -2:   # the mulligan's window charges no one's bank
            pass
        elif c["holder"]:
            spent = now - c["since"]
            c["bank"][c["holder"]] = max(0.0, c["bank"][c["holder"]] - max(0.0, spent - c["free"]))
            c["free"] = max(0.0, c["free"] - spent)
        holder = self.to_act()
        turn = -2 if self.mulliganing() else self.state.turn_counter if self.state else -1
        if holder != c["holder"] or turn != c["turn"]:
            c["free"] = CLOCK_FREE
            # the new holder's clock starts once their screen has played out what led here (played_out), not before
            c["catchup"] = self.seq if holder and turn != -2 and self.played.get(holder, 0) < self.seq else None
        c["holder"], c["turn"], c["since"] = holder, turn, now

    def played_out(self, s: str, seq: int, now: Optional[float] = None) -> bool:
        """Seat `s`'s screen has played the events up to `seq`: if its clock was waiting for that, the wait (up to
        CLOCK_CATCHUP_MAX) is given back, the clock starting from now. Returns whether the clock changed."""
        self.played[s] = seq
        c = self.clock
        if not c or c.get("catchup") is None or c["holder"] != s or seq < c["catchup"]:
            return False
        now = time.time() if now is None else now
        c["since"] += min(CLOCK_CATCHUP_MAX, max(0.0, now - c["since"]))
        c["catchup"] = None
        self.version += 1
        return True

    def clock_deadline(self) -> Optional[float]:
        c = self.clock
        if c is None or c["holder"] is None or self.phase != "playing":
            return None
        if self.mulliganing() and c.get("mull_until"):
            return c["mull_until"]
        return c["since"] + c["free"] + c["bank"][c["holder"]]

    def time_out(self, now: Optional[float] = None) -> bool:
        """If the player to act is out of time, act for them: decline or take the first option of a choice, else end
        their turn. Returns whether it acted."""
        deadline = self.clock_deadline()
        now = time.time() if now is None else now
        if deadline is None or now < deadline:
            return False
        s, st = self.to_act(), self.state
        if self.mulliganing():   # the shared window is over: whoever is still mulliganing keeps the hand they have
            for p in "AB":
                if rules.early_mulligan(st, p) is not None:
                    self.act(p, ChoiceAction(SKIP), auto=True)
            while self.mulliganing():
                self.act(self.to_act(), ChoiceAction(SKIP), auto=True)
            return True
        self._clock_update(now)
        if st.pending is None:
            self.act(s, PassAction(), auto=True)
            out = self.clock.setdefault("out", {"A": 0, "B": 0})
            out[s] += 1
            if out[s] >= TIMEOUTS_TO_LOSE and self.state.result is None:   # gone: the match is the opponent's
                self._check_end(Result(other_player(s), "timeout"))
        else:
            legal = rules.legal_actions(st)
            self.act(s, ChoiceAction(SKIP) if ChoiceAction(SKIP) in legal else legal[0], auto=True)
        return True

    def concede(self, s: str) -> None:
        if self.phase != "playing" or self.state.result is not None:
            raise EngineError("no game to concede")
        self._clock_update()
        self._check_end(Result(other_player(s), "concede"))
        self.version += 1

    def _check_end(self, result: Optional[Result] = None) -> None:
        result = result or rules.is_terminal(self.state)
        if result is None:
            return
        self.state.result = result
        self.result = {"winner": result.winner, "reason": result.reason, "turns": self.state.turn_counter // 2 + 1,
                       "first": self.state.first_player}
        for c in self.state.caps:      # a turn a cap ended: a looping combination of cards, to read in the log
            log.warning("turn capped (%s) in match %s, turn %s, %s: cards %s", c["cap"], self.id, c["turn"], c["player"],
                        ", ".join(c["cards"]) or "?")
        self.phase = "match_over"
        if self.on_game_end:
            self.on_game_end(self, self.game_log())

    def game_log(self) -> dict:
        """The finished game as a log line (animal_kingdom/replay.py replays it with no bot compute)."""
        r = self.result
        return {"seed": self.seed, "first_player": r["first"], "bots": ["bot" if self.seats[p].is_bot else "human" for p in "AB"],
                "winner": r["winner"], "reason": r["reason"], "turns": self.state.turn_counter,
                "actions": list(self.actions), "action_times": list(self.action_times),
                "match_id": self.id, "series": self.rematches,
                "lists": [list(self.state.starting_decks[p]) for p in "AB"],
                "leaders": {p: lead["id"] for p, lead in self.state.leaders.items()},
                **({"capped": [dict(c) for c in self.state.caps]} if self.state.caps else {})}

    def bot_move(self):
        """The action the bot to act would take (pure: call off the event loop, apply after)."""
        s = self.to_act()
        state = self.state.clone()
        return self.bots[s].choose(state.view_for(s), rules.legal_actions(state), state)

    def fallback_move(self):
        """A legal move when the bot's own choice failed: the first legal action."""
        return rules.legal_actions(self.state)[0]

    # ----------------------------------------------------------------- persistence
    def to_dict(self) -> dict:
        """Everything needed to resume this match after a server restart."""
        return {"id": self.id, "seats": {p: asdict(seat) for p, seat in self.seats.items()},
                "phase": self.phase, "result": self.result, "last_result": self.last_result, "seed": self.seed,
                "actions": self.actions, "action_times": self.action_times, "started_at": self.started_at,
                "created": self.created.isoformat(), "version": self.version, "rematches": self.rematches,
                "clock": self.clock, "rematch_offer": self.rematch_offer, "rematch_declined": self.rematch_declined,
                "state": self.state.to_dict() if self.state is not None else None,
                "history": [asdict(m) for m in self.history], "events": self.events, "seq": self.seq}

    @staticmethod
    def from_dict(d: dict) -> "Match":
        seats = {p: Seat(**s) for p, s in d["seats"].items()}
        m = Match(d["id"], seats["A"])
        m.seats = seats
        m.phase, m.result, m.last_result, m.seed = d["phase"], d["result"], d["last_result"], d["seed"]
        m.actions, m.action_times, m.started_at = d["actions"], d["action_times"], d["started_at"]
        m.version, m.rematches = d["version"] + 1, d["rematches"]
        m.rematch_offer, m.rematch_declined = d["rematch_offer"], d["rematch_declined"]
        m.clock = d["clock"]
        if m.clock:
            m.clock["since"] = time.time()      # time the server was down isn't anyone's
        m.created = datetime.fromisoformat(d["created"])
        m.state = GameState.from_dict(d["state"]) if d["state"] else None
        m.history = [Move(**h) for h in d["history"]]
        m.events, m.seq = d["events"], d["seq"]
        if m.state is not None and m.seed is not None:
            m.bots = {s: GreedyBot(m.seed + i) for i, (s, seat) in enumerate(m.seats.items()) if seat.is_bot}
        return m

    # ----------------------------------------------------------------- views
    def view(self, s: str) -> dict:
        v = {
            "id": self.id, "you": s, "phase": self.phase, "version": self.version,
            # a seat's deck by name only for you or a bot: a person's deck name is theirs (their list is open, by rule)
            "seats": {p: {"name": seat.name, "bot": seat.is_bot, "ready": seat.ready,
                          **({"deck": seat.deck, "deckName": DECK_NAMES.get(seat.deck, seat.deck)} if p == s or seat.is_bot else {})}
                      for p, seat in self.seats.items()},
            "result": self.result and {k: self.result[k] for k in ("winner", "reason", "turns")},
            "lists": {p: dict(Counter(load_deck(seat.deck))) for p, seat in self.seats.items() if seat.deck},
            "game": None,
        }
        if self.rematch_offer or self.rematch_declined:
            v["rematch"] = {"offer": self.rematch_offer, "declined": self.rematch_declined}
        if self.state is not None:
            v["game"] = self._game_view(s, other_player(s))
        return v

    def _game_view(self, s: str, opp: str) -> dict:
        st = self.state
        to_act = st.player_to_act() if st.result is None else None
        timers = {x["iid"]: x["remaining"] for x in st.scheduled}
        board = {}
        for cr, stack in st.board.items():
            # "hidden": the enemy can't choose it (Stealth); "spikes" until spent; "armor": no ability removes it
            board[cr] = [{"iid": u.iid, "id": u.card_id, "owner": u.owner, "str": effective_strength(st, u),
                          **({"timer": timers[u.iid]} if u.iid in timers else {}),
                          **({"hidden": True} if not statics.can_be_chosen(st, u, other_player(u.owner)) else {}),
                          **({"spikes": True} if statics.has_keyword(st, u, "Spikes") and not u.retaliation_used else {}),
                          **({"poison": True} if statics.has_keyword(st, u, "Poison") else {}),
                          **({"armor": True} if not statics.can_be_removed(st, u) else {})} for u in stack]
        g = {
            "round": st.turn_counter // 2 + 1,
            "current": st.current,
            "toAct": to_act,
            "first": st.first_player,
            "canPass": rules.can_pass(st),
            "clock": {"on": False} if not self.clock else (self._mulligan_clock(s) if self.mulliganing() and self.clock.get("mull_until") else
                                     {**{k: self.clock[k] for k in ("bank", "holder", "free", "since")}, "now": time.time(),
                                     "on": self.clock_deadline() is not None}),
            "food": dict(st.food),
            "income": {p: rules.region_income(st, p) for p in "AB"},
            "winFood": st.game_map.win_food,
            "board": board,
            "hand": [{"iid": u.iid, "id": u.card_id, "str": effective_strength(st, u), "cost": mana_cost(st, u.card_id, s)}
                     for u in st.hands[s]],
            "handCount": {p: len(st.hands[p]) for p in "AB"},
            "leaders": {p: v for p in "AB" if (v := leader_view(st, p))},
            "deckCount": {p: len(st.decks[p]) for p in "AB"},
            "deckLeft": dict(Counter(st.decks[s])),
            # what the opponent may still hold: their deck, their hand, and the cards their mulligan set aside
            "unseen": dict(Counter(st.decks[opp]) + Counter(u.card_id for u in st.hands[opp])
                           + Counter(c for step in st.effect_stack if step.get("player") == opp for c in step.get("returned", ()))),
            "removed": list(st.remove_pile),
            "pile": [{"id": c, "owner": o, "str": card_strength(st, c, o or s)} for c, o in zip(st.remove_pile, st.pile_owners)],
            "result": st.result.to_dict() if st.result else None,
            "history": [m.public() for m in self.history],
            "events": [public_event(e, s) for e in self.events if not (e["e"] == "mulligan" and e["player"] != s)],
            "mana": {p: {"left": rules.mana_left(st, p), "total": rules.mana_total(st, p)} for p in "AB"},
            "abilityCost": st.config.leader_power_cost,
            "bases": {p: sorted(t) for p, t in st.game_map.hq_connects.items()},
            "legal": None,
            "pending": None,
        }
        if to_act == s:
            g["legal"], g["pending"] = self._decision(s)
        elif st.result is None and rules.early_mulligan(st, s) is not None:   # your mulligan, while theirs goes on too
            g["toAct"] = s
            i = rules.early_mulligan(st, s)
            g["legal"] = {"place": {}, "leader": False}
            g["pending"] = {"mode": "choice", "optional": True, "source": None, "kind": "mulligan",
                            "returned": len(st.effect_stack[i]["returned"]), "cap": st.config.mulligan_cap(s, st.first_player),
                            "options": [self._describe_option(u.iid) for u in st.hands[s]]}
        # who decides what, always stated: over, mulligan (both at once), yours / your choice, theirs / their choice
        mull = st.pending is not None and st.pending.get("kind") == "mulligan"
        g["decision"] = ("over" if st.result is not None else "mulligan" if mull
                         else ("your_choice" if st.pending else "yours") if g["toAct"] == s
                         else "their_choice" if st.pending else "theirs")
        return g

    def _mulligan_clock(self, s: str) -> dict:
        """The shared mulligan window, shown to each player as their own time (no bank is touched)."""
        now = time.time()
        return {"bank": {"A": 0.0, "B": 0.0}, "holder": s, "free": max(0.0, self.clock["mull_until"] - now), "since": now,
                "now": now, "on": True}

    def _decision(self, s: str):
        st = self.state
        legal = rules.legal_actions(st)
        places: dict[str, list] = {}
        for a in legal:
            if isinstance(a, PlaceAction):
                places.setdefault(a.card_id, []).append(list(a.target))
        out = {"place": places, "leader": any(isinstance(a, LeaderAction) for a in legal)}
        if st.pending is None:
            return out, None
        p = st.pending
        step = st.effect_stack[-1] if st.effect_stack else {}
        pending = {"mode": p["mode"], "optional": bool(p.get("optional")), "source": self._source(),
                   "kind": ASKS.get(step.get("op"), "effect"),
                   "returned": len(step.get("returned", ())) if step.get("op") == "mulligan" else 0,
                   "cap": st.config.mulligan_cap(step.get("player"), st.first_player) if step.get("op") == "mulligan" else 0,
                   "options": [self._describe_option(o) for o in p["options"]]}
        return out, pending

    def _source(self) -> Optional[str]:
        """The card whose effect is asking: every step carries it (effects.resolve stamps it)."""
        step = self.state.effect_stack[-1] if self.state.effect_stack else {}
        return step.get("by_card") if step.get("by_card") in CARDS else None

    def _describe_option(self, o) -> dict:
        st = self.state
        if isinstance(o, str) and o in st.game_map.crossroads:
            return {"v": o, "kind": "cr"}
        if isinstance(o, int):
            for p in "AB":
                for u in st.hands[p]:
                    if u.iid == o:
                        return {"v": o, "kind": "hand", "id": u.card_id}
        if isinstance(o, str) and o.startswith("deck:"):     # Scout: a card on top of the chooser's own deck
            deck = st.decks[st.pending["chooser"]]
            return {"v": o, "kind": "card", "id": deck[len(deck) - 1 - int(o.split(":")[1])]}
        return {"v": o, "kind": "other", "label": str(o)}


def map_info() -> dict:
    """The board as the client draws it: its tiles ("row,col"), their adjacency, each region (its tiles, its food, and `c`,
    its lowest tile) and each player's base."""
    gm = load_map(MAP_ID)
    regions = [{"id": r.id, "c": list(min(tuple(map(int, c.split(","))) for c in r.corners)), "corners": list(r.corners),
                "food": r.food} for r in gm.regions.values()]
    return {"id": gm.id, "name": gm.name, "winFood": gm.win_food, "crossroads": sorted(gm.crossroads),
            "cols": max(int(c.split(",")[0]) for c in gm.crossroads), "rows": max(int(c.split(",")[1]) for c in gm.crossroads),
            "edges": [list(e) for e in gm.edges], "bases": {p: sorted(t) for p, t in gm.hq_connects.items()}, "regions": regions}


def card_pool() -> list[dict]:
    """Every card as the client reads it."""
    return [{"id": c.id, "name": c.name, "status": c.status, "rarity": c.rarity,
             # a variable strength (the Shades) prints 0: its text says what it gains
             "str": 0 if c.is_dynamic else c.base_strength, "text": c.text, "kw": sorted(c.keywords), "mana": c.cost,
             **({"related": list(MAKES[c.id])} if c.id in MAKES else {})}
            for c in CARDS.values()]
