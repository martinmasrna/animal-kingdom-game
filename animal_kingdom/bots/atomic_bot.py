"""AtomicBot: the turn is the unit of play, for both sides (Martin, 2026-10-31).

The opponent cannot act during my turn, so a turn's actions are one move played in sequence; scoring the board between
them is like scoring a chess position with the knight in mid-air. So this search never does. It lists every whole turn
I can play (each sequence of actions and choices until the turn passes), and scores each only once it is complete: in
each hand the opponent may hold (every distinct hand their unseen cards make, at its odds: `spread`), against the
opponent's best whole reply turn, by the evaluation of the board after it. The hands are averaged as chances to win
(`_mix`), so a turn that survives in one hand in seven beats one that never does, and a 1% chance counts as 1%. There is no model of the opponent but "the reply that is
worst for me": no GreedyBot playing them, no first action locked to one planned continuation.

It looks `rounds` rounds ahead: round 1 is my turn and their best reply; round 2 adds my best next turn and their best
reply to that. Each level is iterative deepening, as a chess engine's: who goes a level deeper is chosen by the best
score already in hand, never the shallowest one.

    whole turns:   every sequence until the turn passes; two orders that reach the same position count once
    level 0        all of them scored on the board when the turn ends (over the imagined hands, at their odds)
    level 1        the best `widths[0]` of level 0: my evaluation after their best reply, over the hands
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

import math
import multiprocessing as mp
from math import comb
from typing import Optional, Sequence

from ..engine import rules
from ..engine.actions import Action, DrawAction
from ..engine.state import GameState, Rng, StateView, UnitInstance, other_player
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
                 cap: int = 3000, workers: int = 5, hands: int = 30, temperature: float = 2.3, draws: int = 8):
        self.base = base                 # a TurnSearcher: evaluation, imagined hands, decided-game value, mulligan
        self.rounds = rounds
        self.widths = widths             # my turns taken to level 1, then to level 2
        self.inner = inner               # turns followed further at each step inside a deeper line
        self.cap = cap                   # whole turns listed at most for one side in one position
        self.workers = workers
        self.hands = hands               # opponent hands scored at most: every distinct one when there are no more
        # The network's chances are too sure of themselves: at the start of 4,268 turns of 240 of Martin's games, its 5%
        # was won about 20% of the time and its 85% about 70%. Its logit divided by 2.3 fits the record best
        # (2026-10-31); the hands are averaged on that corrected scale.
        self.temperature = temperature
        self.draws = draws               # ways a draw can come out followed at most: the likeliest
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

    def _mix(self, vs: Sequence[float], ws: Sequence[float]) -> float:
        """The value over the imagined hands, each by its odds: the evaluation is a win logit (times the network's
        scale, and over the `temperature` that makes it a true chance), so the hands are averaged as chances to win and
        the mean turned back into the same units. A decided
        game (+/- decisive) counts as a sure win or loss; a 1% chance at a win is worth 1% of one."""
        scale = getattr(self.base.evaluator, "scale", None)
        if not scale:
            return sum(v * w for v, w in zip(vs, ws))
        scale *= self.temperature
        p = 0.0
        for v, w in zip(vs, ws):
            p += w / (1.0 + math.exp(-v / scale))
        cap = self.base.decisive
        if p <= 0.0:
            return -cap
        if p >= 1.0:
            return cap
        return max(-cap, min(cap, scale * math.log(p / (1.0 - p))))

    def spread(self, state: GameState, me: str) -> tuple[list[GameState], list[float]]:
        """The hands the opponent may hold, as imagined worlds with their odds: every distinct hand their unseen cards
        can make, weighted by how many ways it can be dealt (the deck orders, mine and theirs, drawn at random per
        hand); when there are more than `hands` of them, that many hands dealt at random, equally weighted."""
        opp = other_player(me)
        rng = self.base.det_rng
        hand = state.hands[opp]
        kept = [u for u in hand if u.locked_until_turn > state.turn_counter]
        hidden = len(hand) - len(kept)
        pool = sorted([u.card_id for u in hand if u not in kept] + list(state.decks[opp]))
        kinds = sorted(set(pool))
        counts = [pool.count(c) for c in kinds]
        found: list[list[int]] = []

        def walk(i: int, left: int, ks: list[int]) -> bool:
            if len(found) > self.hands:
                return False
            if i == len(kinds):
                if left == 0:
                    found.append(list(ks))
                return True
            for k in range(min(counts[i], left) + 1):
                if not walk(i + 1, left - k, ks + [k]):
                    return False
            return True

        if not walk(0, hidden, []) or len(found) > self.hands:
            worlds = [determinize(state, me, rng) for _ in range(self.hands)]
            return worlds, [1.0 / len(worlds)] * len(worlds)
        worlds, weights = [], []
        for ks in found:
            x = state.clone()
            x.decks[me].sort()
            rng.shuffle(x.decks[me])
            cards = [c for c, k in zip(kinds, ks) for _ in range(k)]
            rest = list(pool)
            for c in cards:
                rest.remove(c)
            rng.shuffle(rest)
            x.hands[opp] = list(kept) + [UnitInstance(c, opp, x.new_iid()) for c in cards]
            x.decks[opp] = rest
            x.rng = Rng(rng.getrandbits(64))
            weight = 1
            for c, k in zip(counts, ks):
                weight *= comb(c, k)
            worlds.append(x)
            weights.append(float(weight))
        total = sum(weights)
        return worlds, [w / total for w in weights]

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

    def _outcomes(self, st: GameState, actor: str, a: Action, k: int) -> list[tuple[float, GameState, tuple]]:
        """The ways action `a`, which takes `k` cards from the actor's deck, can come out: every distinct set of cards it
        can take, with its odds, as (odds, the position after, the cards). Neither side knows the order of a deck, so a
        draw is a chance event, not a choice: the drawer gets the average over what it may bring, never the card it
        would like. More than `draws` of them: that many picked evenly across their odds."""
        deck = st.decks[actor]
        kinds = sorted(set(deck))
        counts = [deck.count(c) for c in kinds]
        found: list[list[int]] = []

        def walk(i: int, left: int, ks: list[int]) -> None:
            if i == len(kinds):
                if left == 0:
                    found.append(list(ks))
                return
            for n in range(min(counts[i], left) + 1):
                walk(i + 1, left - n, ks + [n])

        walk(0, k, [])
        scored = []
        for ks in found:
            weight = 1
            for c, n in zip(counts, ks):
                weight *= comb(c, n)
            scored.append((float(weight), ks))
        if len(scored) > self.draws:
            # more ways than `draws`: that many picked evenly across their odds (systematic sampling: points at
            # (j + 1/2) / draws on the running total), each pick worth 1 / draws; the likeliest alone would over-weight
            # pairs of the same card and could drop the one card that saves the drawer
            total = sum(w for w, _ in scored)
            picked: dict = {}
            run, i = scored[0][0] / total, 0
            for j in range(self.draws):
                point = (j + 0.5) / self.draws
                while run < point and i < len(scored) - 1:
                    i += 1
                    run += scored[i][0] / total
                picked[i] = picked.get(i, 0) + 1
            scored = [(float(n), scored[i][1]) for i, n in sorted(picked.items())]
        total = sum(w for w, _ in scored)
        out = []
        for w, ks in scored:
            taken = [c for c, n in zip(kinds, ks) for _ in range(n)]
            out.append((w / total, self._dealt(st, actor, a, taken), tuple(taken)))
        return out

    @staticmethod
    def _dealt(st: GameState, actor: str, a: Action, taken: list) -> GameState:
        """The position after action `a` when the cards it takes from the actor's deck are `taken`."""
        want = list(taken)
        rest = []
        for c in reversed(st.decks[actor]):       # the deck is drawn from its end: the taken cards go there
            if c in want:
                want.remove(c)
            else:
                rest.append(c)
        x = st.clone()
        x.decks[actor] = rest[::-1] + list(taken)
        rules.apply_action(x, a, validate=False)
        return x

    def _by_card(self, s: GameState, actor: str, me: str, a: Action, k: int) -> Optional[float]:
        """The opponent's draw in their last turn of a line, judged card by card (Martin, 2026-11-01: after a draw they
        have one play left, so of the cards drawn only one can be played, and pairs do not matter). My evaluation sees
        their hand only as its size, so a card left in it changes nothing: their best play with each card type is
        searched once, and the draw is worth, over every set of cards it can bring at its odds, the best of what they
        could do without the new cards and with each of them. None when a line could place two of the drawn cards (an
        extra placement): then the sets of cards are searched one by one."""
        deck = s.decks[actor]
        kinds = sorted(set(deck))
        before = {u.iid for u in s.hands[actor]}
        chain = [False]
        # a draw that ends their turn changes nothing I can see but their hand's size: one position, whatever it brings
        x = self._dealt(s, actor, a, deck[len(deck) - min(k, len(deck)):][:k])
        self._resolve_others(x, actor)
        if rules.is_terminal(x) is not None or x.player_to_act() != actor:
            return self._value(x, me)

        def judged(card):
            def leaf(e, hist, prob):
                gone = [u for u in drawn if u.iid not in {h.iid for h in e.hands[actor]}]
                if len(gone) > 1:
                    chain[0] = True
                if card is None:
                    return self._value(e, me) if not gone else None
                return self._value(e, me) if [u.card_id for u in gone] == [card] else None
            return leaf

        values = {}
        base = None
        for c in kinds:
            others = list(deck)
            others.remove(c)
            x = self._dealt(s, actor, a, others[len(others) - (k - 1):] + [c] if k > 1 else [c])
            drawn = [u for u in x.hands[actor] if u.iid not in before]
            if base is None:
                r = self._tree(x.clone(), actor, me, judged(None), (), {})
                base = r[0] if r is not None else math.inf
            r = self._tree(x, actor, me, judged(c), (), {})
            values[c] = r[0] if r is not None else math.inf
            if chain[0]:
                return None
        counts = [deck.count(c) for c in kinds]
        found: list = []

        def walk(i, left, ks):
            if i == len(kinds):
                if left == 0:
                    found.append(list(ks))
                return
            for n in range(min(counts[i], left) + 1):
                walk(i + 1, left - n, ks + [n])

        walk(0, k, [])
        vals, ws = [], []
        for ks in found:
            weight = 1
            for c, n in zip(counts, ks):
                weight *= comb(c, n)
            vals.append(min([base] + [values[c] for c, n in zip(kinds, ks) if n]))
            ws.append(float(weight))
        total = sum(ws)
        return self._mix(vals, [w / total for w in ws])

    def _tree(self, s: GameState, actor: str, me: str, leaf, hist: tuple, memo: dict, prob: float = 1.0,
              alpha: float = -math.inf, beta: float = math.inf, last: bool = False) -> Optional[tuple[float, list]]:
        """The value of `actor`'s best whole turn from `s` and its actions up to the first draw: a decision is the best
        of its actions for the actor, a draw (anything taken from the actor's deck) the average over what it may bring,
        a finished turn `leaf(end, hist, prob)` (None: not followed, so never chosen). `hist` is the cards drawn so far,
        `prob` their odds. A decision stops looking once it has a decided win for the actor: nothing can beat it; and,
        before any draw, once it has a turn the side choosing above would never allow (mine at `beta` or more, theirs at
        `alpha` or less: the cut-off of a chess engine). After a draw nothing is cut: the average needs every value."""
        self._resolve_others(s, actor)
        if rules.is_terminal(s) is not None or s.player_to_act() != actor:
            v = leaf(s, hist, prob)
            return None if v is None else (v, [])
        key = (_key(s), hist)
        if key in memo:
            return memo[key]
        mine = actor == me
        best = None
        for a in rules.legal_actions(s):
            nxt = s.clone()
            rules.apply_action(nxt, a, validate=False)
            k = len(s.decks[actor]) - len(nxt.decks[actor])
            judged = self._by_card(s, actor, me, a, k) if k > 0 and last and actor != me else None
            if judged is not None:
                v, path = judged, [a]
            elif k > 0:
                outs = self._outcomes(s, actor, a, k)
                vals = []
                for w, x, taken in outs:
                    r = self._tree(x, actor, me, leaf, hist + (taken,), memo, prob * w)
                    if r is None:
                        break
                    vals.append(r[0])
                if len(vals) < len(outs):
                    continue
                v, path = self._mix(vals, [w for w, _, _ in outs]), [a]
            else:
                r = self._tree(nxt, actor, me, leaf, hist, memo, prob, alpha, beta, last)
                if r is None:
                    continue
                v, path = r[0], [a] + r[1]
            if best is None or (v > best[0] if mine else v < best[0]):
                best = (v, path)
                if (v >= self.base.decisive) if mine else (v <= -self.base.decisive):
                    break
                if not hist and ((v >= beta) if mine else (v <= alpha)):
                    break
        memo[key] = best
        return best

    def line_value(self, s: GameState, me: str, plies: int, alpha: float = -math.inf, beta: float = math.inf) -> float:
        """My evaluation of `s` (the start of a turn, or decided) looking `plies` whole turns ahead, each side playing
        its best turn: the last one judged on the board, the earlier ones by following, for every set of cards drawn,
        the best `inner` of their finished turns for that side further. Outside (`alpha`, `beta`) the value is only a
        bound: the side choosing above already has better."""
        return self.best_line(s, me, plies, alpha, beta)[0]

    def best_line(self, s: GameState, me: str, plies: int, alpha: float = -math.inf,
                  beta: float = math.inf) -> tuple[float, list[Action]]:
        """(the value, the actions of the first turn up to its first draw of) the line `line_value` follows."""
        if plies <= 0 or rules.is_terminal(s) is not None:
            return self._value(s, me), []
        actor = s.player_to_act()
        mine = actor == me
        if plies == 1:
            r = self._tree(s.clone(), actor, me, lambda e, hist, prob: self._value(e, me), (), {}, 1.0, alpha, beta,
                           last=True)
            return r if r is not None else (self._value(s, me), [])
        ends: dict = {}

        def board(e, hist, prob):
            v = self._value(e, me)
            ends.setdefault(hist, {}).setdefault(_key(e), v)
            return v

        first = self._tree(s.clone(), actor, me, board, (), {})
        if first is None:
            return self._value(s, me), []
        followed = {h: set(k for k, _ in sorted(es.items(), key=lambda t: -t[1] if mine else t[1])[:self.inner])
                    for h, es in ends.items()}
        achieved = [alpha if mine else beta]      # the best this side is sure of so far, as a bound for the next line

        def deeper(e, hist, prob):
            if _key(e) not in followed.get(hist, ()):
                return None
            if hist:                              # after a draw: one of an average, so exact
                return self.line_value(e, me, plies - 1)
            v = self.line_value(e, me, plies - 1, *((achieved[0], beta) if mine else (alpha, achieved[0])))
            achieved[0] = max(achieved[0], v) if mine else min(achieved[0], v)
            return v

        r = self._tree(s.clone(), actor, me, deeper, (), {}, 1.0, alpha, beta)
        return r if r is not None else first

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
        r = self._tree(s.clone(), me, me, lambda e, hist, prob: self._remembered(e, me, plies, hand), (), {})
        return self._remembered(s, me, plies, hand) if r is None else r[0]

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

    def rank(self, state: GameState, me: str, worlds: Optional[list[GameState]] = None, progress=None,
             weights: Optional[list[float]] = None) -> list[dict]:
        """Every whole turn for `me`, best first: {turn, board, levels: [round 1 score, round 2 score...]}, a level's
        score None for a turn that did not reach it. `progress(rows, level, done, total)` hears the ranking fill.
        `worlds` (with `weights`, equal by default) replaces the spread of the opponent's possible hands."""
        if worlds is None:
            worlds, weights = self.spread(state, me)
        weights = weights or [1.0 / len(worlds)] * len(worlds)
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
            board = self._mix([self._best_board(e, me) if open_ else self._value(e.clone(), me) for e in ends], weights)
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
            # a turn already won or lost outright in a hand one level up stays so deeper: nothing to search there
            values: dict = {}
            if lv > 0:
                for i, r in enumerate(go):
                    for k, v in enumerate(r["per_hand"][lv - 1]):
                        if abs(v) >= self.base.decisive:
                            values[(i, k)] = v
            jobs = [(i, k) for i in range(len(go)) for k in range(len(worlds)) if (i, k) not in values]

            def finish(i):
                if go[i]["levels"][lv] is None and all((i, k) in values for k in range(len(worlds))):
                    vs = [values[(i, k)] for k in range(len(worlds))]
                    go[i]["levels"][lv], go[i]["per_hand"][lv] = self._mix(vs, weights), vs
                    if progress:
                        progress(order(), lv + 1, sum(r["levels"][lv] is not None for r in go), len(go))

            for i in range(len(go)):
                finish(i)
            for job, v in _run_jobs(self, go, jobs, me, plies):
                values[job] = v
                finish(job[0])
            pool = sorted(go, key=lambda r: -r["levels"][lv])
        rows = order()
        for r in rows:
            r.pop("ends", None)
            r["score"] = next((v for v in reversed(r["levels"]) if v is not None), None)
        return rows

    def _best_board(self, e: GameState, me: str) -> float:
        """The board a turn a draw left open reaches, in this imagined hand, by its best continuation."""
        r = self._tree(e.clone(), me, me, lambda end, hist, prob: self._value(end, me), (), {})
        return self._value(e.clone(), me) if r is None else r[0]

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
