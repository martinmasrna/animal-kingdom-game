# 31 Claims: alive

Passes every machine criterion (`node sim.mjs 400 3000`, numbers in `report.json`; set positions in `node sanity.mjs`).

| Check | Result | Line |
|---|---|---|
| Expert vs Random | 100% (400 games) | ≥ 70% |
| Expert vs Greedy | 80.0% | ≥ 70% |
| Expert vs Racer | 85.5% | ≥ 70% |
| First player, Expert mirror | 52.5% | 30–70% |
| Games at the turn cap | 0% | ≤ 2% |
| Expert's choice equals Greedy's | 56.6% of 31,326 decisions | ≤ 90% |
| Set positions (free challenge, lethal, no challenge on 3 life, free trade, use the mana) | all pass, Expert and Greedy | |

Expert: determinized flat Monte Carlo over each single action (3,000 play-outs, successive halving, play-outs 10 turns deep then a position score), resampling the opponent's hand, deck and face-down units from the unseen copies. It judges a claim from public counts only: the chance the claimer held a copy, against the claimer's revealed lie rate; it expects a challenge as often as the opponent has actually challenged. The first Expert (4-turn play-outs) beat Greedy only 69%; deeper play-outs and the challenge-rate model fixed that. The page's Expert uses 6,000 play-outs.

## The loop

- Each turn: which card to put down and what to call it (the truth, or a better card paid with the cheapest card in hand), whether to challenge each enemy claim, and the usual attack choices.
- Watching the Expert mirror (60 games): 37% of claims are lies, mostly a spell called a Striker or Raider; 76% of all claims get challenged, and 39% of those catch a lie. Penalties alone come to about 20 life per game, a full life bar, so the mirror ends in 8.1 turns (11.4 against Greedy, who never lies or challenges blind).
- The best play boils down to counting copies and challenging almost everything: the 3-life penalty is worth more than most cards on the list, so the unit duel shrinks to a guessing war over penalties, with units and burn finishing what the penalties started.
