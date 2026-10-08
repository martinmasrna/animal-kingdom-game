"""A match over the engine (one game for now; best-of-3 once there are three maps to reveal): seats, series score, move history, and per-seat views.

Transport-free: the server feeds it actions and reads views; nothing here does I/O. A view
carries only what that seat may see (open decklists, public board and Remove Pile, its own
hand); the opponent's hand and both deck orders never leave this module.
"""

from __future__ import annotations

import logging
import random
import secrets
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional

from ..decks import PREMADE_DECKS, load_premade_deck
from ..engine import rules, statics
from ..engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction, RoamAction, action_from_dict
from ..engine.cards import load_cards
from ..engine.effects import roar_condition
from ..engine.maps import load_map
from ..engine.state import EngineError, GameState, Result, new_game, other_player
from ..engine.strength import effective_strength, placement_strength
from ..sim.runner import make_bot
from . import tutorial

CARDS = load_cards()
# What a pending choice asks, by the effect step asking it: a choice from your own hand names its verb (the client heads it).
ASKS = {"mulligan": "mulligan", "magpie_steal": "discard", "raven_dig": "shuffle"}
MAP_ID = "map_b"
# One game per match while there is one map: the best-of-3 is part of the game, but its point is the three-map
# reveal (rules §14), so it comes back with the maps (Martin, 2026-09-30). Rematch carries the loser-first rule.
GAMES_TO_WIN = 1
# The turn clock, for matches between two people (pre-launch.md: a starting guess, to be set from
# real games). Whoever must act gets a free window each time the decision comes to them (unused
# time is lost), then spends their bank for the game. At zero, the engine acts for them.
CLOCK_FREE = 30.0
CLOCK_BANK = 180.0
CLOCK_CATCHUP_MAX = 8.0      # at most this long, a turn's clock waits for its player's screen to show the opponent's moves
CLOCK_MULLIGAN = 30.0        # one window for both players' mulligans at once (Martin, 2026-10-01); what's left is kept
EVENTS_KEPT = 200            # a view carries the game's last events: enough for a client that missed a few views
TIMEOUTS_TO_LOSE = 3         # turns in a row a player's clock ran out: they have left, and lose (Martin, 2026-10-01)

# Menu labels for the premade decks (the design mockups' names).
DECK_NAMES = {"cats_midrange": "Cats", "canine_buff_tempo": "Canines", "aggro_hq_rush": "Aggro",
              "colony_food_swarm": "Colony", "egg_control": "Egg", "food_otk": "Food", "ramp": "Ramp",
              "goodstuff": "Goodstuff", **tutorial.NAMES}

# Easy / Normal / Expert, as in the play screen: the same bot kinds, with the same settings, the
# simulations measure (a bare RefereeBot() is an untested configuration).
log = logging.getLogger(__name__)
BOT_LEVELS = {"easy": "easy", "normal": "turn", "expert": "referee"}


def bot_for(level: str, seed: int):
    if level in tutorial.BOTS.values():
        return tutorial.TutorialBot(seed=seed, lesson=next(n for n, b in tutorial.BOTS.items() if b == level))
    return make_bot(BOT_LEVELS[level], seed)


def deck_list(slug: str) -> list[str]:
    """A seat's deck as card ids: a premade deck, or one of the tutorial's fixed deals."""
    return list(tutorial.DECKS[slug]) if slug in tutorial.DECKS else load_premade_deck(slug)


@dataclass
class Seat:
    token: str
    name: str
    bot: Optional[str] = None        # bot level, or None for a human
    deck: Optional[str] = None
    ready: bool = False
    profile: Optional[str] = None    # the player's profile id, when they have one
    ladder: Optional[str] = None     # on the ladder (a ranked match): a person's profile id, or a bot's ladder id
    rating: Optional[str] = None     # a ranked match: the seat's rating as shown when it opened ("1781", "1500?")

    @property
    def is_bot(self) -> bool:
        return self.bot is not None


@dataclass
class Move:
    """One top-level action and everything that resolved under it (choices included)."""
    round: int
    seat: str
    kind: str                        # "draw" | "place" | "roam" (card: the animal that roamed)
    card: Optional[str] = None
    target: Optional[list] = None
    fx: list = field(default_factory=list)
    pre: dict = field(default_factory=dict, repr=False)
    events: list = field(default_factory=list, repr=False)   # the engine's events under this move, in order

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


