# Deck: CANINE BUFF TEMPO

Mono-`Canine` tribal built on **persistent strength buffs** — pump the pack (in hand and on
board), snowball tempo, remove with buffed bodies. 4-4-6 shape (4 legendary ×1, 4 rare ×2,
6 common ×3 = 30).
Source: user's offline Google Sheet (uploaded 2026-06-28). **Complete (2026-06-28).**

## Legendary (×1) — names **PROVISIONAL** (assigned 2026-06-30; final flavor pass pending — alternates in `flavor-review.md` §3). The former *howl* / *hellhound* placeholders are now real named wolves (Clarion / Shuck) — resolves the `flavor-review.md` THEME must-fix.
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Lobo** | Canine | 4 | Has +2 strength for each other Canine you control. *(self-scaling alpha — the HQ-rush finisher; one body, linear scaling; art: a towering alpha wolf)* |
| **Shuck** | Canine | 6 | Battlecry: return a removed Canine to your hand. Give it +2 strength. *(a real black wolf — raise-the-fallen; evokes the black-dog legend, not a literal hellhound)* |
| **Raksha** | Canine | 5 | Your other Canines have +1 strength. *(anthem — the pack matriarch; 2026-07-05: aura +2→+1 de-swung, body 4→5 to compensate — was a +12.6% feast-or-famine outlier)* |
| **Clarion** | Canine | 4 | Battlecry: give +1 strength to all other Canines in your hand and battlefield. *(a real wolf whose Battlecry is the rallying howl)* |

## Rare (×2)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Dhole** | Canine | 3 | Battlecry: give all adjacent Canines +3 strength. *(2026-07-05: +2→+3)* |
| **Bush Dog** | Canine | 3 | Once a turn, when this gains strength, give all friendly adjacent Canines +1 strength. |
| **Jackal** | Canine | 5 | Whenever an adjacent unit is removed, gain 5 food. *(2026-07-05: body 3→5, food 3→5; note: canine has no food sink, so watch whether this actually helps)* |
| **Red Wolf** | Canine | 5 | Battlecry: give +1 strength to all Canines in your hand. |

## Common (×3)
| Name | Tag | Str | Effect |
|---|---|---:|---|
| **Gray Wolf** | Canine | 4 | Battlecry: remove an adjacent enemy with less or equal strength. |
| **Coyote** | Canine | 3 | Battlecry: if this has 5 or more strength, draw a card. |
| **Fox** | Canine | 3 | Whenever this gains strength, draw a card (once per turn). *(gas engine; 2026-07-05: body 5→3 — too strong a body for a common draw engine)* |
| **African Wild Dog** | Canine | 2 | Has +1 strength for each friendly Canine. |
| **Dingo** | Canine | 5 | At the end of your turn, give a friendly adjacent Canine +1 strength. |
| **Dog** | Canine | 1 | Battlecry: if you control another Canine, play another Canine from your hand (other than Dog). |

---

## Open items — RESOLVED (2026-06-28)
- **Legendary 1:** self-scaling alpha wolf (Canine 4, "has +2 str per other Canine") — the HQ-rush finisher; fixed an earlier broken "+1 per Canine to *each*" surge (quadratic). Now **Lobo** (provisional, 2026-06-30).
- **Rare 6:** Bush Dog (3) — reworked from "random adjacent" to **all** friendly adjacent Canines.
- **Rare 8:** Red Wolf (5) — modest hand-buff effect on a solid body.
- **Common 11:** Fox (3) — gas engine (draw when buffed).
- **Common 13:** Dingo (5) — end-of-turn neighbor buffer (body bumped to 5).
- **Dog:** Canine **1**, the "play another Canine" chain (the Canine House Cat).
- **Power-calibration note:** there is no mana — 1 card/turn — so strength *is* the body and low strength must be bought back by a strong effect (baseline = vanilla Lion 7). Bodies were set/raised accordingly.
- **Animals** (Fox / Dingo / Red Wolf / alpha-wolf) still flexible — flag any flavour that's off.

## New mechanics / systems this deck introduces (the heaviest engine impact so far)
- **⚠⚠ Persistent strength buffs ("+X strength") — a whole new subsystem.** Three distinct flavors that must be modeled separately:
  1. **Anthems (conditional, while source in play):** wolf matriarch "your other Canines have +2"; African Wild Dog "+1 per friendly Canine" (count-of-tag, dynamic). These evaporate if the source/condition changes.
  2. **Permanent counters (one-time, persist after the granter leaves):** Dhole "+3 to adjacent Canines", Howl "+1 to all other Canines", end-of-turn "+1 to adjacent Canine", hellhound's returned Canine "+2". These attach to the *unit instance* and stay.
  3. **Buffs applied to cards in hand:** Howl and the unnamed rare buff "all Canines in your **hand**". **This means hand entries need per-instance strength state** — a buff stuck on a card in hand must carry over when it's played. Today the engine likely treats hands as card ids/counts; this forces hand cards to be instances with their own modifiers.
- **`effective_strength` becomes `base/dynamic + permanent counters + active anthems`.** Touches every strength comparison (covering, removal thresholds, region holding) and now also applies to **cards in hand**, not just board units.
- **New event `ON_GAIN_STRENGTH`** (unnamed rare: "when this gains strength, …") — fires on buff application; enables buff cascades. Needs a once-per-turn guard (the card states "once a turn").
- **Removal threshold = own (buffed) strength** (Gray Wolf: "remove an adjacent enemy with less or equal strength" = ≤ this unit's current effective strength). Scales as Gray Wolf is buffed.
- **Condition on own current strength** (Coyote: "if this has 5+ strength, draw") — reads buffed effective strength at resolution.
- **Recursion + buff** (hellhound): return a removed Canine from the Remove Pile to hand, with +2 attached (a hand-buff instance, per above).
- **Food on adjacent removal** (Jackal): any adjacent unit removed → +5 food (friend or enemy — confirm).

## Flags (resolve in the all-at-once review)
- **Buff subsystem — RESOLVED.** Full spec in `keywords.md` (§ Strength modifiers) + README decision E. Convention: **"has +X" = anthem** (live, conditional — wolf matriarch, African Wild Dog), **"give +X" = permanent counter** (stored, sticks — Dhole, howl, end-of-turn, hellhound's returned Canine). Strength is live everywhere; hand cards carry counters; `ON_GAIN_STRENGTH` fires only on counter grants; slot-6 reactor once/turn + loop-guarded; African Wild Dog counts itself ("each friendly Canine").
- **Finish the 6 open cards / names / strengths** (see Open items).
- **Jackal "adjacent unit removed"** — friendly and enemy both? (reads as any.) Once per turn? (not stated.) → folds into G (once-per-turn caps).
- **Legendary names** — provisional (Lobo / Shuck / Raksha / Clarion, assigned 2026-06-30; flavor-lock pending). The *howl* / *hellhound* identities are now real named wolves (resolves the `flavor-review.md` THEME must-fix).
