# 01 Score or Fight: alive

| Gate | Result | Line |
|---|---|---|
| Expert vs Random | 100% | ≥ 70% |
| Expert vs Greedy | 93.8% | ≥ 70% |
| Expert vs Racer | 98.0% | ≥ 70% |
| First player, Expert vs Expert | 36.5% | 30–70% |
| Games at the turn cap | 0 of 2,000 | ≤ 2% |
| Expert's turn the same as Greedy's | 48.5% of 4,787 turns (55.9% of single actions) | ≤ 90% |
| Set positions | Expert passes all 4 (lethal, kill the unit that would win, no idle ready unit, Hit 2 before Hit 6) | all |

400 games per pairing, seats alternated on the same deals (`report.json` has every number). Expert: flat Monte Carlo with UCB1 over the distinct actions, 3,000 full-game play-outs per action with Greedy on both sides, the unseen cards dealt again for each play-out. Greedy is the spec's rule plus scoring out when the ready units reach 40. Games last about 15 turns each between Experts.

## The loop

Each turn you deploy, then decide unit by unit: cash this unit's health now, or spend it killing an enemy unit, which deletes that unit's health from every future turn of his. Expert falls behind early on purpose: it trades its cheap and damaged units and its Hit cards into his scorers while he banks points, keeps its own big units healthy, then cashes a full board in two or three turns (it scored 3.9 health per Score action against Greedy's 2.6). The best play boils down to board control with a timing question on top: every enemy unit left alive is a recurring score, so the real decision is the turn you stop fighting and start cashing.

## Notes

- The second player (4 cards and the Coin) wins 63.5% of Expert mirrors: inside the line, but the Coin is worth a lot here.
- The spec's "free trade" position (ready Heavy 4/5 against an enemy Raider 3/2: attack) is not a free trade in this game, because damage stays and costs the Heavy 3 of its 5 scoring health; it is kept in `sanity.mjs` ungated. Expert attacks there anyway. The gated equivalent is the denial kill: his unit would score him to 40 next turn.
- The spec's Hit cards say "any unit"; the build lets them hit enemy units only, since hitting your own never helps.
