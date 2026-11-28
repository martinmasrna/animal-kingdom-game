# 10 Engine War: alive

| Gate | Result | Line |
|---|---|---|
| Expert vs Random | 96.8% | ≥ 70% |
| Expert vs Greedy | 74.3% | ≥ 70% |
| Expert vs Racer | 77.2% | ≥ 70% |
| First player, Expert vs Expert | 37.8% | 30–70% |
| Games at the turn cap | 4 of 2,000 (0.2%), all Expert vs Racer | ≤ 2% |
| Expert's turn the same as Greedy's | 55.6% of 4,430 turns (58.0% of single actions) | ≤ 90% |
| Set positions | Expert passes all 3 (shoot the Post that would win, 6 damage kills one Health-5 Post, buy with 8 coin) | all |

400 games per pairing, seats alternated on the same deals (`report.json` has every number). Expert: flat Monte Carlo with UCB1 over the distinct actions, 600 full-game play-outs per action with Greedy on both sides; each play-out deals again the opponent's hand and deck, its own deck, the market deck and the future reshuffles. Games last about 15 turns each.

## The loop

Your hand plays itself, so the turn is two choices: what to buy from the row, and which enemy Posts to shoot. Expert builds an economy of Posts (37 Posts and Small Posts bought in 8 watched games against Greedy's 25) and buys few guns, shooting only Posts that matter (8 shots to Greedy's 27); it also declines to buy now and then to keep its deck thin. The best play boils down to a race of Post yield, with damage bought only to deny the Post that would decide it. That is the weak spot: the margins over Greedy (74%) and the pure Post racer (77%) are the thinnest of this batch, so racing is close to the right plan and shooting is the minority decision.

## Notes

- The second player (a 5-card first hand against 3) wins 62% of Expert mirrors.
- The market only advances when someone buys, and the Racer never buys Shots, Draw, Wall Posts or Trash; the 4 capped games (all against the Racer) were not inspected, but a row of cards neither side wants is the likely cause.
- Trash: the whole hand plays at once here, so Trash resolves first and removes another card from your hand (forgoing its effect) or your discard pile. Buying and shooting can be done in any order (neither affects the other).
