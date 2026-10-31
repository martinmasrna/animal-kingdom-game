"""AtomicBot: the turn is the unit of play, for both sides (Martin, 2026-10-31).

The opponent cannot act during my turn, so a turn's actions are one move played in sequence; scoring the board between
them is like scoring a chess position with the knight in mid-air. So this search never does. It lists every whole turn
I can play (each sequence of actions and choices until the turn passes), and scores each only once it is complete: in
each of the hands it imagines for the opponent (determinization, the Expert's own five), against the opponent's best
whole reply turn, by the evaluation of the board after it. There is no model of the opponent but "the reply that is
worst for me": no GreedyBot playing them, no first action locked to one planned continuation.

    whole turns:   every sequence until the turn passes; two orders that reach the same position count once
    shortlist:     all of them scored on the board when the turn ends (mean over the imagined hands); the best
                   `turn_width` go on
    score:         mean over the imagined hands of min over the opponent's whole reply turns of my evaluation
                   after it (a capture or a food win inside it scores as the decided game it is)

A draw inside my turn splits it: what follows depends on cards I cannot see yet, so in each imagined hand (whose deck
order is fixed) the rest of the turn is the best continuation for the cards drawn there, chosen the same way. Inside an
imagined hand everything is known, so the opponent's turn, draws included, is enumerated straight through.

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
    def __init__(self, base, turn_width: int = 20, draw_width: int = 3, cap: int = 3000, workers: int = 5):
        self.base = base                 # a TurnSearcher: evaluation, imagined hands, decided-game value, mulligan
        self.turn_width = turn_width
        self.draw_width = draw_width     # continuations after a draw that get the reply search, per imagined hand
        self.cap = cap                   # whole turns enumerated at most for one side in one position
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
        Without `through_draws` a draw ends the listing there (the rest is played per imagined hand)."""
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

    def reply_value(self, s: GameState, me: str) -> float:
        """My evaluation after the opponent's best whole reply turn from `s` (their turn to act), or of `s` itself when
        the game is decided."""
        return self.best_reply(s, me)[0]

    def best_reply(self, s: GameState, me: str) -> tuple[float, list[Action]]:
        """(my evaluation after it, the actions of) the opponent's whole reply turn from `s` that is worst for me."""
        if rules.is_terminal(s) is not None:
            return self._value(s, me), []
        opp = other_player(me)
        replies = self.turns(s, opp, through_draws=True)
        if not replies:
            return self._value(s, me), []
        best = min(replies, key=lambda t: self._value(t[1], me))
        return self._value(best[1], me), best[0]

    def _finish_after_draw(self, s: GameState, me: str) -> float:
        """The rest of my turn after a draw in one imagined hand (its drawn cards known there): the best continuation,
        shortlisted on the board, the best few searched against the reply."""
        if rules.is_terminal(s) is not None or s.player_to_act() != me:
            return self.reply_value(s, me)
        rest = self.turns(s, me, through_draws=True)
        if not rest:
            return self.reply_value(s, me)
        rest.sort(key=lambda t: -self._value(t[1], me))
        return max(self.reply_value(end, me) for _, end in rest[:self.draw_width])

    # ------------------------------------------------------------------ the search

    def rank(self, state: GameState, me: str, worlds: Optional[list[GameState]] = None, progress=None) -> list[dict]:
        """Every whole turn for `me`, best first: {turn, board, score} with `score` None past the shortlist.
        `progress(rows, done, total)` hears the ranking as the shortlist's scores come in."""
        worlds = worlds or [determinize(state, me, self.base.det_rng) for _ in range(self.base.determinizations)]
        mine = self.turns(state, me, through_draws=False)
        rows = []
        for path, _ in mine:
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
            open_ = rules.is_terminal(ends[0]) is None and ends[0].player_to_act() == me     # a draw left the turn open
            board = sum(self._value(e.clone(), me) for e in ends) / len(ends)
            rows.append({"turn": path, "ends": ends, "open": open_, "board": board, "score": None})
        rows.sort(key=lambda r: -r["board"])
        short = rows[:self.turn_width]
        order = lambda: sorted(rows, key=lambda r: (r["score"] is None, -(r["score"] if r["score"] is not None else r["board"])))
        if progress:
            progress(order(), 0, len(short))
        jobs = [(i, k) for i in range(len(short)) for k in range(len(worlds))]
        values: dict = {}
        for job, v in _run_jobs(self, short, jobs, me):
            values[job] = v
            i = job[0]
            if all((i, k) in values for k in range(len(worlds))):
                vs = [values[(i, k)] for k in range(len(worlds))]
                short[i]["score"], short[i]["per_hand"] = sum(vs) / len(vs), vs
                if progress:
                    progress(order(), sum(r["score"] is not None for r in short), len(short))
        rows = order()
        for r in rows:
            r.pop("ends", None)
        return rows

    def _job(self, row: dict, k: int, me: str) -> float:
        s = row["ends"][k].clone()
        return self._finish_after_draw(s, me) if row["open"] else self.reply_value(s, me)

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
            self._plan_key = self._next_key(st, a, me)
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


# ---------------------------------------------------------------------- parallel reply search

_W: dict = {}


def _init(bot, short, me):
    _W["bot"], _W["short"], _W["me"] = bot, short, me


def _work(job):
    i, k = job
    return job, _W["bot"]._job(_W["short"][i], k, _W["me"])


def _run_jobs(bot, short, jobs, me):
    """((row, hand), value) for every job, as each finishes: in worker processes when there are enough of them."""
    if bot.workers <= 1 or len(jobs) < 4:
        for i, k in jobs:
            yield (i, k), bot._job(short[i], k, me)
        return
    ctx = mp.get_context("fork")
    with ctx.Pool(bot.workers, initializer=_init, initargs=(bot, short, me)) as pool:
        yield from pool.imap_unordered(_work, jobs)
