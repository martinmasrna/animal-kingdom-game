# 48 Junk war: alive

Passes every machine criterion (`node sim.mjs 400 2000`, numbers in `report.json`; set positions in `node sanity.mjs`).

| Check | Result | Line |
|---|---|---|
| Expert vs Random | 97.8% (400 games) | ≥ 70% |
| Expert vs Greedy | 85.0% | ≥ 70% |
| Expert vs Racer (never buys Foul, Foul 2, Thief) | 94.5% | ≥ 70% |
| First player, Expert mirror | 43.0% | 30–70% |
| Games at the turn cap | 0% | ≤ 2% |
| Expert's choice equals Greedy's (buys and Purge targets) | 66.7% of 27,095 decisions | ≤ 90% |
| Set positions (don't end a buy with 8 coin, Purge the two Junk, Score 4 on 22) | all pass, Expert and Greedy | |

Playing the hand is a fixed order for every bot but Random (Draw first, then Purge, then the rest): order matters only for those two cards, so it is not counted as a decision. Expert: determinized Monte Carlo over whole rest-of-turn plans (Purge targets, then any set of up to two row cards or nothing), 2,000 play-outs to the end of the game with Greedy-plus-noise, Greedy's plan kept unless another beats it by a standard error. An earlier one-action Expert let the play-out finish its turn and so bought a Clean that thinned nothing; it purged a Coin over a Junk and passed on a Score 4 at 22 points. Planning the whole turn fixed both. Among the trivial bots, Greedy (which buys attacks) beats Racer (which never does) 73%, so polluting pays.

## The loop

- Each turn the hand plays itself; the decisions are what to buy with the coin (or nothing) and what Purge removes.
- Watching the Expert mirror (30 games, all ending at 25 points, 25.6 turns in all): Purge removes Coins far more than Junk (146 against 57), Coin 2 and Score 2 are the staple buys, Foul is the third most bought card, and about 8 Junk enter decks a game. Score 4 was bought once: 8 coin in one hand almost never happens.
- The best play boils down to a thinning race: keep the deck small so the Score cards come around more often, with Foul bought nearly as often as Coin 2 to clog the other deck; a bot that never attacks loses to one that does (Greedy beats Racer 73%).
