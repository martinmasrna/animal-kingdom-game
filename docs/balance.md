# Balance

How the game gets measured, and what is known on the current ruleset (draw 2 per Draw action, timed effects that run only on top of the stack, no Landmarks). Results from before 2026-09-25 are void.

## Targets

- Every deck's win rate against the field within **40–60%**.
- Every card's impact within **±10%**. Impact is win rate when drawn minus the deck's overall win rate, read within a deck and within a rarity; don't compare it across decks or rarities.
- Above both: the archetype metagame in [`design/principles.md`](design/principles.md), which the goodstuff problem currently blocks ([`design/goodstuff.md`](design/goodstuff.md)).

## Method

The `balance-eval` skill (`.claude/skills/balance-eval/`) holds the full procedure. In short:

- At least 200 games per matchup, paired seeds, both seats. 40-game runs have misled this project before.
- Read deltas against their confidence interval; a delta inside it is noise.
- Triage every finding: a card signal goes to the cards, a pilot flaw to the bots. If a stronger pilot changes the result, it was the pilot.
- Pilot sensitivity is itself a result. A matchup that swings between pilots is unreliable, so report the spread rather than averaging it away.
- Balance values live in `engine/config.py` (effect magnitudes) and `cards.json` (strength, food cost), never as literals in effect code.

## Instruments

- `./report N` plays the round-robin (or `--deck X [--opponent Y]`) and prints the matchup matrix and per-card impact; `--format files --out DIR` writes CSV/JSON, `--log FILE` records every game for `sim.replay`.
- `sim/rules_ab.py` A/Bs a rules change over the full matrix with paired seeds.
- `sim/benchmark_set.py` plays the fixed baseline deck against the field, scoring both seats' cards in one pass. It checkpoints and resumes, but the resume key doesn't fingerprint card data or config values: never resume a run across a card or config change.
- The deckbuilding instruments for the goodstuff problem are listed in [`design/goodstuff.md`](design/goodstuff.md).

## The baseline deck ruler

The plan for pricing cards in absolute terms: a fixed, synergy-free 30-card reference deck (`decks.BASELINE_DECK`: 18 common, 8 rare, 4 legendary, one copy each, including calibration bodies such as vanilla 5 to 10). Because it never changes, it measures card power and drift without the coupled 7×7 matrix, and it gives every synergy deck a meaningful target: beat a pile of merely good cards.

Decided:

- Pilot everything recorded with RefereeBot; greedy is for quick probes only.
- Anchor within each rarity. A fair common matches the vanilla 7 ground body and the vanilla 5 flyer, which are asserted equal: that prices Flight at about +2 strength, and the rig checks it. Rare and legendary anchors are set by feel on the same ladder; the rarity premium exists because a deck has only 4 legendary and 8 rare slots.

Caveats that survive:

1. Pilot bias favours the baseline, since a synergy-free deck is the easiest to pilot. A scaling deck (egg, ramp) that "loses to baseline" needs human play before any redesign.
2. The anchor values set the whole game's power level. That's a design decision to own, not a measurement.
3. Strength is threshold-y (vanilla 5 to 8 perform about the same), so measure the rig's resolution floor from its off-baseline test cards before tuning anything finer.
4. Beating the baseline doesn't make two decks balanced against each other; the 7×7 check is still needed.

Status: the roster is built and was tuned once, but its run was killed when two of its own cards (Black Bear, Grizzly Bear) turned out to cheat under the old timer bug. Next is the full fresh run: `.venv/bin/python -m animal_kingdom.sim.benchmark_set --pilot referee --games 500`, both seats, all 7 decks.

## Current data (2026-09-25, current ruleset)

**Premade matrix, TurnBot vs TurnBot, 200 games per matchup** (`./report 100 --bots turn,turn`; output was in the untracked `results/queue-2026-09-25/`):

| Deck | Win rate vs field |
|---|---:|
| colony_food_swarm | 64% |
| cats_midrange | 62% |
| food_otk | 59% |
| aggro_hq_rush | 56% |
| canine_buff_tempo | 55% |
| ramp | 45% |
| egg_control | 8% |

- **egg_control at 8% is the first thing to investigate.** It was about 43% under the old ruleset with stronger pilots. Either a rule change since (draw 2, timed effects running only on top of the stack) broke its Egg engine, or it is a bug. Check by hand before any card change; the bots understate this deck, but not by 35 points.
- Excluding egg, the field spans 45 to 64%: colony and cats sit above the 60% line, ramp just above 40%.
- First player wins 56.7%; games average 10.4 turns.

**Goodstuff still dominates.** A greedy hill-climb built a pile that beats all seven premades (92% mean), and RefereeBot confirms it: **80% mean, worst matchup 64% (vs aggro)**. The structural problem in [`design/goodstuff.md`](design/goodstuff.md) holds under the current rules. The recipe: legendaries Alpha, Gale, Rat King, Sirocco; rares Black Panther, Chinchilla, Polar Bear, Serval; commons Anaconda, Bat, Dire Wolf, Lemming, Lion, Tiger.

## Leads to re-check

- **Food OTK**'s combo is real and the bots play it well at two actions.
- **Methuselah** had the loudest single-card impact (+12.5 points) before its food was cut to 5.
- **Decision H**, re-deriving every food number on one shared scale against the 100-food win and 10/20 regions, is still open.