def _jsonable(x):
    """Sets (hand iids in a move's snapshot) become sorted lists; membership tests still work."""
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, set):
        return sorted(x)
    return x


def _effects(events: list, move: Move) -> list:
    """What a move did, read from the engine's events in the order they happened (public facts only): an enemy covered,
    each removal and bounce (exactly which unit), cards drawn, food from cards (a turn's region income is not the move's)."""
    fx = []
    for e in events:
        if e["e"] == "cover" and e["owner"] != move.seat:
            fx.append({"k": "cover", "card": e["card"], "owner": e["owner"]})
        elif e["e"] == "remove" and e.get("cr"):
            fx.append({"k": "remove", "card": e["card"], "owner": e["owner"]})
        elif e["e"] == "bounce":
            fx.append({"k": "bounce", "card": e["card"], "owner": e["owner"]})
        elif e["e"] == "to_deck":
            fx.append({"k": "to_deck", "card": e["card"], "owner": e["owner"]})
        elif e["e"] == "draw":
            fx.append({"k": "draw", "seat": e["player"], "n": len(e["cards"])})
        elif e["e"] == "food" and not e.get("income"):
            fx.append({"k": "food", "seat": e["player"], "n": e["n"]})
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
    if e["e"] == "to_hand" and e["player"] != viewer and not e.get("public"):
        return {k: v for k, v in e.items() if k not in ("card",)}
    if e["e"] == "leave_hand" and e["owner"] != viewer:   # which card went back to their deck is theirs to know
        return {k: v for k, v in e.items() if k not in ("card",)}
    return e


