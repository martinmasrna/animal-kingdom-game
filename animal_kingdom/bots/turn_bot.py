"""TurnBot: the scalable complete-own-turn planner - the default large-sim pilot.

Where GreedyBot scores one action at a time (and so cannot reliably plan draw -> play,
ordered Battlecries, or effect-granted extra placements under the two-action rules), and
RefereeBot pays for a full sampled opponent reply on every decision (~100-200x greedy),
TurnBot sits in between: it searches every candidate action until the *current turn is
completely finished* - all configured top-level actions, a Draw followed by a placement
using the newly observed card, pending choices, mandatory/optional effect-granted
placements, chains like Nurse Bumblebee -> Queen Bee -> Worker, and the end-of-turn
triggers `rules.apply_action` resolves when the turn advances - then stops the moment
control passes to the opponent and scores the finished own-turn position. It never
simulates the opponent's turn, which is what keeps it cheap enough for large balance sims.

All of that - determinized worlds so unknown draws don't leak, information-set grouping so
indistinguishable worlds pick the same action, beam pruning, the hard next-turn-HQ-loss
filter, wasted-battlecry penalties, and the projected end-of-turn readiness eval - lives in
the shared `TurnSearcher` (bots/turn_search.py). TurnBot is that searcher with the default
own-turn hooks: it scores lines by their end-of-turn planning eval, never runs a reply
rollout, and models any opponent-owned sub-choice opened during its turn adversarially
(worst legal public continuation). It is a deliberate generalist - no deck slugs or card
ids anywhere in the search - so balance conclusions are not tuned to one archetype.
"""

from __future__ import annotations

import random
from typing import Optional

from .greedy_bot import GreedyWeights
from .turn_search import TurnSearcher

# Defaults mirrored by sim.runner.TURN_DETERMINIZATIONS / TURN_BEAM_WIDTH (kept in sync
# there so the sim can name them without importing the bots package).
TURN_DETERMINIZATIONS = 3
TURN_BEAM_WIDTH = 8
# Lookahead beam width for Owl/Raven deck-reveal choices (see TurnSearcher). 0 = off. Tuned
# by the egg-vs-field width sweep (paired, 420 games/width): width 1 was 9.1x faster but cost
# ~7pt of egg strength (over-collapse); width 2 keeps ~8.2x (11.9s->1.45s/game) with the
# strength cost statistically insignificant (-1.4% [-5.0, +2.1]); width 3 reaches parity but
# at half the speedup. 2 is the elbow. Only egg has Owl/Raven, so this is a no-op elsewhere.
TURN_DECK_REVEAL_CHOICE_WIDTH = 2
# Per-root own-turn search-node budget (see TurnSearcher._complete_own_turn). None = disabled
# (exhaustive own-turn search). N = once a root candidate's expansion exceeds N branch-nodes,
# finish the remainder greedily (one line per info-set group) instead of branching. This caps the
# shallow-but-bushy breadth blow-up on the deep decks. 80 tuned via the paired benchmark: it is
# *byte-identical* in play on all 7 decks at 200 games/opp (every paired delta 0.0) while cutting
# food_otk's gauntlet cost ~20% (17.5x->13.5x vs greedy). Lower budgets buy a little more speed
# but start clipping real food_otk/aggro lines; 80 is the free elbow. Mirrored in sim.runner.
TURN_MAX_SEARCH_NODES: Optional[int] = 80


class TurnBot(TurnSearcher):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 determinizations: int = TURN_DETERMINIZATIONS,
                 beam_width: int = TURN_BEAM_WIDTH,
                 deck_reveal_choice_width: int = TURN_DECK_REVEAL_CHOICE_WIDTH,
                 max_search_nodes: Optional[int] = TURN_MAX_SEARCH_NODES):
        super().__init__(weights=weights, rng=rng, seed=seed,
                         determinizations=determinizations, beam_width=beam_width,
                         deck_reveal_choice_width=deck_reveal_choice_width,
                         max_search_nodes=max_search_nodes)

    def _begin_root_candidate(self, action) -> None:
        # Per-root budget: each root candidate gets a fresh node allowance (mirrors the oracle).
        self._search_nodes = 0

    def _complete_own_turn(self, branches, me, *, guard):
        if self.max_search_nodes is not None:
            self._search_nodes += len(branches)
            if self._search_nodes > self.max_search_nodes:
                return self._greedy_complete_turn(branches, me, guard=guard)
        return super()._complete_own_turn(branches, me, guard=guard)
