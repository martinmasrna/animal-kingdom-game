# 06 Breaking Sites: alive

| Gate | Result | Line |
|---|---|---|
| Expert vs Random | 98.0% | ≥ 70% |
| Expert vs Greedy | 95.5% | ≥ 70% |
| Expert vs Racer | 99.8% | ≥ 70% |
| First player, Expert vs Expert | 43.9% | 30–70% |
| Games at the turn cap | 0 of 2,000 | ≤ 2% |
| Expert's turn the same as Greedy's | 29.3% of 3,488 turns (42.6% of single actions) | ≤ 90% |
| Set positions | Expert passes all 4 (a Pawn breaks the site and wins, never break a site that hands him the game, never break a site for him mid-game, Strike his only unit on my site) | all |

400 games per pairing, seats alternated on the same deals (`report.json` has every number). Expert: flat Monte Carlo with UCB1 over the distinct actions, 1,000 full-game play-outs per action with Greedy on both sides; each play-out deals again his hand and deck, its own deck and the site deck. A loss later and a win sooner count slightly more, and a card that hands him the game at once is never played while anything else is legal (without that, a position lost anyway made every option score 0 and it chose at random). Games last about 9 turns each.

## The loop

Each turn: which site to add power to, how much, and whether to play at all. The power you add to a site near its threshold is a gift to whoever breaks it, so Expert waits: it held unspent mana in 13 of 48 watched turns, let Greedy pile power onto a site, then struck one of its units and dropped a big unit to break the site with the lead (it caused 19 breaks to Greedy's 9 in 6 games). The best play boils down to a last-mover fight at each threshold: build a lead where the other side cannot cheaply top it, and be the one holding the big card when the site is one push from breaking.

## Notes

- Only one site can reach its threshold from a single card, so the spec's "the mover orders simultaneous breaks" never comes up.
- The spec's "don't break a site you are losing" is only a clear error when the break hands him points he could not take himself soon; the gated positions are the two cases where it is.
