"""The tutorial: a real game on the real map with a fixed deal and a gentle opponent.

The first two turns are forced in the client (it teaches one step at a time and lets only that step be taken), so the
deal and the opponent's first turn are fixed to match what it says. After that the opponent keeps to one placement a
turn, on the empty crossroad nearest the player, never covers and never takes the den: the player meets weak enemies to
cover and an open path to the den, and wins. The lessons themselves live in the client (static/tutorial.js).
"""
from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ..bots.base import Bot
from ..engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction
from ..engine.config import Config

# Draw order, first card first. The player opens with the three the first turns place (Lion, Buffalo, Wolf) and draws a
# Jaguar and a Lion with the deck lesson; the rest are plain strong animals and a few Roars to meet later.
PLAYER_DECK = ["lion", "cape_buffalo", "dire_wolf", "jaguar", "lion", "cheetah", "dire_wolf", "jaguar", "lion",
               "cape_buffalo", "cheetah", "dire_wolf", "lion", "jaguar", "cape_buffalo", "dire_wolf", "lion", "cheetah",
               "jaguar", "lion"]
# The opponent: a Buffalo (7) walls the middle of its den, then wild dogs (1) that any animal can cover.
OPPONENT_DECK = ["cape_buffalo", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup",
                 "poppy", "rusty", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup"]
DECKS = {"tutorial_you": PLAYER_DECK, "tutorial_them": OPPONENT_DECK}
NAMES = {"tutorial_you": "Tutorial", "tutorial_them": "Wild dogs"}

# The opponent's first turn, fixed: the wall in front of its den, then a dog beside it.
OPENING = [("cape_buffalo", "5,2"), ("pup", "4,2")]


def config() -> Config:
    """The tutorial skips the mulligan: the deal is already the one the lessons need."""
    return replace(Config.default(), mulligan=False)


class TutorialBot(Bot):
    """The tutorial's opponent (seat B): the fixed opening, then one placement a turn on the leftmost empty crossroad it
    can reach (never one that would close a region for it), drawing when its hand is empty. It never covers and never
    takes the den."""

    def __init__(self, seed: Optional[int] = None):
        pass

    def choose(self, view, legal: Sequence, state=None):
        choices = [a for a in legal if isinstance(a, ChoiceAction)]
        if choices:
            return next((a for a in choices if a.choice == SKIP), choices[0])
        places = [a for a in legal if isinstance(a, PlaceAction) and not a.is_hq_capture]
        if state.turn_counter <= 1:       # the opponent's first turn: the fixed opening
            for card, cr in OPENING:
                pick = next((a for a in places if a.card_id == card and a.crossroad == cr), None)
                if pick:
                    return pick
        if state.actions_taken_this_turn:   # one placement a turn
            return PassAction()
        board = state.board
        mine = lambda cr: bool(board.get(cr)) and board[cr][-1].owner == "B"
        # never the last corner of a region: the opponent takes no food, so the tutorial ends on the player's win
        closes = lambda cr: any(cr in r.corners and all(c == cr or mine(c) for c in r.corners)
                                for r in state.game_map.regions.values())
        empty = [a for a in places if not board.get(a.crossroad) and not closes(a.crossroad)]
        if empty:
            col = lambda a: int(a.crossroad.split(",")[0])
            row = lambda a: abs(int(a.crossroad.split(",")[1]) - 2)
            empty.sort(key=lambda a: (col(a), row(a), a.crossroad))
            return empty[0]
        draw = next((a for a in legal if isinstance(a, DrawAction)), None)
        return draw or PassAction()
