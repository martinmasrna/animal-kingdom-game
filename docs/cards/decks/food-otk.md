# Deck: FOOD OTK

**Pure food-combo deck** (overhauled 2026-07-05). Win condition: cross `win_food` (100) in a
burst. The old deck was three half-decks in one (a food-OTK core, a wall package, and a
sacrifice package) and finished last at ~33–37%; the overhaul cut the wall/sacrifice packages
(shelved in [`../shelved-cards.md`](../shelved-cards.md), earmarked for a future Aristocrats-Spider
deck) and rebuilt around a single, coherent combo. 4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).

## The plan
Dig → go wide with cheap Rodents in one turn (Chinchilla's extra action + Greywhisker's replay)
→ **Rat King** converts the wide board to a food burst, each enabler stacks, and **Scrooge**
doubles the turn's haul. The **defensive package** (Porcupine / Hedgehog / Armadillo) buys the
turns to assemble; Armadillo's aura shields the fragile payoff pieces from removal.

## Signature mechanic: **food gained this turn**
A per-turn counter (`turn_flags["food_gained_<player>"]`, reset each turn end; helper
`effects._food_gained_this_turn`). Four cards key off it — a unique, teachable identity:

- **Scrooge** — gain again whatever you gained this turn (doubles the haul).
- **Hamster / Muskrat / Groundhog** — if you gained ≥ `fed_threshold` (10) this turn: draw 2 / remove an adjacent enemy / +5 strength.

## Legendary (×1)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Fathom** | — | 4 | Battlecry: draw a legendary unit. *(tutors Rat King / Scrooge)* |
| **Greywhisker** | Rodent | 1 | Battlecry: gain 1 food. Draw 1 card. You may play 1 more unit. |
| **Scrooge, Keeper of the Stash** | Rodent | 4 | Battlecry: gain food equal to the food you gained this turn. *(reworked — was the bank-and-double-in-2-turns coin flip; lost Immovable)* |
| **Rat King** | Rodent | 5 | Battlecry: gain 4 food per other Rodent you control. Draw 1 card. |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Flying Squirrel** | Rodent | 4 | Flight. Battlecry: gain 8 food. |
| **Porcupine** | Rodent | 7 | Cannot be covered by enemy units. |
| **Chinchilla** | Rodent | 3 | Battlecry: next turn, take 1 additional action. |
| **Armadillo** | — | 5 | Immovable. Adjacent friendly units can't be chosen by enemy abilities. *(grants Stealth as an aura)* |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Squirrel** | Rodent | 3 | Battlecry: gain 12 food. |
| **Chipmunk** | Rodent | 1 | Battlecry: gain 10 food. At the start of next turn, gain 10 more. |
| **Hedgehog** | — | 3 | Immovable. Battlecry: gain 5 food. |
| **Hamster** | Rodent | 3 | Battlecry: if you gained 10+ food this turn, draw 2 cards. |
| **Muskrat** | Rodent | 3 | Battlecry: if you gained 10+ food this turn, remove an adjacent enemy unit. |
| **Groundhog** | Rodent | 2 | Battlecry: if you gained 10+ food this turn, gain +5 strength. |

## New mechanics / systems this deck introduces
- **Food gained this turn** — the signature counter above (`fed_threshold`, `scrooge_gain_multiplier`).
- **Bonus actions next turn** (Chinchilla) — `grant_action` op scheduled to the owner's next turn, read off `turn_flags["bonus_actions_<player>"]` by `rules._resolve_and_maybe_end_turn` (`chinchilla_bonus_actions`).
- **Stealth as an aura** (Armadillo) — `statics.can_be_chosen` now also shelters a unit adjacent to a friendly Armadillo, not just cards with the Stealth keyword.
- **Per-Rodent food payoff** (Rat King) — `rat_king_per_rodent`; go-wide reward (cf. Queen Marabunta for Colony).

## Open tuning items (all magnitudes are config dials)
- **Validated on TurnBot** (2026-07-05, 30 games/opp vs a TurnBot-piloted field, map_b): **45.2%**
  under competent play, vs 18.6% when piloted by greedy — a **+26.7pt [+19.5,+33.8]** pilot delta
  that confirms the combo is real and rewards sequencing (GreedyBot can't execute it; its
  round-robin floor was 41.5%, was 36.9% pre-overhaul). From dead-last outlier to in the pack;
  a light dial nudge could reach ~50% but confirm at higher game counts first.
- Dials: `rat_king_per_rodent=4`, `fed_threshold=10`, `hedgehog_food=5`, `groundhog_strength=5`, `hamster_draw=2`, `chinchilla_bonus_actions=1`, `scrooge_gain_multiplier=1`.
- **Chinchilla stacking** — two in a turn → +2 actions next turn; watch for degenerate chains (no cap today).
- **Survival floor** — three sticky bodies (Porcupine uncoverable, Hedgehog + Armadillo Immovable); confirm the deck actually lives to its combo turn.
