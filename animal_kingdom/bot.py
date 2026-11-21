"""The Practice opponent. `SearchBot` is the engine's own bot (`engine_rs/src/bots/`, by its spec: the whole-turn search);
it reads the position only as its seat may know it. `GreedyBot` is the one-action-at-a-time bot the game shipped with,
which plays a move whenever the search bot fails: at each decision it tries every legal action on a copy of the game and
keeps the one whose position it scores best. Both keep their opening hand."""

from __future__ import annotations

import logging
import random
from typing import Optional

import ak_engine

from .game import SKIP, Action, ChoiceAction, GameState, PassAction, action_from_dict, other_player

log = logging.getLogger(__name__)
WIN = 1_000_000.0


def evaluate(rs, me: str, game_map) -> float:
    """How good the engine's position `rs` is for `me`."""
    opp = other_player(me)
    d = rs.to_dict()
    if d["result"] is not None:
        return WIN if d["result"]["winner"] == me else -WIN if d["result"]["winner"] == opp else 0.0
    score = d["food"][me] - d["food"][opp]
    score += 2.0 * (rs.region_income(me) - rs.region_income(opp))
    for stack in d["board"].values():
        top = stack[-1]
        score += (1.0 if top["owner"] == me else -1.0) * (1.0 + 0.3 * rs.effective_strength(top["iid"]))
    # a connected animal on the other side's base can raid next turn
    for p, sign in ((me, 1.0), (opp, -1.0)):
        occ = set(rs.connected_occupied(p))
        score += sign * 4.0 * sum(1 for cr in game_map.hq_front(other_player(p)) if cr in occ)
    score += 0.8 * (len(d["hands"][me]) - len(d["hands"][opp]))
    return score


class GreedyBot:
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def choose(self, state: GameState) -> Action:
        """The action the bot takes for the player to act in `state`."""
        rs = state._sync()
        legal = rs.legal_actions()
        if not legal:
            return PassAction()
        if state.pending is not None and state.pending.get("kind") == "mulligan":
            return ChoiceAction(SKIP)
        me = state.player_to_act()
        best_score, best = -float("inf"), []
        for action in legal:
            nxt = rs.clone()
            nxt.apply_action(action, False)
            score = evaluate(nxt, me, state.game_map)
            if score > best_score:
                best_score, best = score, [action]
            elif score == best_score:
                best.append(action)
        return action_from_dict(best[0] if len(best) == 1 else self.rng.choice(best))


class SearchBot:
    """The engine's bot `spec` (`engine_rs/src/bots/`; `tools/bot_bench/README.md` lists the specs). It plans across the
    actions of a turn, so one game gets one SearchBot. A move it fails on is played by the greedy bot."""

    def __init__(self, spec: str, seed: int):
        self.spec = spec
        self.failures = 0
        self._greedy = GreedyBot(seed)
        try:
            self._bot = ak_engine.Bot(spec, seed % (1 << 64))
        except Exception:   # a spec the built engine does not know: the greedy bot plays the game
            log.exception("no bot %r; the greedy bot plays", spec)
            self._bot = None

    def choose(self, state: GameState) -> Action:
        """The action the bot takes for the player to act in `state`."""
        if self._bot is not None:
            try:
                return action_from_dict(self._bot.choose(state._sync()))
            except BaseException as e:   # an error, or a panic the binding did not turn into one
                if not isinstance(e, Exception) and type(e).__name__ != "PanicException":
                    raise
                self.failures += 1
                log.exception("the bot %r failed; the greedy bot plays this move", self.spec)
        return self._greedy.choose(state)
