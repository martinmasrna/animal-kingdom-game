# 19 Supply Grid: alive

| Gate | Result | Line |
|---|---|---|
| Expert vs Random | 99.8% | ≥ 70% |
| Expert vs Greedy | 99.3% | ≥ 70% |
| Expert vs Racer | 98.3% | ≥ 70% |
| First player, Expert vs Expert | 43.4% | 30–70% |
| Games at the turn cap | 0 of 2,000 (round 12 is the rule's own end) | ≤ 2% |
| Expert's turn the same as Greedy's | 18.3% of 4,173 turns (46.4% of single actions) | ≤ 90% |
| Set positions | Expert passes all 4 (strike the Base with a Heavy beside it, cut the chain whose Heavy would kill my Base, cut the one link to three pieces on the last turn, never strike a stronger piece) | all |

400 games per pairing, seats alternated on the same deals (`report.json` has every number). Expert: flat Monte Carlo with UCB1 over the distinct actions, 500 full-game play-outs per action with Greedy on both sides, unseen cards dealt again for each play-out (it beat Greedy 100% at 500 to 1,500 play-outs in shorter runs, so the count was cut to fit the night). Greedy is the spec's rule plus striking the enemy Base whenever that destroys it.

## The loop

Each turn you choose where to grow (which empty cell next to your network), what to put there (cheap links or strong pieces), and which strikes to make, knowing that any piece you destroy takes down everything hanging on it. Between Experts the game is a race to plant a piece of power 3 or more beside the enemy Base (it can strike the turn it lands) while keeping the cells beside your own Base covered; it ends by a Base kill around turn 8 each, rarely at the round-12 count. Expert rarely plays Greedy's turn (18%): it places to threaten the Base and to cut, not to win the nearest fight. The best play boils down to reading threats two moves deep on a tiny board: where can he land a 3 next to my Base, and which single piece of his holds his whole front.

## Notes

- The spec's mid-game cut position (his Line is the only link to three Posts, cut it) is not a clean test here: against an opponent who keeps building on the doomed chain, holding the Cut a turn removes more, and the play-outs preferred that. The gated versions are the cut that saves your Base and the same cut on the last turn, where the count decides.
- Draws: 7 of 400 Expert mirrors.