class Match:
    def __init__(self, match_id: str, host: Seat):
        self.id = match_id
        self.seats: dict[str, Seat] = {"A": host}
        self.events: list[dict] = []     # the game's engine events, numbered (`seq`); see _take_events
        self.seq = 0
        self.played: dict[str, int] = {}   # seat -> the last event its screen has played out (server._watched); not saved
        self.phase = "lobby"             # lobby -> prematch -> playing -> game_over -> match_over
        self.results: list[dict] = []    # one {winner, reason, turns} per finished game
        self.hold = False                # the tutorial's coach is talking: its opponent waits (not saved)
        self.last_game: Optional[dict] = None   # the previous match's last game, so a rematch's loser goes first
        self.state: Optional[GameState] = None
        self.history: list[Move] = []
        self.bots: dict[str, object] = {}
        self.version = 0                 # bumped on every change; the server pushes on bumps
        self.seed: Optional[int] = None
        self.actions: list[dict] = []    # the current game's actions, for the replayable log
        self.action_times: list[float] = []   # seconds since the game started, one per action
        self.started_at = 0.0
        self.on_game_end = None          # callback(match, log record); the server saves human games
        self.on_match_end = None         # callback(match); the server adds it to the players' histories
        self.rematches = 0               # a rematch starts a new series in the same match
        self.last_log: Optional[dict] = None   # the last finished game (game_log), for its replay
        self.clock: Optional[dict] = None   # {bank: {A, B}, holder, turn, free, since}; None when a bot plays
        self.rng = random.Random(secrets.randbits(32))
        self.created = datetime.now(timezone.utc)
        self.schedule: Optional[list[dict]] = None   # gauntlet: one {seat, deck, first} per game, in order

    def make_gauntlet(self, decks: list[str], per_seat: int, rotating: str = "B") -> None:
        """A fixed series instead of a best-of-3: `per_seat` games going first and `per_seat` going
        second with each of `decks`, alternating who starts, one deck at a time. The decks rotate
        through seat `rotating`: the bot's seat for a gauntlet, the player's for a reverse one."""
        self.schedule = [{"seat": rotating, "deck": d, "first": "A" if k % 2 == 0 else "B"}
                         for d in decks for k in range(2 * per_seat)]
        self.seats[rotating].deck = self.schedule[0]["deck"]

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
        if deck not in DECK_NAMES:
            raise EngineError(f"unknown deck {deck!r}")
        if self.phase not in ("lobby", "prematch"):
            raise EngineError("decks are fixed for the whole match")
        self.seats[s].deck = deck
        self.seats[s].ready = False
        self._maybe_prematch()

    def _maybe_prematch(self) -> None:
        if len(self.seats) == 2 and all(seat.deck for seat in self.seats.values()):
            # No Ready step (Martin, 2026-10-01): both decklists are one hover away in the game, so a match starts as
            # soon as both seats are filled.
            self.phase = "prematch"
            for seat in self.seats.values():
                seat.ready = True
            self._start_game()
        self.version += 1

    def ready(self, s: str) -> None:
        if self.phase != "prematch":
            return   # every match starts on its own now; an older client's Ready is harmless
        self.seats[s].ready = True
        if all(seat.ready for seat in self.seats.values()):
            self._start_game()
        self.version += 1

    # ----------------------------------------------------------------- games
    @property
    def tutorial(self) -> bool:
        """The tutorial: its opponent is the tutorial's bot."""
        return "B" in self.seats and self.seats["B"].bot in tutorial.BOTS.values()

    def lesson(self) -> int:
        """The tutorial's lesson (1 or 2); 0 for any other match."""
        bot = self.seats["B"].bot if "B" in self.seats else None
        return next((n for n, b in tutorial.BOTS.items() if b == bot), 0)

    def score(self) -> dict:
        return {p: sum(1 for r in self.results if r["winner"] == p) for p in "AB"}

    def _start_game(self) -> None:
        # Game 1 is a coin flip; afterwards (and in a rematch) the loser of the previous game goes first
        # (Martin, 2026-09-26). A drawn game keeps the previous first player.
        first = None
        if self.schedule:
            entry = self.schedule[len(self.results)]
            self.seats[entry.get("seat", "B")].deck, first = entry["deck"], entry["first"]
        elif self.results or self.last_game:
            last = self.results[-1] if self.results else self.last_game
            first = other_player(last["winner"]) if last["winner"] else last["first"]
        seed = self.seed = self.rng.randrange(1 << 30)
        self.actions = []
        self.action_times = []
        self.started_at = time.time()
        if self.tutorial:     # the fixed deal the lessons are written for: you first, no mulligan
            self.state = new_game(deck_list(self.seats["A"].deck), deck_list(self.seats["B"].deck), seed,
                                  map_id=MAP_ID, first_player="A", stacked=True, config=tutorial.config(2 if self.seats["B"].bot == tutorial.BOTS[2] else 1))
            tutorial.set_up(self.state, 2 if self.seats["B"].bot == tutorial.BOTS[2] else 1)
        else:
            self.state = new_game(load_premade_deck(self.seats["A"].deck),
                                  load_premade_deck(self.seats["B"].deck), seed,
                                  map_id=MAP_ID, first_player=first)
        self.bots = {s: bot_for(seat.bot, seed + i) for i, (s, seat) in enumerate(self.seats.items())
                     if seat.is_bot}
        self.history = []
        self.events, self.seq = [], 0
        self.phase = "playing"
        self.clock = None if any(seat.is_bot for seat in self.seats.values()) else \
            {"bank": {"A": CLOCK_BANK, "B": CLOCK_BANK}, "holder": None, "turn": -1, "free": 0.0, "since": time.time(),
             "mull_until": time.time() + CLOCK_MULLIGAN, "out": {"A": 0, "B": 0}}
        self._clock_update()

    def next_game(self) -> None:
        if self.phase != "game_over":
            raise EngineError("no game to continue from")
        self._start_game()
        self.version += 1

    def rematch(self) -> None:
        if self.phase != "match_over":
            raise EngineError("the match is still on")
        self.last_game = self.results[-1]
        self.results = []
        self.state = None
        self.history = []
        self.events, self.seq = [], 0
        self.rematches += 1
        self.phase = "prematch"
        for seat in self.seats.values():
            seat.ready = True
        self._start_game()
        self.version += 1

    def to_act(self) -> Optional[str]:
        if self.phase != "playing":
            return None
        return self.state.player_to_act()

    def _take_events(self) -> list:
        """The engine's new events, numbered for the game (the view sends them; a client plays what it hasn't seen)."""
        new, self.state.events = self.state.events, []
        for e in new:
            self.seq += 1
            e["seq"] = self.seq
        self.events = (self.events + new)[-EVENTS_KEPT:]
        return new

    def mulliganing(self) -> bool:
        """The game's opening mulligans are under way (both at once, on one shared clock window)."""
        st = self.state
        return bool(st and st.result is None and st.pending and st.pending.get("kind") == "mulligan")

    def act(self, s: str, action, auto: bool = False) -> None:
        """Apply one action for seat `s`: a top-level move or a pending sub-choice. `auto`: the clock acted for them."""
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
            self.actions.append({**action.to_dict(), "by": s})   # replays apply it the same way (replay.game_views)
            self.action_times.append(round(time.time() - self.started_at, 1))
            self.version += 1
            return
        if state.player_to_act() != s:
            raise EngineError("not your decision")
        # A placement starts a history entry, including a free extra play inside a Roar;
        # draws and sub-choices fold into the entry they belong to.
        starts_move = (state.pending is None and not isinstance(action, PassAction)) or isinstance(action, PlaceAction)
        pre = _snapshot(state) if starts_move else None
        roamer = state.top_unit(action.origin).card_id if isinstance(action, RoamAction) and state.top_unit(action.origin) else None
        rules.apply_action(state, action)    # validates; raises EngineError if illegal
        new = self._take_events()
        self.actions.append(action.to_dict())
        self.action_times.append(round(time.time() - self.started_at, 1))
        if starts_move:
            placed, roamed = isinstance(action, PlaceAction), isinstance(action, RoamAction)
            self.history.append(Move(
                round=pre["turn"] // 2 + 1, seat=s, kind="place" if placed else "roam" if roamed else "draw", pre=pre,
                card=action.card_id if placed else roamer,
                target=list(action.target) if placed or roamed else None))
        if self.history:
            self.history[-1].events += new
            self.history[-1].fx = _effects(self.history[-1].events, self.history[-1])
        self._check_end()
        self._clock_update()
        self.version += 1

    # ----------------------------------------------------------------- turn clock
    def _clock_update(self, now: Optional[float] = None) -> None:
        """Charge the time since the last update to whoever held the decision, then hand the
        clock to whoever must act now: a fresh free window if it changed hands or a new turn began."""
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
        CLOCK_CATCHUP_MAX) is given back, the clock starting from now (player report 2026-10-04: the opponent's moves
        animated while the clock ran). Returns whether the clock changed."""
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
        """If the player to act is out of time, act for them: decline or take the first option of a
        choice, else end their turn. Returns whether it acted."""
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
        """The seat gives up the game in play; the series goes on as after any other loss."""
        if self.phase != "playing" or self.state.result is not None:
            raise EngineError("no game to concede")
        self._clock_update()
        self._check_end(Result(other_player(s), "concede"))

    def _check_end(self, result: Optional[Result] = None) -> None:
        result = result or rules.is_terminal(self.state)
        if result is None:
            return
        self.state.result = result
        self.results.append({"winner": result.winner, "reason": result.reason,
                             "turns": self.state.turn_counter // 2 + 1,
                             "first": self.state.first_player, "opp_deck": self.seats["B"].deck,
                             "series_deck": self.seats[self.schedule[len(self.results)].get("seat", "B")].deck
                             if self.schedule else None})
        self.last_log = self.game_log()
        if self.on_game_end:
            self.on_game_end(self, self.last_log)
        score = self.score()
        over = max(score.values()) >= GAMES_TO_WIN or len(self.results) >= 2 * GAMES_TO_WIN - 1
        if self.schedule:
            over = len(self.results) >= len(self.schedule)
        self.phase = "match_over" if over else "game_over"
        if over and self.on_match_end:
            self.on_match_end(self)

    def game_log(self) -> dict:
        """The finished game in the sim.replay log format (replayable with no bot compute)."""
        r = self.results[-1]
        return {"deck_a": self.seats["A"].deck, "deck_b": self.seats["B"].deck, "seed": self.seed,
                "map_id": MAP_ID, "first_player": r["first"],
                "bots": [self.seats[p].bot or "human" for p in "AB"],
                "winner": r["winner"], "reason": r["reason"], "turns": self.state.turn_counter,
                "actions": list(self.actions), "action_times": list(self.action_times),
                "match_id": self.id, "game_no": len(self.results), "series": self.rematches,
                "lists": [list(self.state.starting_decks[p]) for p in "AB"]}

    def bot_move(self):
        """The action the bot to act would take (pure: call off the event loop, apply after)."""
        s = self.to_act()
        state = self.state.clone()
        return self.bots[s].choose(state.view_for(s), rules.legal_actions(state), state)

    def fallback_move(self):
        """A legal move when the bot's own choice failed: the Easy bot's, else the first legal action."""
        s = self.to_act()
        state = self.state.clone()
        legal = rules.legal_actions(state)
        try:
            return make_bot("greedy", self.seed).choose(state.view_for(s), legal, state)
        except Exception:
            log.exception("fallback bot failed in match %s", self.id)
            return legal[0]

    # ----------------------------------------------------------------- persistence
    def to_dict(self) -> dict:
        """Everything needed to resume this match after a server restart."""
        return {"id": self.id, "seats": {p: asdict(seat) for p, seat in self.seats.items()},
                "phase": self.phase, "results": self.results, "seed": self.seed,
                "actions": self.actions, "action_times": self.action_times,
                "started_at": self.started_at, "created": self.created.isoformat(),
                "schedule": self.schedule, "version": self.version, "rematches": self.rematches, "clock": self.clock, "last_game": self.last_game, "last_log": self.last_log,
                "state": self.state.to_dict() if self.state is not None else None,
                "history": [_jsonable(asdict(m)) for m in self.history],
                "events": self.events, "seq": self.seq}

    @staticmethod
    def from_dict(d: dict) -> "Match":
        seats = {p: Seat(**s) for p, s in d["seats"].items()}
        m = Match(d["id"], seats["A"])
        m.seats = seats
        m.phase, m.results, m.seed = d["phase"], d["results"], d["seed"]
        m.actions, m.action_times = d["actions"], d["action_times"]
        m.started_at, m.schedule, m.version = d["started_at"], d["schedule"], d["version"] + 1
        m.rematches = d.get("rematches", 0)
        m.last_game = d.get("last_game")
        m.last_log = d.get("last_log")
        m.clock = d.get("clock")
        if m.clock:
            m.clock["since"] = time.time()      # time the server was down isn't anyone's
        m.created = datetime.fromisoformat(d["created"])
        m.state = GameState.from_dict(d["state"]) if d["state"] else None
        m.history = [Move(**h) for h in d["history"]]
        m.events, m.seq = d.get("events", []), d.get("seq", 0)
        if m.state is not None and m.seed is not None:
            m.bots = {s: bot_for(seat.bot, m.seed + i) for i, (s, seat) in enumerate(m.seats.items())
                      if seat.is_bot}
        return m

    # ----------------------------------------------------------------- views
    def view(self, s: str) -> dict:
        opp = other_player(s)
        v = {
            "id": self.id, "you": s, "phase": self.phase, "version": self.version,
            # a seat's deck by name only for you or a bot: a person's deck name is theirs (their list is open, by rule)
            "seats": {p: {"name": seat.name, "bot": seat.bot, "ready": seat.ready, **({"rating": seat.rating} if seat.rating else {}),
                          **({"deck": seat.deck, "deckName": DECK_NAMES.get(seat.deck, seat.deck)} if p == s or seat.is_bot else {})}
                      for p, seat in self.seats.items()},
            "results": [{k: r[k] for k in ("winner", "reason", "turns")} for r in self.results],
            "score": self.score(),
            "lists": {p: dict(Counter(deck_list(seat.deck)))
                      for p, seat in self.seats.items() if seat.deck},
            "game": None,
            "ranked": bool(self.seats["A"].ladder and self.seats.get("B") and self.seats["B"].ladder),
        }
        if getattr(self, "rating_change", None) and s in self.rating_change:   # a ranked match just rated: your before and after
            v["rating"] = self.rating_change[s]
        if self.schedule:
            record = {}
            for r in self.results:
                d = r.get("series_deck") or r["opp_deck"]
                w, l = record.get(d, (0, 0))
                record[d] = (w + (r["winner"] == "A"), l + (r["winner"] == "B"))
            n = len(self.results)
            nxt = self.schedule[n] if n < len(self.schedule) else None
            v["gauntlet"] = {"played": n, "total": len(self.schedule),
                             "next": nxt and {"deckName": DECK_NAMES.get(nxt["deck"], nxt["deck"]),
                                              "first": nxt["first"], "yours": nxt.get("seat", "B") == s},
                             "record": [{"deckName": DECK_NAMES.get(d, d), "w": w, "l": l}
                                        for d, (w, l) in record.items()]}
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
            # "hidden": the enemy can't choose it right now (Stealth, printed or from an adjacent Armadillo).
            board[cr] = [{"iid": u.iid, "id": u.card_id, "owner": u.owner, "str": effective_strength(st, u),
                          **({"timer": timers[u.iid]} if u.iid in timers else {}),
                          **({"hidden": True} if not statics.can_be_chosen(st, u, other_player(u.owner)) else {}),
                          **({"spikes": True} if "Spikes" in st.cards[u.card_id].keywords and not u.retaliation_used else {})} for u in stack]   # until used
        g = {
            "round": st.turn_counter // 2 + 1,
            "current": st.current,
            "toAct": to_act,
            "first": st.first_player,
            "actionsLeft": st.config.actions_per_turn + bonus - st.actions_taken_this_turn,
            "actionsTotal": st.config.actions_per_turn + bonus,
            "canPass": rules.can_pass(st),
            "clock": {"on": False} if not self.clock else (self._mulligan_clock(s) if self.mulliganing() and self.clock.get("mull_until") else
                                     {**{k: self.clock[k] for k in ("bank", "holder", "free", "since")}, "now": time.time(),
                                     "on": self.clock_deadline() is not None}),
            "food": dict(st.food),
            "income": {p: rules.region_income(st, p) for p in "AB"},
            "winFood": st.game_map.win_food,
            "board": board,
            "hand": [{"iid": u.iid, "id": u.card_id, "str": placement_strength(st, u),
                      **({"ready": True} if roar_condition(st, s, u.card_id) else {})}
                     for u in st.hands[s]],
            "handCount": {p: len(st.hands[p]) for p in "AB"},
            "handLimit": st.config.hand_limit,
            "deckCount": {p: len(st.decks[p]) for p in "AB"},
            "deckLeft": dict(Counter(st.decks[s])),
            # what the opponent may still hold: their deck, their hand, and the cards a choice of theirs holds in between
            # (the mulligan's set-aside, a Scout's three, a Raven's put-back): counted out meanwhile, they told what was there
            "unseen": dict(Counter(st.decks[opp]) + Counter(u.card_id for u in st.hands[opp])
                           + Counter(c for step in st.effect_stack if step.get("player") == opp
                                     for k in ("returned", "pulled", "shuffled") for c in step.get(k, ()))),
            "removed": list(st.remove_pile),
            "result": st.result.to_dict() if st.result else None,
            "history": [m.public() for m in self.history],
            "events": [public_event(e, s) for e in self.events if not (e["e"] == "mulligan" and e["player"] != s)],
            "legal": None,
            "pending": None,
        }
        if to_act == s:
            g["legal"], g["pending"] = self._decision(s)
        elif st.result is None and rules.early_mulligan(st, s) is not None:   # your mulligan, while theirs goes on too
            g["toAct"] = s
            i = rules.early_mulligan(st, s)
            g["legal"] = {"draw": False, "place": {}, "roam": {}}
            g["pending"] = {"mode": "choice", "optional": True, "source": None, "kind": "mulligan",
                            "returned": len(st.effect_stack[i]["returned"]), "cap": st.config.mulligan_cap(s, st.first_player),
                            "options": [self._describe_option(u.iid) for u in st.hands[s]]}
        # who decides what, always stated (never left to a missing field): over, mulligan (both at once), yours / your
        # choice, theirs / their choice
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
        roams: dict[str, list] = {}       # crossroad of a roaming animal -> where it may go (Roam)
        for a in legal:
            if isinstance(a, PlaceAction):
                places.setdefault(a.card_id, []).append(list(a.target))
            elif isinstance(a, RoamAction):
                roams.setdefault(a.origin, []).append(list(a.target))
        out = {"draw": any(isinstance(a, DrawAction) for a in legal), "place": places, "roam": roams}
        if st.pending is None:
            return out, None
        p = st.pending
        step = st.effect_stack[-1] if st.effect_stack else {}
        pending = {"mode": p["mode"], "optional": bool(p.get("optional")), "source": self._source(),
                   "kind": ASKS.get(step.get("op"), "effect"),
                   "returned": len(step.get("returned", ())) if step.get("op") == "mulligan" else 0,
                   "cap": st.config.mulligan_cap(step.get("player"), st.first_player) if step.get("op") == "mulligan" else 0,
                   "options": []}
        if p["mode"] == "choice":
            pending["options"] = [self._describe_option(o) for o in p["options"]]
        if pending["kind"] == "shuffle":
            pending["left"] = step.get("remaining", 0)   # the Raven's cards still to shuffle back
        return out, pending

    def _source(self) -> Optional[str]:
        """The card whose effect is asking: every step carries it (effects.resolve stamps it), so nothing is guessed."""
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
             # A variable-strength card (Python) prints 0: its text says what it gains ("+1 for each removed animal").
             "str": 0 if c.is_dynamic else c.base_strength, "text": c.text,
             "kw": sorted(c.keywords), "cost": c.food_cost}
            for c in CARDS.values()]

