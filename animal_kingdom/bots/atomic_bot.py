"""AtomicBot: the turn is the unit of play, for both sides (Martin, 2026-10-31).

The opponent cannot act during my turn, so a turn's actions are one move played in sequence; scoring the board between
them is like scoring a chess position with the knight in mid-air. So this search never does. It lists every whole turn
I can play (each sequence of actions and choices until the turn passes), and scores each only once it is complete: in
each of the hands it imagines for the opponent (determinization, the Expert's own five), against the opponent's best
whole reply turn, by the evaluation of the board after it. There is no model of the opponent but "the reply that is
worst for me": no GreedyBot playing them, no first action locked to one planned continuation.

It looks `rounds` rounds ahead: round 1 is my turn and their best reply; round 2 adds my best next turn and their best
reply to that. Each level is iterative deepening, as a chess engine's: who goes a level deeper is chosen by the best
score already in hand, never the shallowest one.

    whole turns:   every sequence until the turn passes; two orders that reach the same position count once
    level 0        all of them scored on the board when the turn ends (mean over the imagined hands)
    level 1        the best `widths[0]` of level 0: mean over the hands of my evaluation after their best reply
    level 2        the best `widths[1]` of level 1: their reply, my next turn, their reply to that

Inside a deeper line every whole turn of the side to act is listed and scored on the board; the best `inner` of them
for that side are followed further, and the last turn of the line is the plain best of all of them.

A draw inside my turn splits it: what follows depends on cards I cannot see yet, so in each imagined hand (whose deck
order is fixed) the rest of the turn is the best continuation for the cards drawn there, chosen the same way. Inside an
imagined hand everything is known, so later turns, draws included, are listed straight through.

The evaluation, the imagined hands, the decided-game value and the opening hand come from a base searcher (the Expert's
RefereeBot), so the two bots differ only in the search.
"""
from __future__ import annotations

import multiprocessing as mp
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import Action, DrawAction
from ..engine.state import GameState, StateView, other_player
from ..engine.strength import effective_strength
from .base import Bot
from .determinize import determinize


def _key(s: GameState) -> tuple:
    """A position, for merging turns that reach it by different orders: the board's stacks, both hands, food, decks
    and whether the game is decided. Unit ids are left out (tokens made in another order get other ids)."""
    board = tuple(sorted((cr, tuple((u.card_id, u.owner, effective_strength(s, u)) for u in st))
                         for cr, st in s.board.items() if st))
    hands = tuple(tuple(sorted(u.card_id for u in s.hands[p])) for p in ("A", "B"))
    result = rules.is_terminal(s)
    return (board, hands, tuple(sorted(s.food.items())), tuple(len(s.decks[p]) for p in ("A", "B")),
            s.current, result.winner if result else None)


