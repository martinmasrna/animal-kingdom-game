"""The tutorial: two lessons, each a real game on the real map with a fixed deal and a gentle opponent.

Lesson 1 teaches the basics and ends on taking the den; lesson 2 the deeper mechanics (the glow, food from a Roar,
stacks and removal, Flight, Apex Predator) and ends on 100 food, since its opponent walls its den. The client (static/
tutorial.js) forces the steps it teaches, so each lesson's deal and the opponent's first turns are fixed to match what it
says. After them the opponent keeps to one placement a turn on the empty crossroad nearest the player, never closes a
region, never covers (but for lesson 2's one scripted cover) and never takes the den: the player always wins.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Optional, Sequence

from ..bots.base import Bot
from ..engine.actions import SKIP, ChoiceAction, DrawAction, PassAction, PlaceAction
from ..engine.config import Config

# Draw order, first card first. One new idea a turn: the player opens with four (Lion, Buffalo, Wolf, Lion), places two
# (turn 1) and closes the +10 region with the other two (turn 2); turn 3 draws a Wolf and a Buffalo and covers a Pup with
# one; turn 4 draws the Lynx, whose Roar (draw 1 if you control another Cat) always works beside the Lion. No Roar comes
# before it; the rest are strong animals and Roars to meet later.
PLAYER_DECK = ["lion", "cape_buffalo", "dire_wolf", "lion", "dire_wolf", "cape_buffalo", "lynx", "jaguar", "cheetah",
               "lion", "dire_wolf", "jaguar", "cape_buffalo", "lion", "cheetah", "dire_wolf", "jaguar", "lion",
               "cape_buffalo", "lion"]
PLAYER_DECK += PLAYER_DECK[7:] + PLAYER_DECK[7:10]   # 36 cards: a slow first game never runs out (no exhaustion loss)
# The opponent: a Buffalo (7) walls the middle of its den, then wild dogs (1) that any animal can cover.
OPPONENT_DECK = ["cape_buffalo", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup",
                 "poppy", "rusty", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup"]
# Lesson 2. The player opens with Lion, Lynx (it glows once the Lion stands) and a Buffalo; the Lynx's Roar draws the
# Eagle (Flight, on your own animal first); the next draw brings the Squirrel (food from a Roar) and the Black Mamba
# (removes up to 5: the opponent's Eagle), the one after the Tiger (Apex Predator); then animals and food Roars.
PLAYER_DECK_2 = ["lion", "lynx", "cape_buffalo", "eagle", "squirrel", "black_mamba", "tiger", "dire_wolf", "lion",
                 "squirrel", "cape_buffalo", "dire_wolf", "lion", "chipmunk", "cape_buffalo", "dire_wolf", "lion",
                 "squirrel", "cape_buffalo", "dire_wolf", "lion", "chipmunk", "cape_buffalo", "dire_wolf", "lion",
                 "squirrel", "cape_buffalo", "dire_wolf", "lion", "cape_buffalo", "dire_wolf", "lion", "squirrel",
                 "cape_buffalo", "dire_wolf", "lion"]
# Its opponent walls all three crossroads before its den with 7s (a 7 can't cover a 7, so no den win), flies its Eagle
# onto the Squirrel (stacks), then plays wild dogs.
OPPONENT_DECK_2 = ["cape_buffalo", "dire_wolf", "lion", "eagle"] + OPPONENT_DECK[1:]

DECKS = {"tutorial_you": PLAYER_DECK, "tutorial_them": OPPONENT_DECK, "tutorial2_you": PLAYER_DECK_2, "tutorial2_them": OPPONENT_DECK_2}
NAMES = {"tutorial_you": "Tutorial", "tutorial_them": "Wild dogs", "tutorial2_you": "Tutorial", "tutorial2_them": "Wild dogs"}
BOTS = {1: "tutorial", 2: "tutorial2"}   # the opponent's bot name per lesson

# The opponent's scripted moves, by its turn (turn_counter): lesson 1 walls the middle of its den and puts a dog beside
# it; lesson 2 walls all three crossroads, then flies the Eagle onto the player's Squirrel (SQUIRREL: wherever it is).
SQUIRREL = "squirrel"
OPENINGS = {1: {1: [("cape_buffalo", "5,2"), ("pup", "4,2")]},
            2: {1: [("cape_buffalo", "5,2"), ("dire_wolf", "5,1")], 3: [("lion", "5,3")]}}
# Lesson 2's Eagle flies onto the Squirrel the first turn it can (the Squirrel on top of its stack), whenever that is.
AMBUSH = {2: ("eagle", SQUIRREL)}


def config(lesson: int = 1) -> Config:
    """The tutorial skips the mulligan: the deal is already the one the lessons need. Lesson 1 opens with four cards, so
    its first two turns build a whole region before any draw (one new idea a turn)."""
    return replace(Config.default(), mulligan=False, **({"first_player_opening_draw": 4} if lesson == 1 else {}))


class TutorialBot(Bot):
    """The tutorial's opponent (seat B): the fixed opening, then one placement a turn on the leftmost empty crossroad it
    can reach (never one that would close a region for it), drawing when its hand is empty. It never covers and never
    takes the den."""

    def __init__(self, seed: Optional[int] = None, lesson: int = 1):
        self.opening, self.ambush = OPENINGS[lesson], AMBUSH.get(lesson)

    def choose(self, view, legal: Sequence, state=None):
        choices = [a for a in legal if isinstance(a, ChoiceAction)]
        if choices:
            return next((a for a in choices if a.choice == SKIP), choices[0])
        places = [a for a in legal if isinstance(a, PlaceAction) and not a.is_hq_capture]
        board = state.board
        for card, cr in self.opening.get(state.turn_counter, []) + ([self.ambush] if self.ambush else []):   # scripted moves, while they can be made
            if cr == SQUIRREL:
                cr = next((c for c, st in board.items() if st and st[-1].owner == "A" and st[-1].card_id == "squirrel"), None)
            pick = next((a for a in places if a.card_id == card and a.crossroad == cr), None)
            if pick:
                return pick
        if state.units_placed_this_turn:   # one placement a turn (a draw first still leaves it one)
            return PassAction()
        if self.ambush:   # the ambush card waits for its moment, never an ordinary placement
            places = [a for a in places if a.card_id != self.ambush[0]]
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
