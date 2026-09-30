"""The tutorial: two lessons, each a real game on the real map with a fixed deal and a gentle opponent.

Lesson 1 teaches the basics and ends on 100 food (its regions); lesson 2 the deeper mechanics (the glow, Flight, stacks
and removal, Apex Predator) and ends on taking the den, once the Polar Bear has eaten a way through its wall of 7s. The client (static/
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

# Draw order, first card first. One new idea a turn: the player opens with four (Lion, Buffalo, Wolf, Buffalo), places two
# (turn 1) and closes the +10 region with the other two (turn 2); turn 3 draws a Wolf and a Pup (1: the cover lesson's other half, 1 can't beat 1) and covers a Pup with
# one; turn 4 draws the Squirrel, whose Roar (gain 10 food) has no condition, so it doesn't glow: the glow is lesson 2's. No
# Roar comes before it; the rest are strong animals and Roars to meet later.
PLAYER_DECK = ["lion", "cape_buffalo", "dire_wolf", "cape_buffalo", "dire_wolf", "pup", "squirrel", "lion", "cape_buffalo",
               "lion", "dire_wolf", "squirrel", "cape_buffalo", "lion", "dire_wolf", "dire_wolf", "cape_buffalo", "lion",
               "cape_buffalo", "lion"]   # after the Squirrel only plain animals and Squirrels: no target Roar, no glow in lesson 1
PLAYER_DECK += PLAYER_DECK[7:] + PLAYER_DECK[7:10]   # 36 cards: a slow first game never runs out (no exhaustion loss)
# The opponent: wild dogs (1) that any animal can cover. None of them walls its den: the march must reach it before
# the player's food reaches 100 (a 7 in front of the den forced a detour, and food won first).
OPPONENT_DECK = ["rusty", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup",
                 "poppy", "rusty", "pup", "poppy", "rusty", "pup", "poppy", "rusty", "pup"]
# Lesson 2. The player opens with Lion, Lynx (it glows once the Lion stands) and a Buffalo; the Lynx's Roar draws the
# Eagle (Flight, on your own animal first); the next draw brings the Squirrel (food from a Roar) and the Black Mamba
# (removes up to 5: the opponent's Eagle), the one after the Polar Bear (8, Apex Predator: it eats a 7 of the wall, and
# the den falls); then animals.
PLAYER_DECK_2 = ["lynx", "eagle", "squirrel", "black_mamba", "polar_bear", "dire_wolf", "lion",
                 "squirrel", "cape_buffalo", "dire_wolf", "lion", "chipmunk", "cape_buffalo", "dire_wolf", "lion",
                 "squirrel", "cape_buffalo", "dire_wolf", "lion", "chipmunk", "cape_buffalo", "dire_wolf", "lion",
                 "squirrel", "cape_buffalo", "dire_wolf", "lion", "cape_buffalo", "dire_wolf", "lion", "squirrel",
                 "cape_buffalo", "dire_wolf", "lion"]
# Its opponent walls all three crossroads before its den with 7s (a 7 can't cover a 7: only the Polar Bear gets in), flies its Eagle
# onto the Squirrel (stacks), then plays wild dogs.
OPPONENT_DECK_2 = ["eagle"] + OPPONENT_DECK[1:]

DECKS = {"tutorial_you": PLAYER_DECK, "tutorial_them": OPPONENT_DECK, "tutorial2_you": PLAYER_DECK_2, "tutorial2_them": OPPONENT_DECK_2}
NAMES = {"tutorial_you": "Tutorial", "tutorial_them": "Wild dogs", "tutorial2_you": "Tutorial", "tutorial2_them": "Wild dogs"}
BOTS = {1: "tutorial", 2: "tutorial2"}
# Placements a turn, by the opponent's turn (its first two, then every later one): lesson 1's uses both moves while the
# two-moves rule is new, then one dog on the player's way and a draw: the march covers it (covering drilled, not slowed); lesson 2's keeps to one, so no extra dog takes the
# crossroad the Black Mamba needs beside the Eagle.
PER_TURN = {1: (2, 2, 1), 2: (1, 1, 1)}   # the opponent's bot name per lesson

# The opponent's scripted moves, by its turn (turn_counter): lesson 1 walls the middle of its den and puts a dog beside
# it; lesson 2 walls all three crossroads, then flies the Eagle onto the player's Squirrel (SQUIRREL: wherever it is).
SQUIRREL = "squirrel"
OPENINGS = {1: {1: [("rusty", "5,2"), ("pup", "4,2")]},
            2: {}}   # lesson 2's board is set up (set_up): the guard of 7s stands from the start
# Lesson 2's Eagle flies onto the Squirrel the first turn it can (the Squirrel on top of its stack), whenever that is.
AMBUSH = {2: ("eagle", SQUIRREL)}


# Lesson 2 starts from a set-up board (Martin, from the cold reviews: placing the Lion and Buffalo again taught nothing):
# the player's Lion and Buffalo in a chain from the den, the opponent's den guarded by three 7s.
SET_UP = {2: [("A", "lion", "1,2"), ("A", "cape_buffalo", "2,2"),
              ("B", "dire_wolf", "5,1"), ("B", "cape_buffalo", "5,2"), ("B", "lion", "5,3")]}


def set_up(state, lesson: int) -> None:
    """Put the lesson's starting animals on the board (not from any deck or hand)."""
    from ..engine.state import UnitInstance
    for owner, card, cr in SET_UP.get(lesson, []):
        state.board[cr] = [UnitInstance(card, owner, state.new_iid())]


