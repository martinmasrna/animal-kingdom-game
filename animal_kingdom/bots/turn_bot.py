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


class TurnBot(TurnSearcher):
    def __init__(self, weights: Optional[GreedyWeights] = None,
                 rng: Optional[random.Random] = None, seed: Optional[int] = None,
                 determinizations: int = TURN_DETERMINIZATIONS,
                 beam_width: int = TURN_BEAM_WIDTH):
        super().__init__(weights=weights, rng=rng, seed=seed,
                         determinizations=determinizations, beam_width=beam_width)
