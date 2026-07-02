# Deck: FOOD OTK

Sacrifice-for-value combo: feed Deathrattle fodder into sac outlets, burst food, double it,
cross `win_food` in one big turn. 4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28). **Has one open `?` common.**

## Legendary (×1) — names **PROVISIONAL** (assigned 2026-06-30; final flavor pass pending — alternates in `flavor-review.md` §3)
| Name | Tag | Str | Effect | Description |
|---|---|---:|---|---|
| **Fathom** | — | 4 | Battlecry: draw a legendary unit. | Octopus, looking like a kraken. |
| **Greywhisker** | Rodent | 1 | Battlecry: gain 1 food. Draw 1 card. You may play 1 more unit. | Old, wise little mouse. |
| **Carmilla, the Devourer** | Arachnid | 5 | Battlecry: remove up to 3 friendly units. Draw a card for each. | Evil-looking black widow (female name). |
| **Scrooge, Keeper of the Stash** | Rodent | 4 | Immovable. Battlecry: store all your food. In 2 turns, recover twice as much. | Squirrel with a giant hoard of nuts behind him. |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Flying Squirrel** | Rodent | 4 | Flight. Battlecry: gain 8 food. |
| **Porcupine** | Rodent | 5 | Cannot be covered by enemy units. |
| **Opossum** | — | 2 | Battlecry: draw 1 card. Deathrattle: return this to your hand. |
| **Giant Tortoise** | — | 5 | Immovable. |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Squirrel** | Rodent | 3 | Battlecry: gain 12 food. |
| **Chipmunk** | Rodent | 1 | Battlecry: gain 10 food. At the start of next turn, gain 10 more. |
| **Pufferfish** | Fish | 2 | When an enemy unit is placed on top of this, remove that enemy unit and this unit. *(ON_COVERED trap — the deck's only interaction/defense)* |
| **Black Widow** | Arachnid | 3 | Battlecry: remove an adjacent friendly unit to draw 1. |
| **Impala** | — | 2 | When this is removed, draw 2. |
| **Gazelle** | — | 2 | When this is removed, gain 40 food. |

---

## Open items — RESOLVED (2026-06-28)
- **Slot 11 filled:** Pufferfish (Fish 2, ON_COVERED trap) — gives the deck its only enemy interaction + a defensive trap to survive to the combo turn (the deck otherwise has zero ways to touch the opponent's board). New `Fish` tag in this deck.

## New mechanics / systems this deck introduces
- **`Deathrattle` keyword now in active use** (resolves a `docs/STATUS.md` naming TODO). Opossum prints "Deathrattle: …"; Impala/Gazelle write it out as "When this is removed, …". **Inconsistent wording for the same trigger — standardize** (pick "Deathrattle:" or "When removed", apply uniformly across the pool; Phoenix in Egg Control also uses "When this is removed").
- **⚠ Friendly-unit removal / sacrifice as a resource.** New targeting direction: effects remove *your own* units as a cost/effect — the Devourer (remove up to 3 friendly, draw each), Black Widow (remove adjacent friendly → draw). Engine needs friendly-target removal **and** must fire Deathrattles on sacrifice (Gazelle/Impala/Opossum payoffs). This is the deck's core loop.
- **Rarity-filtered tutor/draw:** kraken "draw a legendary unit" — reads card rarity to filter the draw. New (cf. tag-filtered draws in Egg/Ramp, strength-filtered in Ramp).
- **Store-and-double food** (Keeper of the Stash): "store all your food; in 2 turns, recover twice as much" — Immovable so it resolves. Same shape as the classic hoard-doubler; food sits at 0 during the 2-turn window.
- **Big Deathrattle payoffs as sac fodder:** Gazelle (remove → +20 food), Impala (remove → draw 2), Opossum (remove → return to hand, recyclable). Devourer + 3 Gazelles = +60 food + draw 3 in one Battlecry; Keeper then doubles the hoard. That's the OTK.
- **Split delayed food:** Chipmunk "gain 5 now, +5 at start of next turn."
- **New tag:** `Arachnid`.

## Flags (resolve in the all-at-once review)
- **Standardize the Deathrattle wording** (above).
- **Sacrifice engine semantics:** does removing a friendly unit count as "removed" for all Deathrattle/`ON_REMOVE` triggers? (Assume yes.) Do Immovable units (Keeper, Giant Tortoise) resist *friendly* sacrifice, or only *enemy* removal? Immovable text says "cannot be removed by special effects" — would block your own Devourer from sacrificing them. Likely intended (you wouldn't sac your Immovable anchors), but flag.
- **"Remove up to 3" / "you may play 1 more" — optional counts:** confirm "up to"/"may" = controller chooses 0..N; bots pick per policy.
- **Legendary names — provisional set assigned 2026-06-30** (Fathom / Greywhisker / Carmilla, the Devourer / Scrooge, Keeper of the Stash; alternates in `flavor-review.md` §3, flavor-lock pending). The black-widow legendary **Carmilla** is a different card from the common **Black Widow** (legendary = named individual). *(No collision — README decision A.)*
- **Gazelle 20-food + mass sac = OTK swing** — central tuning dial; sim should check OTK consistency vs the 100 threshold and the 2-turn double window.
- **Keeper "store all food":** with food = 0 during the window the player can't win-by-food or pay food costs; confirm interaction is identical to other store/double effects. (×1 legendary, so no multi-copy stacking.)
- **Legendary names** — provisional (assigned 2026-06-30); see the legendary table + the `docs/STATUS.md` flavor-lock item.