def config(lesson: int = 1) -> Config:
    """The tutorial skips the mulligan: the deal is already the one the lessons need. Lesson 1 opens with four cards, so
    its first two turns build a whole region before any draw (one new idea a turn)."""
    return replace(Config.default(), mulligan=False, first_player_opening_draw=4 if lesson == 1 else 1)   # lesson 2: the Lynx


class TutorialBot(Bot):
    """The tutorial's opponent (seat B): the fixed opening, then one placement a turn on the leftmost empty crossroad it
    can reach (never one that would close a region for it), drawing when its hand is empty. It never covers and never
    takes the den."""

    def __init__(self, seed: Optional[int] = None, lesson: int = 1):
        self.opening, self.ambush = OPENINGS[lesson], AMBUSH.get(lesson)
        self.per_turn = PER_TURN[lesson]

    def choose(self, view, legal: Sequence, state=None):
        choices = [a for a in legal if isinstance(a, ChoiceAction)]
        if choices:
            return next((a for a in choices if a.choice == SKIP), choices[0])
        places = [a for a in legal if isinstance(a, PlaceAction) and not a.is_hq_capture]
        board = state.board
        for card, cr in self.opening.get(state.turn_counter, []) + ([self.ambush] if self.ambush else []):   # scripted moves, while they can be made
            if cr == SQUIRREL:
                cr = next((c for c, st in board.items() if st and st[-1].owner == "A" and st[-1].card_id == "squirrel"), None)
            done = cr in board and board[cr] and board[cr][-1].owner == "B" and board[cr][-1].card_id == card
            pick = None if done else next((a for a in places if a.card_id == card and a.crossroad == cr), None)
            if pick:
                return pick
        quota = self.per_turn[min(state.turn_counter // 2, 2)]
        if state.units_placed_this_turn >= quota:   # its placements done: the other move draws (two moves, like every player)
            draw = next((a for a in legal if isinstance(a, DrawAction)), None)
            if draw and state.actions_taken_this_turn:
                return draw
            return PassAction()
        if self.ambush:   # the ambush card waits for its moment, never an ordinary placement
            places = [a for a in places if a.card_id != self.ambush[0]]
        mine = lambda cr: bool(board.get(cr)) and board[cr][-1].owner == "B"
        # never the last corner of a region: the opponent takes no food, so the tutorial ends on the player's win
        closes = lambda cr: any(cr in r.corners and all(c == cr or mine(c) for c in r.corners)
                                for r in state.game_map.regions.values())
        # lesson 2: never beside the player's Squirrel, where the Black Mamba must come to its rescue
        squirrel = {cr for cr, st in board.items() if any(u.owner == "A" and u.card_id == "squirrel" for u in st)}
        beside = lambda cr: self.ambush and any(abs(int(cr[0]) - int(q[0])) + abs(int(cr[2]) - int(q[2])) == 1 for q in squirrel)
        empty = [a for a in places if not board.get(a.crossroad) and not closes(a.crossroad) and not beside(a.crossroad)]
        if empty:
            col = lambda a: int(a.crossroad.split(",")[0])
            row = lambda a: abs(int(a.crossroad.split(",")[1]) - 2)
            empty.sort(key=lambda a: (col(a), row(a), a.crossroad))
            return empty[0]
        draw = next((a for a in legal if isinstance(a, DrawAction)), None)
        return draw or PassAction()
