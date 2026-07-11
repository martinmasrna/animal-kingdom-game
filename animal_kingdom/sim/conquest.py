"""Conquest series solver: does a 3-deck roster win, under optimal blind deck selection?

Given the deck-vs-deck win-rate matrix between two rosters, this computes each roster's
probability of winning a *series* under two formats:

  * conquest  - first to 2 game wins; a deck that WINS is retired (so your 2 wins must come
                from two different decks). This is the format that punishes concentration: a
                single dominant "goodstuff" deck can only ever carry one game.
  * last_hero - first to 2 wins; nothing is retired (you may replay your best deck). Included
                as the contrast that concentration is *supposed* to beat.

Deck selection each game is a blind simultaneous choice among available decks; we solve that
one-shot choice as a zero-sum matrix game (row maximizes its series-win probability), by
fictitious play - dependency-free and plenty accurate for <=3x3 games whose payoffs are
themselves noisy win-rate estimates. The series value is a memoized recursion over roster
states, each state's value being the matrix-game value of the current selection subgame.

Pure stdlib: the solver takes a plain matrix, so it's unit-testable with no simulation. The
sim that *measures* the deck-vs-deck rates and drives the roster experiment lives in
`roster_experiment.py`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Sequence

Matrix = Sequence[Sequence[float]]


def matrix_game_value(payoff: Matrix, iters: int = 20000) -> float:
    """Value of a zero-sum matrix game (row maximizes, col minimizes) via fictitious play.

    Returns the row player's guaranteed expected payoff. Both players best-respond to the
    opponent's empirical action frequencies; the running average of the two best-response
    values brackets the game value, and we return the midpoint."""
    n_rows = len(payoff)
    n_cols = len(payoff[0])
    if n_rows == 1 and n_cols == 1:
        return payoff[0][0]
    row_choice_counts = [0] * n_rows
    col_choice_counts = [0] * n_cols
    # Cumulative payoff of each row vs the col's played history, and vice versa.
    row_scores = [0.0] * n_rows   # if row played r against col's empirical mix
    col_scores = [0.0] * n_cols   # payoff col concedes if col played c against row's empirical mix
    row_value_sum = 0.0
    col_value_sum = 0.0
    # Seed with each side's first action so the empirical mixes are well-defined.
    last_col = 0
    last_row = 0
    for t in range(1, iters + 1):
        # Row best-responds to col's empirical distribution (col_choice_counts).
        for r in range(n_rows):
            row_scores[r] += payoff[r][last_col]
        best_row = max(range(n_rows), key=lambda r: row_scores[r])
        row_value_sum += row_scores[best_row] / t
        # Col best-responds to row's empirical distribution (minimizes row's payoff).
        for c in range(n_cols):
            col_scores[c] += payoff[last_row][c]
        best_col = min(range(n_cols), key=lambda c: col_scores[c])
        col_value_sum += col_scores[best_col] / t
        row_choice_counts[best_row] += 1
        col_choice_counts[best_col] += 1
        last_row, last_col = best_row, best_col
    # row_value_sum/iters is a lower bracket, col_value_sum/iters an upper bracket.
    return (row_value_sum + col_value_sum) / (2 * iters)


def _conquest_value(matrix: Matrix) -> float:
    """P(row roster wins) under conquest (a deck that wins is retired for its owner).

    matrix[i][j] = P(row deck i beats col deck j). Series = first to 2 game wins; a roster
    wins only by winning with two *different* decks. State = the still-available deck indices
    per side (a roster with 1 deck left has already won 2)."""
    n = len(matrix)

    @lru_cache(maxsize=None)
    def value(a: tuple[int, ...], b: tuple[int, ...]) -> float:
        if len(a) == 1:
            return 1.0
        if len(b) == 1:
            return 0.0
        # Selection subgame: rows = row's available decks, cols = col's available decks.
        payoff = [
            [matrix[i][j] * value(tuple(x for x in a if x != i), b)
             + (1 - matrix[i][j]) * value(a, tuple(x for x in b if x != j))
             for j in b]
            for i in a
        ]
        return matrix_game_value(payoff)

    return value(tuple(range(n)), tuple(range(n)))


def _last_hero_value(matrix: Matrix) -> float:
    """First to 2 wins, no retirement (you may replay any deck). State = (row_wins, col_wins)."""
    n = len(matrix)

    @lru_cache(maxsize=None)
    def value(row_wins: int, col_wins: int) -> float:
        if row_wins == 2:
            return 1.0
        if col_wins == 2:
            return 0.0
        payoff = [[matrix[i][j] * value(row_wins + 1, col_wins)
                   + (1 - matrix[i][j]) * value(row_wins, col_wins + 1)
                   for j in range(n)] for i in range(n)]
        return matrix_game_value(payoff)

    return value(0, 0)


def conquest_series(matrix: Matrix) -> float:
    """P(row roster wins) under conquest (winner's deck retired)."""
    return _conquest_value(matrix)


def last_hero_series(matrix: Matrix) -> float:
    """P(row roster wins) under last-hero-standing (no retirement)."""
    return _last_hero_value(matrix)