class AtomicBot(Bot):
    def __init__(self, base, rounds: int = 1, widths: tuple = (60, 20), inner: int = 4,
                 cap: int = 3000, workers: int = 5):
        self.base = base                 # a TurnSearcher: evaluation, imagined hands, decided-game value, mulligan
        self.rounds = rounds
        self.widths = widths             # my turns taken to level 1, then to level 2
        self.inner = inner               # turns followed further at each step inside a deeper line
        self.cap = cap                   # whole turns listed at most for one side in one position
        self.workers = workers
        self._plan: list[Action] = []
        self._plan_key = None
        self.last_ranking: list[dict] = []

    # ------------------------------------------------------------------ evaluation

    def _value(self, s: GameState, me: str) -> float:
        r = rules.is_terminal(s)
        if r is not None:
            s.result = r
        return self.base._clamped_eval(s, me)

    def _resolve_others(self, s: GameState, actor: str) -> None:
        """A choice the other side must make inside `actor`'s turn: theirs by the base's fast policy."""
        for _ in range(20):
            if rules.is_terminal(s) is not None or s.pending is None or s.player_to_act() == actor or s.current != actor:
                return
            who = s.player_to_act()
            rules.apply_action(s, self.base._policy.choose(s.view_for(who), rules.legal_actions(s), s), validate=False)

    def turns(self, s: GameState, actor: str, through_draws: bool) -> list[tuple[list[Action], GameState]]:
        """Every whole turn `actor` can play from `s`, one per position it ends on: (the actions, the end position).
        Without `through_draws`, anything taken from the actor's own deck ends the listing there (the rest is played
        per imagined hand)."""
        seen: dict = {}
        out: list[tuple[list[Action], GameState]] = []

        def walk(st: GameState, path: list[Action]):
            if len(out) >= self.cap:
                return
            self._resolve_others(st, actor)
            if rules.is_terminal(st) is not None or st.player_to_act() != actor:
                k = _key(st)
                if k not in seen:
                    seen[k] = True
                    out.append((path, st))
                return
            for a in rules.legal_actions(st):
                nxt = st.clone()
                rules.apply_action(nxt, a, validate=False)
                # anything taken from my own deck (a draw, a card an effect plays or shows from it) is unseen until it
                # happens: the turn splits there, as at a draw
                if not through_draws and (isinstance(a, DrawAction) or len(nxt.decks[actor]) != len(st.decks[actor])):
                    out.append((path + [a], nxt))
                    continue
                walk(nxt, path + [a])

        walk(s.clone(), [])
        return out

    def line_value(self, s: GameState, me: str, plies: int) -> float:
        """My evaluation of `s` (the start of a turn, or decided) looking `plies` whole turns ahead, each side playing
        its best turn: the last one the best of all its turns on the board, the earlier ones the best `inner` of them
        followed further."""
        return self.best_line(s, me, plies)[0]

    def best_line(self, s: GameState, me: str, plies: int) -> tuple[float, list[Action]]:
        """(the value, the actions of the first turn of) the line `line_value` follows."""
        if plies <= 0 or rules.is_terminal(s) is not None:
            return self._value(s, me), []
        actor = s.player_to_act()
        ends = self.turns(s, actor, through_draws=True)
        if not ends:
            return self._value(s, me), []
        mine = actor == me
        scored = sorted(((self._value(end, me), path, end) for path, end in ends), key=lambda t: t[0], reverse=mine)
        if plies == 1:
            return scored[0][0], scored[0][1]
        pick = max if mine else min
        followed = [(self.line_value(end, me, plies - 1), path) for _, path, end in scored[:self.inner]]
        best = pick(followed, key=lambda t: t[0])
        return best[0], best[1]

    def best_reply(self, s: GameState, me: str) -> tuple[float, list[Action]]:
        """(my evaluation after it, the actions of) the opponent's whole reply turn from `s` that is worst for me."""
        return self.best_line(s, me, 1)

    def _after_my_turn(self, s: GameState, me: str, open_: bool, plies: int, hand: int = -1) -> float:
        """The value of my turn ending in `s`, looking `plies` turns past it; a turn a draw left open is finished in
        this imagined hand (`hand`) by the best of every continuation for the cards drawn there. Every one, never a
        board-scored shortlist: "draw, then the Orangutan" reaches the same position as "the Orangutan, then draw" in
        the same hand, so drawing first can never score below it (Martin, 2026-10-31: "if you're going to draw anyway,
        you might as well do it first"). Positions already scored in this hand are remembered, which keeps it cheap."""
        if not open_ or rules.is_terminal(s) is not None or s.player_to_act() != me:
            return self._remembered(s, me, plies, hand)
        rest = self.turns(s, me, through_draws=True)
        if not rest:
            return self._remembered(s, me, plies, hand)
        return max(self._remembered(end, me, plies, hand) for _, end in rest)

    def _remembered(self, s: GameState, me: str, plies: int, hand: int) -> float:
        key = (hand, plies, _key(s))
        memo = self.__dict__.setdefault("_memo", {})
        if hand < 0 or key not in memo:
            v = self.line_value(s, me, plies)
            if hand < 0:
                return v
            memo[key] = v
        return memo[key]

    # ------------------------------------------------------------------ the search

    def rank(self, state: GameState, me: str, worlds: Optional[list[GameState]] = None, progress=None) -> list[dict]:
        """Every whole turn for `me`, best first: {turn, board, levels: [round 1 score, round 2 score...]}, a level's
        score None for a turn that did not reach it. `progress(rows, level, done, total)` hears the ranking fill."""
        worlds = worlds or [determinize(state, me, self.base.det_rng) for _ in range(self.base.determinizations)]
        self._memo = {}
        rows = []
        for path, _ in self.turns(state, me, through_draws=False):
            ends = []
            for w in worlds:
                x = w.clone()
                try:
                    for a in path:
                        rules.apply_action(x, a, validate=False)
                except Exception:     # the step that reached into the deck reads another card in this hand
                    break
                self._resolve_others(x, me)
                ends.append(x)
            if len(ends) < len(worlds):
                continue
            open_ = rules.is_terminal(ends[0]) is None and ends[0].player_to_act() == me     # a draw left it open
            # never the board in mid-turn: a turn a draw left open scores, in each hand, the best board its
            # continuations reach with the cards drawn there
            board = sum((max((self._value(end, me) for _, end in self.turns(e, me, through_draws=True)),
                             default=self._value(e.clone(), me)) if open_ else self._value(e.clone(), me))
                        for e in ends) / len(ends)
            rows.append({"turn": path, "ends": ends, "open": open_, "board": board,
                         "levels": [None] * self.rounds, "per_hand": [None] * self.rounds})

        def order():
            def key(r):
                for lv in range(self.rounds - 1, -1, -1):
                    if r["levels"][lv] is not None:
                        return (-(lv + 1), -r["levels"][lv])
                return (0, -r["board"])
            return sorted(rows, key=key)

        if progress:
            progress(order(), 0, 0, len(rows))
        pool = sorted(rows, key=lambda r: -r["board"])
        for lv in range(self.rounds):
            go = pool[:self.widths[min(lv, len(self.widths) - 1)]]
            plies = 2 * lv + 1
            jobs = [(i, k) for i in range(len(go)) for k in range(len(worlds))]
            values: dict = {}
            for job, v in _run_jobs(self, go, jobs, me, plies):
                values[job] = v
                i = job[0]
                if all((i, k) in values for k in range(len(worlds))):
                    vs = [values[(i, k)] for k in range(len(worlds))]
                    go[i]["levels"][lv], go[i]["per_hand"][lv] = sum(vs) / len(vs), vs
                    if progress:
                        progress(order(), lv + 1, sum(r["levels"][lv] is not None for r in go), len(go))
            pool = sorted(go, key=lambda r: -r["levels"][lv])
        rows = order()
        for r in rows:
            r.pop("ends", None)
            r["score"] = next((v for v in reversed(r["levels"]) if v is not None), None)
        return rows

    def _job(self, row: dict, k: int, me: str, plies: int) -> float:
        return self._after_my_turn(row["ends"][k].clone(), me, row["open"], plies, hand=k)

    def choose(self, view: StateView, legal: Sequence[Action], state: Optional[GameState] = None) -> Action:
        legal = list(legal)
        if state is None or len(legal) == 1:
            return legal[0]
        me = view.player
        st = state
        if st.pending is not None and st.effect_stack and st.effect_stack[-1].get("op") == "mulligan" \
                or rules.early_mulligan(st, me) is not None:
            return self.base.choose(view, legal, state)
        key = self.base._observation_key(st, me)
        if self._plan and self._plan_key == key and self._plan[0] in legal:
            a = self._plan.pop(0)
            self._plan_key = self._next_key(st, a, me) if self._plan else None
            return a
        ranking = self.rank(st, me)
        self.last_ranking = ranking
        best = ranking[0]["turn"]
        a, self._plan = best[0], list(best[1:])
        if isinstance(a, DrawAction):      # what follows a draw is planned once the cards are seen
            self._plan = []
        self._plan_key = self._next_key(st, a, me) if self._plan else None
        return a

    def _next_key(self, st: GameState, a: Action, me: str):
        nxt = st.clone()
        rules.apply_action(nxt, a, validate=False)
        return self.base._observation_key(nxt, me)


# ---------------------------------------------------------------------- parallel search

_W: dict = {}


def _init(bot, rows, me, plies):
    _W["bot"], _W["rows"], _W["me"], _W["plies"] = bot, rows, me, plies


def _work(job):
    i, k = job
    return job, _W["bot"]._job(_W["rows"][i], k, _W["me"], _W["plies"])


def _run_jobs(bot, rows, jobs, me, plies):
    """((row, hand), value) for every job, as each finishes: in worker processes when there are enough of them."""
    if bot.workers <= 1 or len(jobs) < 4:
        for i, k in jobs:
            yield (i, k), bot._job(rows[i], k, me, plies)
        return
    ctx = mp.get_context("fork")
    with ctx.Pool(bot.workers, initializer=_init, initargs=(bot, rows, me, plies)) as pool:
        yield from pool.imap_unordered(_work, jobs)
