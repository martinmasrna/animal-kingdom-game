# 22 Possession: alive, narrowly

| Gate | Result | Line |
|---|---|---|
| Expert vs Random | 76.1% (239 won, 131 drawn, 30 lost) | ≥ 70% |
| Expert vs Greedy | 88.5% (315, 78, 7) | ≥ 70% |
| Expert vs Racer | 95.3% (362, 38, 0) | ≥ 70% |
| Kickoff possession, Expert vs Expert (no first player here) | 60.4% | 30–70% |
| Matches at a cap | none possible (20 plays) | ≤ 2% |
| Expert's choice the same as Greedy's | 41.8% of 6,732 choices | ≤ 90% |
| Set positions | Expert passes all 3, asked 12 times each (shoot when he cannot Block, never Press a Walk-only attacker, Block on the last play when level) | all |

400 matches per pairing, seats alternated on the same deals; draws count half (`report.json` has every number). Expert, as the spec asks: for 8 deals of his hidden hand it rates every pair of options by 12 play-outs of the rest of the match (the same 12 futures for every pair), solves the game of incomplete information by regret matching and plays from the result. Two additions came out of testing. Reading: it counts what he chose before in the same situation (his role, ball in shooting range or not), from revealed plays only, and plays the best reply when that clearly beats the equilibrium mix; this beat the pure equilibrium Expert 58% head to head over 100 matches; the pure one scored about 73% against Random in 100-match runs. Options another option beats outright for no more stamina are dropped before solving.

## The loop

Every play is a blind guess priced in stamina: the attacker needs two or three won guesses to reach the last three zones, then one more (Shoot against Block) to score; the defender spends stamina to stop the likely option. Expert manages stamina across the 20 plays and reads habits: against Greedy, which always shoots in range, it always blocks. The best play boils down to reading the opponent's pattern while hiding your own, which is exactly the spec's question, and the answer is yes: reading beats every fixed mix tested here.

## The caution

Goals are rare and draws common: 1.15 goals and 47% draws per match between Experts, a third of matches drawn even against Random. A strong player cannot convert skill into wins fast enough over 20 plays; the 76% against Random is the closest call of the batch. A best reply built only to beat a uniform opponent reached 90% against Random, so the game rewards reading strongly, but a match is short and lands on 0–0 or 1–1 often. Possession at kickoff is worth 60%.
