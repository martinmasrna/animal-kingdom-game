# 21 Round purse: alive

Passes every machine criterion (`node sim.mjs 400 2000`, numbers in `report.json`; set positions in `node sanity.mjs`).

| Check | Result | Line |
|---|---|---|
| Expert vs Random | 99.5% (400 games) | ≥ 70% |
| Expert vs Greedy | 99.8% | ≥ 70% |
| Expert vs Spend (never passes while a card helps) | 98.4% | ≥ 70% |
| First player (round 1 starter), Expert mirror | 49.0% (10% draws) | 30–70% |
| Games at the turn cap | 0% | ≤ 2% |
| Expert's choice equals Greedy's | 32.7% of 24,885 decisions | ≤ 90% |
| Set positions (cheapest win, pass when ahead, the card that wins the match) | Expert all pass; Greedy misses the cheapest win (throws Big where Troop wins) | |

Expert: determinized flat Monte Carlo over the legal moves (2,000 play-outs, successive halving, play-outs to the end of the match), resampling the opponent's hand from the cards it has not shown. With Greedy as the play-out policy it chose Big over Troop in the cheapest-win position, because Greedy wastes the purse later anyway, so saved mana is worth nothing inside its play-outs. The play-outs therefore use Thrifty: ahead, pass; behind, the cheapest card that gets ahead; give up a round that is neither deciding nor close, dumping a Gift into it. Thrifty alone beats Greedy 80% and Spend 94%, but the Expert beats Thrifty 97% (400 games), so no fixed rule of this kind solves the game. The page's Expert uses 3,000 play-outs.

## The loop

- Each turn: play one card or pass, which really means how much of the one purse this round is worth, and whether to give the round up.
- Watching the Expert mirror (30 games, 77 rounds): it spends about half the purse in round 1 (9.5 of 18 left on average), 3.4 left after round 2; 40 of its passes come while behind, conceding the round; Gift is played almost whenever drawn (free cards for 4 power the opponent gets in a round), Big rarely (37 plays, the dearest power per mana). Matches split 14 at 2–0 and 13 at 2–1.
- The best play boils down to buying each round as cheaply as possible and refusing the rounds that would cost too much; the Expert's near-total wins over every fixed rule say the timing of that refusal, against what the opponent has shown and kept, is where the skill sits.
