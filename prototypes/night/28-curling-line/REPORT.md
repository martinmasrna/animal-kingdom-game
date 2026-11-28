# 28 Curling line: alive (the hammer near the line)

Passes every machine criterion (`node sim.mjs 400 1000`, numbers in `report.json`; set positions in `node sanity.mjs`).

| Check | Result | Line |
|---|---|---|
| Expert vs Random | 99.6% (400 games) | ≥ 70% |
| Expert vs Greedy | 100% | ≥ 70% |
| First player (hammer in end 1), Expert mirror | 66.7%; 64.5% on 400 more games; 65.6% pooled over 800 (95% interval about 62–69%) | 30–70% |
| Games at the turn cap | 0% (a match is 6 or 7 ends) | ≤ 2% |
| Expert's choice equals Greedy's | 58.2% of 38,911 throws | ≤ 90% |
| Set positions (free takeout with Hit, Draw 9 rather than Any to the same cell, get closer for the match on the last throw) | all pass, Expert and Greedy | |

No Racer: there is nothing to race. Expert: determinized flat Monte Carlo over each throw (1,000 play-outs, successive halving, play-outs to the end of the match with Greedy-plus-noise), resampling the opponent's hand from the cards not in its discard; Greedy's throw stands unless another beats it by a standard error, and throws that leave the same table collapse onto the cheapest (an end's last throw had picked Any over Draw 9 to the same cell before that). The page's Expert uses 2,000 play-outs.

## The loop

- Each throw: a free Lag or Guard in front, a draw to a cell in the House, or a hit that pushes a stone out, paid from 5 energy for 4 throws an end, with a 5-card hand.
- Watching the Expert mirror (30 games, 192 ends): the free Lag is 29% of all throws; Any is played 205 times, spread over every target cell; 15% of ends are blank; the hammer scores 80% of the scoring ends (130 against 33 stolen), at about one point an end.
- The best play boils down to the hammer: the side throwing last converts the end, the other side clogs the front with free throws to deny it, and a blank keeps the hammer. The edge it gives is large (the end-1 hammer wins 65.6% between Experts) but inside the gate's band.
