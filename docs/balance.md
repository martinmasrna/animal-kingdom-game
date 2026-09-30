# Balance

How the game gets measured, and what is known on the current ruleset (draw 2 per Draw action, timed effects that run only on top of the stack, no Landmarks). Results from before 2026-09-25 are void.

## Targets

- Every deck's win rate against the field within **40–60%**.
- Every card priced by its **paired value** (below), within its rarity. The older per-card *impact* (win rate when drawn minus the deck's win rate) is retired: it records which games a card showed up in, not what it did, and it has ranked a vanilla 6 above a vanilla 8.
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
- **Paired swaps** price a card: the deck's win rate minus the same deck with that card's copies replaced in place by vanilla 7s (Cape Buffalo), on the same seeds, both seats. Games only differ once a swapped card matters (5–15% of them), so about 6,000 GreedyBot games give ±1 point in about a minute. A card priced in its home deck and again in goodstuff gives its **synergy**: home value minus pile value. The scripts are in the untracked `results/card-value-2026-09-26/`; promote them to `sim/` once the method has settled.
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
3. Strength is not flat. Paired swaps on GreedyBot (Cats, its three Lions replaced by vanilla bodies, 6,000 games each) give 5: 62.3%, 6: 64.3%, 7: 65.3%, 8: 66.3%, 9: 68.2%, monotonic, about 1–2 points per strength step, with the smallest steps around 7. The earlier "5 to 8 perform about the same" came from the impact metric and is void.
4. Beating the baseline doesn't make two decks balanced against each other; the 7×7 check is still needed.

Status: the roster is built and was tuned once, but its run was killed when two of its own cards (Black Bear, Grizzly Bear) turned out to cheat under the old timer bug. Next is the full fresh run: `.venv/bin/python -m animal_kingdom.sim.benchmark_set --pilot referee --games 500`, both seats, all 7 decks.

## Current data (2026-09-29, current ruleset and pool)

**Round robin, RefereeBot vs RefereeBot, 7 premades plus the goodstuff pile, 200 games per matchup, both seats, base seed 12,000,000** (`results/queue-2026-09-29/`, untracked: `2-summary.txt` has the full matchup matrix and per-card table, `logs/` every game). Premade win rates are against the six other premades only (1,200 games, ±2.8 points):

| Deck | Win rate vs premades |
|---|---:|
| cats_midrange | 69.1% |
| aggro_hq_rush | 67.8% |
| canine_buff_tempo | 62.2% |
| colony_food_swarm | 50.2% |
| ramp | 49.0% |
| food_otk | 34.5% |
| egg_control | 17.2% |

- First player wins 57.7%. Games end 57% on food, 43% on den capture, in about 12 rounds.
- The field is three strong tempo decks, two even ones, and two losers. Food OTK sits below target; Egg Control is far below it.
- Every card's impact is inside ±10. The largest are Ramp's Borealis (+7.7) and Brutus (+5.6), Food's Greywhisker (+5.3) and Barley (+5.1), Canine's Scarlett (+5.1).

**Baseline ruler, RefereeBot, 600 games per deck (2026-09-26, before the Egg, Colony, Ramp and Food passes):** the fixed synergy-free pile beats aggro 66.7%, canine 58.2%, colony 54.8%, egg 96.0% and food 65.2%, is even with ramp (49.3%), and loses only to cats (47.0%).

**Goodstuff still dominates.** A greedy hill-climb over the current pool built a pile that beats all seven premades (90% mean on GreedyBot), and RefereeBot confirms it: **73.7% mean, worst matchup 57.5% (vs aggro)**, 81% vs cats, 92% vs egg (2026-09-29). The recipe: legendaries Scarlett, Brutus, Gale, Pestis; rares Chinchilla, Polar Bear, Rhinoceros, Taipan; commons Wolf, Elephant, Lemming, Lion, Mouse, Tiger. The structural problem in [`design/goodstuff.md`](design/goodstuff.md) holds.

**Martin against the pile (reverse gauntlet, 2026-09-29).** Martin played each premade 10 times (5 first, 5 second) against the same pile piloted by RefereeBot, in the web client (`results/human_games/web/web_20260929T103600_SJWERG.jsonl`). He went **35–35**, where RefereeBot piloting the premades gets 26%. Per deck, Martin vs the bots' rate against the pile: Ramp 8–2 (38%), Aggro 5–5 (42.5%), Cats 5–5 (19%), Colony 5–5 (33.5%), Egg 5–5 (8%), Canine 4–6 (23.5%), Food 3–7 (19.5%). Ten games per deck is ±30 points, so only Egg, Ramp and Cats are clear of the bot rate on their own; the overall 50% against 26% is not noise (p < 0.0001). The bots underplay the premades far more than the pile, so part of the goodstuff gap is a pilot artifact. How much is still open: Martin knows the pile's list and the bot's habits, and one player's 70 games isn't a field.

## Leads to re-check

- **Food's walls (2026-09-29):** Fathom 4→7, Armadillo 5→7, Hedgehog 5→6 gaining 6 food took Food from 26.5% to **39.3%** against the five non-Egg premades (RefereeBot, the overnight seeds and seats, 1,000 paired games, +12.8 ±2.7). Every matchup improved: Cats +19.5, Canine +15.5, Ramp +12.5, Aggro +12.0, Colony +4.5. Den-capture losses fell from 39% to 30% of games; going first it now wins 52%, second 26%. Output in `results/food-walls-2026-09-29/`.
- **Food OTK dies ahead on food (2026-09-29).** Against the five non-Egg premades it wins 26% (RefereeBot, 1,000 games), 37% going first and 16% second. It loses about as often to den capture (39% of games) as to the opponent's food (34%), and when its den falls it is usually ahead on food (median 55 to 30). The burst turn the deck is named for rarely happens: its food wins end on a median +25 turn from 80, and only 6% of them come from a turn of 50 or more; it gains a steady 10 to 20 a turn instead. Martin's 10 games agree: 3–7 against the goodstuff pile, six of the seven losses by den capture, four of them at 87 to 96 food. Its Rodents are 1 to 4 strength and get covered on 25–46% of placements; only Porcupine (2%) holds. The replay scripts are in the session scratchpad; the logs are in `results/queue-2026-09-29/logs/`.
- **Methuselah** had the loudest single-card impact (+12.5 points) before its food was cut to 5.
- **Decision H**, re-deriving every food number on one shared scale against the 100-food win and 10/20 regions, is still open.
