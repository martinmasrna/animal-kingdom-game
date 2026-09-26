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
- **Paired swaps** price a card: the deck's win rate minus the same deck with that card's copies replaced in place by vanilla 7s (Cape Buffalo), on the same seeds, both seats. Games only differ once a swapped card matters (5–15% of them), so about 6,000 GreedyBot games give ±1 point in about a minute. A card priced in its home deck and again in the goodstuff pile gives its **synergy**: home value minus pile value. The scripts are in the untracked `results/card-value-2026-09-26/`; promote them to `sim/` once the method has settled.
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

## Current data (2026-09-26, current ruleset)

**Premade matrix, RefereeBot vs RefereeBot, 200 games per matchup, both seats** (`./report 100 --bots referee,referee`; output in the untracked `results/queue-2026-09-26/`):

| Deck | Win rate vs field |
|---|---:|
| cats_midrange | 64.8% |
| aggro_hq_rush | 62.7% |
| canine_buff_tempo | 61.2% |
| colony_food_swarm | 55.2% |
| ramp | 52.1% |
| food_otk | 41.4% |
| egg_control | 12.7% |

- First player wins 56.3%. Games end 57% on food, 43% on HQ capture, in about 12 rounds.
- **Egg Control** isn't a bug: since Draw draws 2, an Egg is a slower, riskier Draw. Hatching into 3 instead of 2 (TurnBot, 200 games per matchup) moved it only from 8.9% to 10.9%, so better Eggs alone don't rescue the deck.

**Baseline ruler, RefereeBot, 600 games per deck:** the fixed synergy-free pile beats aggro 66.7%, canine 58.2%, colony 54.8%, egg 96.0% and food 65.2%, is even with ramp (49.3%), and loses only to cats (47.0%).

**Goodstuff still dominates.** A greedy hill-climb built a pile that beats all seven premades (92% mean), and RefereeBot confirms it: **80% mean, worst matchup 64% (vs aggro)** (2026-09-25). The structural problem in [`design/goodstuff.md`](design/goodstuff.md) holds under the current rules. The recipe: legendaries Alpha, Gale, Rat King, Sirocco; rares Black Panther, Chinchilla, Polar Bear, Serval; commons Anaconda, Bat, Dire Wolf, Lemming, Lion, Tiger.

## Leads to re-check

- **Food OTK**'s combo is real and the bots play it well at two actions.
- **Methuselah** had the loudest single-card impact (+12.5 points) before its food was cut to 5.
- **Decision H**, re-deriving every food number on one shared scale against the 100-food win and 10/20 regions, is still open.
