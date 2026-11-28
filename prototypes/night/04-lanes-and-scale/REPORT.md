# 04 Lanes and scale: alive

Passes every machine gate (`node sim.mjs 400`, `report.json`); the set positions pass (`node sanity.mjs`); the page plays (`node check.mjs`: whole games clicked through in headless Chrome at 1512×800 and phone width, no script errors).

## Numbers

- Expert vs Random: **97.3%** of 400 (seats alternated, same deals)
- Expert vs Greedy: **73.8%** of 400
- Expert vs Racer: **89.2%** of 400
- First player's win rate, Expert vs Expert: **44.5%** of 400; Greedy vs Greedy: 65.9% of 2000
- Games hitting the turn cap: **0%**
- Expert's choice equal to Greedy's: **54.1%** of its decisions with more than one option
- Length: 9.2 turns in all (Expert vs Expert), about 4 or 5 each

Expert is single-observer ISMCTS (1500 iterations a move; each iteration deals the hidden cards anew from what its seat has seen, plays out 4 turns with a heuristic policy, scores the end by scale, open-lane attack and board). Plays within a turn are searched in one canonical order (combat comes only at the end, so the order changes nothing but legality). More search did not buy strength: against Greedy, 1500 iterations won 74% and 4000 won 75% (100 games each), so the 74% looks like the game's ceiling against a decent fixed rule, not the bot's. It is above the 70% line, but not by much.

## The loop

Each turn is a placement puzzle: a unit facing an empty slot tips the scale by its attack at the end of your turn, the turn it is played; a unit facing an enemy unit damages it and takes nothing back. So every card is a choice between running free (scale now), standing opposite their best attacker (it then hits your unit instead of the scale, and yours hits it back next combat) or killing outright. Expert blocks early, kills what it can kill for free, and saves Shift for the turn a lane opens, when moving a blocked unit into it is worth its whole attack on the scale. Games are short (five on the scale ends it), so tempo dominates: Greedy mirrors favour the first player 66%, but played well the second player's extra card and Coin even it out (44.5%).

## Notes

- Set positions (Expert, every seed): lethal (Raider into the one open lane at scale 3), free kill (Heavy opposite a Lancer it destroys this combat), never Shift a unit that is hitting the scale onto a Wall.
- Hit 2 may target any unit, as the spec says; the bots aim it only at enemy units.
