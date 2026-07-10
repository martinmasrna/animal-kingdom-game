# Card Balance — To-Do

Design decisions from the 200-game full 7×7 matchup simulation. The simulation used the
Greedy Bot, so these are directional signals rather than final human-play balance conclusions.
New-card candidates referenced here are consolidated in
[`../cards/card-candidates.md`](../cards/card-candidates.md).

## Locked changes

No locked changes waiting to be made.

## Card-pool direction

- The 14-card archetype packages are starting lists, not intended final card pools.
- Each archetype should eventually offer meaningfully more than 14 cards so players must
  make deckbuilding choices rather than include every card associated with the archetype.
- Shelved cards remain available for that expansion unless explicitly retired.
- Testing decks are not required to use the premade 4–4–6 maximum-copy shape. Test candidates
  include high-diversity lists (potentially 4 legendary, 8 rare, and 18 common singletons when
  preserving the usual rarity totals) and focused maximum-copy synergy lists.
- Card metrics from expanded lists must record copy count and exact decklist. A singleton sees
  fewer drawn games than a three-copy common, and changing the surrounding 29 cards changes the
  meaning of `WR_drawn`.
- Possible attribution method to evaluate: hold a stable archetype core and rotate a smaller set
  of experimental slots. Compare this with full 4–8–18 breadth lists before choosing a standard
  testing method.

## Quick follow-up sweep — tests, not locked changes

- [x] **DONE 2026-07-10 — Prototype Colony's five-unit gates at four units.** Isolated experiment
  changed Guard Hornet, Soldier Ant, and Nurse Bumblebee from “5 or more Colony units” to “4 or
  more” via the shared config thresholds. RefereeBot vs RefereeBot directional screen:
  `./report 50 --deck colony --bots referee,referee --seed 0 --format both --out results/colony_threshold4_referee_100`
  (6 non-mirror matchups, 100 games each, 50 each seat, 600 total). Result:
  **colony_food_swarm 53.8%**, +12.7pt vs the prior 41.1% context number. Matchups:
  aggro 44%, canine 47%, cats 51%, egg 69%, food_otk 38%, ramp 74%. This is a useful direction
  signal, not a balance-grade verdict; rerun at ≥200 games/matchup and inspect the individual
  threshold cards before locking the change.
- [ ] **Watch Methuselah rather than nerfing it again immediately.** Its +12.5-point drawn impact
  is the loudest current signal, but the recurring food amount was already reduced to 5 and needs
  clean post-change data.

## Random Martin notes

- remove "other than Dog" from dog and other cards like this? Seems too defensive for no real reason
- nerf queen Adira to 4 strength
- nerf Bullwark to 8 strength
