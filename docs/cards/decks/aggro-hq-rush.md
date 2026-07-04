# Deck: AGGRO HQ RUSH

Cheap chained bodies + reach/flyers to threaten and capture the enemy HQ; removal to punch
through defenders. 4-4-6 shape (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28). **Complete (2026-06-28).**
**card-balance-todo applied 2026-07-04:** Stoop moved to Egg Control (rare, see `egg-control.md`);
Gale is its legendary replacement. Hornet redesigned (spare-copy sac, gained Flight). Skunk 2→4
str. See `../../balance/card-balance-todo.md`.

## Legendary (×1) — names **PROVISIONAL** (assigned 2026-06-30; final flavor pass pending — alternates in `flavor-review.md` §3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Verminus, the Rat King** | Rodent | 3 | Has +1 strength for each other unit you control. *(swarm → wall-breaker finisher; art: a writhing mass of rats)* |
| **Pestis** | Rodent | 3 | Battlecry: remove everything from an adjacent crossroad. *(art: a plague rat; whole-tile wipe)* |
| **Sirocco** | — | 5 | Battlecry: return all enemy units adjacent to this to their owner's hand. *(mass-bounce disruptor — opens the HQ front; art: a great musk-beast / legendary skunk)* |
| **Gale** | Bird | 4 | Flight. The first time an enemy unit covers this, return that enemy unit to its owner's hand. *(card-balance-todo, 2026-07-04: replaces Stoop, which moved to Egg Control as a rare; name provisional)* |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Jerboa** | Rodent | 2 | Battlecry: play another unit. |
| **Hornet** | — | 2 | Flight. Battlecry: you may remove another Hornet from your hand or deck. If you do, destroy an adjacent enemy unit. *(card-balance-todo, 2026-07-04: was a self-sac; now saccs a spare copy so Hornet survives, and gained Flight)* |
| **Chameleon** | Lizard | ±∞ | May be placed on any unit, and any unit may be placed on top of it. |
| **Skunk** | — | 4 | Return an adjacent enemy to your opponent's hand. They can't play it next turn. *(card-balance-todo, 2026-07-04: strength 2→4)* |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Lemming** | Rodent | 1 | Battlecry: place all Lemmings from your hand and deck on random adjacent **empty** crossroads. |
| **Cheetah** | Cat | 5 | Battlecry: if you play this next to the opponent's base, draw 1 card. |
| **Rat** | Rodent | 2 | Battlecry: remove a card in your hand to destroy an adjacent enemy unit. |
| **Falcon** | Bird | 4 | Flight. Battlecry: if you play this next to the opponent's base, draw 1 card. |
| **Bat** | — | 2 | Flight. Battlecry: draw 1 card. |
| **Mouse** | Rodent | 1 | Battlecry: draw a Rodent. |

---

## Open items — RESOLVED (2026-06-28)
- **Legendary 1:** Rat King (Rodent 3, has +1 str per other unit) — the swarm finisher that out-muscles the fat HQ wall.
- **Legendary 3:** "Choking Cloud" mass-bounce (— 5, return all adjacent enemies to hand) — disruption that opens the HQ front without an instant win (bounce, they replay). Flavoured as a legendary skunk; pairs with the common Skunk (single-target bounce).
- **Legendary 4:** "Great Raptor" (Bird 6, Flight + remove adjacent ≤6) — reach beachhead + capped snipe; capture still needs a normal connected placement.
- **Rare 6:** "Hornet" (— 2, self-sac to destroy any adjacent enemy) — expendable uncapped removal to clear a big defender.
- **Tags:** Skunk → —, Bat → — (tagless off-tribe utility).
- **Two earlier proposals rejected as broken:** a "play up to two more units" burst (→ uninteractable OTKs) and a Flight + connection-ignore-grant flyer (→ 2-card instant HQ win). Replaced per above. **Design guards confirmed:** no burst extra-placements; no effect that grants a connection-ignoring placement reachable to the HQ (Flight alone never captures — see Ramp flag).
- Plague Rat wording updated to "remove everything from an adjacent crossroad" (per README decision F3 / occupant vocabulary).

## New mechanics / systems this deck introduces
- **⚠ HQ-adjacency condition — "next to the opponent's base".** Cheetah and Falcon draw when placed adjacent to the enemy HQ. Engine needs an "is this crossroad adjacent to enemy HQ" helper (HQ front-crossroads). Thematically the payoff for the rush plan.
- **Remove an entire stack** (Plague Rat): "remove ALL units from an adjacent crossroad" — clears a whole crossroad (every unit in the stack), distinct from top-unit removal. New `remove_all_at_crossroad` op. Is it friendly-and-enemy, or enemy-only? ("ALL units" reads as everything — flag.)
- **Bounce enemy to hand + temporary lock** (Skunk): return an enemy unit to the opponent's hand, and that card "can't be played next turn." Two new things: (a) bounce an enemy unit to enemy hand; (b) a per-card "locked until turn N" status. New.
- **Discard-from-hand as a cost** (Rat): "remove a card in your hand to destroy an adjacent enemy unit" — pay a hand card → kill adjacent enemy (no strength cap stated). New cost type.
- **Random placement** (Lemming): "place all Lemmings from your hand on random adjacent crossroads" — multi-place using seeded RNG and adjacency (adjacent to what — the placed Lemming? flag).
- **Generic extra placement** (Jerboa "play another unit", and the swarm chains). Mouse "draw a Rodent" = tag-filtered draw (consistent with Egg/Food/Ramp filtered draws/tutors).
- **New tag:** `Lizard` (Chameleon).

## Flags (resolve in the all-at-once review)
- **Finish 4 open cards** (3 legendaries + 1 rare) and **assign Skunk/Bat tags**.
- **HQ-adjacency helper** — define "next to the opponent's base" precisely (adjacent by a single edge to any enemy HQ front crossroad? or adjacent to the HQ node itself?).
- **Plague Rat scope** — "ALL units" = both players' units at that crossroad, or enemy-only? Big difference (could nuke your own stack).
- **Rat removal** — destroy adjacent enemy of *any* strength for the price of a card? Confirm no strength cap (strong for a common at HQ-rush; intended?).
- **Skunk lock semantics** — "can't play it next turn" tracks a status on a specific card in the opponent's hand; define how it survives shuffles/redraws and exactly which turn it unlocks.
- **Lemming random placement** — adjacency anchor (to the triggering Lemming?) and behavior when no legal adjacent crossroad exists; RNG must be seeded/deterministic.
- **Chameleon ±∞** — same special unit as elsewhere; share its existing engine handling.
- **Within-deck naming:** Rat (common) vs Plague Rat (legendary); Mouse/Jerboa/Lemming rodents — distinct, fine.
