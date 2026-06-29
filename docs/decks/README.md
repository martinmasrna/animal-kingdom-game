# Reworked Card Pool — Deck Staging Index

The reworked pool: **7 premade decks**, each 4-4-6 (4 legendary ×1, 4 rare ×2, 6 common ×3 = 30).
These decklists (uploaded from the designer's Google Sheet, 2026-06-28) are the **source of truth**.
The legacy `cards.md` §5–9 lists are dead — do not reconcile against them.

Status: **all 7 decks content-complete (2026-06-28).** Remaining before build: assign final
**legendary names** (mostly placeholder descriptions today) and the **G/H** tuning pass
(once-per-turn caps + food economy — largely a sim job). Next step is rebuilding
`data/cards.json` + the effect registry from these files.

> **Power calibration (read before designing any card):** there is **no mana** — 1 card/turn —
> so strength **is** the body, and low strength must be paid back by a strong effect. Baseline
> vanilla = **Lion (7)**. See memory `no-mana-power-calibration`.

## Roster & completeness
| # | Deck | File | Identity | Complete? |
|---|---|---|---|---|
| 1 | Cats Midrange Tempo | `midrange-cats.md` | mono-Cat tempo/removal | ✅ all 14 defined (legendary names final: Prince Leo, Princess Lea, King Theron, Queen Adira) |
| 2 | Egg Control | `egg-control.md` | Snake/Bird/Egg draw-shuffle-remove → food | ⚠ effects complete; **3/4 legendary names** are `[NAME]` |
| 3 | Colony Food Swarm | `colony-food-swarm.md` | mono-Colony swarm → food | ⚠ effects complete; **4/4 legendary names** placeholders |
| 4 | Ramp | `ramp.md` | ramp food → huge `Costs 20` bodies | ✅ all 14 defined (2 legendaries + Rhino/Hippo reworked 2026-06-28); legendary names TBD |
| 5 | Food OTK | `food-otk.md` | sacrifice + Deathrattle → food OTK | ✅ all 14 defined (Pufferfish added); legendary names TBD |
| 6 | Aggro HQ Rush | `aggro-hq-rush.md` | cheap chains + reach → capture HQ | ✅ all 14 defined (2026-06-28); legendary names TBD |
| 7 | Canine Buff Tempo | `canine-buff-tempo.md` | mono-Canine persistent strength buffs | ✅ all 14 defined (2026-06-28); animal names for Fox/Dingo/Red Wolf/alpha flexible |

## Consolidated decision agenda (for the all-at-once review)
Cross-cutting questions raised across the 7 decks, each detailed in the per-deck files:

- **A. Card identity / keying. — RESOLVED (2026-06-28).** Every card is **globally unique by name**, lives in **exactly one deck**, and is never shared or redefined across decks → `cards.json` keyed by unique id, no deck-scoping. Apparent "duplicates" are deliberately distinct animals/cards (Worker Ant / Soldier Ant, Worker Bee / Queen Bee, Black/Grizzly/Polar Bear, Leopard / Snow Leopard, …). The "Anaconda"/"Black Widow"/"kraken" notes on legendaries are **art/flavor descriptions, not names** (real legendary names TBD); legendaries are the named-individual exception, so one can share a species with a common (e.g. the giant-anaconda legendary vs the common **Anaconda**). No collision.
- **B. Tag taxonomy & sub-tags — RESOLVED (2026-06-28).**
  - **Schema:** a card record carries `type` (`"unit"` | `"landmark"`, from C) and **`tags`: a flat list** (default `[]`). Tags is a *list* — most cards have one, but meme/hybrid cards (e.g. Platypus) can carry several (`["Bird","Reptile","Mammal"]`) and then count for *every* matching tribal effect. **Roles live in the same list** (no separate `subtags` field): `Worker Ant` = `["Colony","Worker"]`, `Queen Bee` = `["Colony","Queen"]`. Effects query membership uniformly ("a Colony Queen" = tags ⊇ {Colony, Queen}; "non-Queen Colony unit" = has Colony, lacks Queen).
  - **Active species families:** `Cat, Canine, Colony, Snake, Lizard, Bird, Rodent, Arachnid, Bear, Megafauna, Egg`. (`Bear`/`Megafauna`/`Lizard`/`Arachnid` have no effect referencing them yet — kept as future-synergy hooks per §4.2.)
  - **Retired:** `Reptile` → split into `Snake`/`Lizard`; `Insect` → `Colony` (+ `Arachnid` for spiders). Re-add an umbrella only if a card needs it.
  - **Dormant/reserved** (listed in taxonomy, no current card): `Fish, Primate, Rabbit`.
  - **Roles/sub-tags:** only `Queen` and `Worker` for now (the only ones effects reference). `Soldier`/`Nurse`/`Guard`/`King` are flavor names, not tags yet — promote when something references them.
  - **Tagless** (`[]`) allowed (no tribal hook; already established in the old pool).
  - **Consequence:** multi-tag means "one species per pool" gets a deliberate meme exception, and a unit counts toward several tribes at once. Fine — intended.
- **C. Card types beyond animal units. — RESOLVED (2026-06-28), revisit later.** `cards.md` §2 relaxed to permit **non-animal cards, used sparingly** (a deliberate minority so the "Animal Kingdom" identity holds). Card model = **three flavor categories, two engine behaviors:**
  - `Unit` (animals) and `Egg` (a unit subtype — "something that becomes an animal", §2) are **units** mechanically: counted by unit-queries, hit by unit-triggers, can capture an HQ.
  - `Landmark` (Fig Tree, Watering Hole) is the **lone non-unit type**: occupies a crossroad, is Fragile, uses the delayed scheduler, participates in covering/connection — but is **invisible to "unit" card-wording and cannot capture an HQ**.
  - Engine cost is one flag (`type == Landmark`): unit-keyed event handlers/queries filter it out.
  - **Rules-doc cleanup:** "unit" in card text = `Unit`/`Egg` only; introduce an umbrella noun (**"occupant"**) for placement/covering/stack/connection rules that mean *everything* on a crossroad. Reword "all units on a crossroad" texts (e.g. **Plague Rat** → "remove everything from that crossroad").
  - **TODO — revisit:** sanity-check this once more before building `cards.json`/rules (see `todo.md`) — confirm Egg-as-unit doesn't create odd interactions and that "occupant" vocabulary reads cleanly across all card text.
- **D. Keyword registry — RESOLVED (2026-06-28).** Canonical definitions now live in **`docs/keywords.md`** (single source of truth — don't re-explain keywords in deck/card files). Summary: official keywords are **Flight, Immovable, Fragile, Apex Predator, Battlecry, Deathrattle**; `Costs X food` is a placement *cost*, not a keyword (→ F). **Apex Predator** is a keyword, **not** vanilla (Tiger/Anaconda/Polar Bear + giant legendaries) and is now fully specified (normal covering strength rules; may eat your own units; can't be placed on an HQ; destroys Eggs/Landmarks). **Battlecry/Deathrattle** stay placeholder names (rename deferred, `todo.md`); Deathrattle prints as "Deathrattle: …". Only **Lion** (Cats) is a true vanilla body.
- **E. Strength-modifier subsystem — RESOLVED (2026-06-28).** Model spec in `keywords.md` (§ Strength modifiers). One number, three layers, evaluated **live** wherever strength matters: `effective_strength = base_or_dynamic + stored_counters + active_anthems`, clamped ≥ 0.
  - **"has +X" = anthem** (live, conditional aura; vanishes with its source) — wolf matriarch, African Wild Dog, Colony's Champion / Guard Hornet. This live layer **subsumes existing dynamic strength** (giant anaconda = removed units) — one mechanism in `strength.py`.
  - **"give +X" = permanent counter** (one-time grant, stored on the instance, persists after the granter dies) — Dhole, howl, hellhound's returned Canine, the end-of-turn buffer.
  - **Always live** → resolves the open `handoff-engine §9` snapshot question (we never snapshot; strength is recomputed at check time).
  - **Hand cards carry buffs:** hand entries are instances with a `strength_counter` that travels onto the board when played. Hand buffs are **one-time** (a Canine drawn *after* the buff is not retroactively buffed).
  - **`ON_GAIN_STRENGTH`** fires only on discrete counter grants (Layer B), never on live anthem drift; the slot-6 reactor is once-per-turn + loop-guarded.
  - **Counters are signed ints** (future "−X" debuff just works; none exist yet — Skunk is a bounce).
  - Engineering: `strength_counter` on `UnitInstance` (incl. hand instances), anthem providers scanned live, a `grant_strength` op firing `ON_GAIN_STRENGTH` — localized to `strength.py` + the effect stack, no core-loop surgery.
- **F. New events/ops — RESOLVED (2026-06-28, quickfire round).**
  - **F1 — Extra placements** ("play another unit / a Cat / a Worker", Wild Dogs, etc.): a **full normal placement** (connection unless Flight, covering/strength rules, pay any cost) that simply **doesn't consume the turn action** (so they chain); **hand-only unless the card says "or deck"**; per-card constraints on *what* may be placed; "may" = optional, can fizzle.
  - **F2 — Shuffle event** = **one event per card shuffled *into* the deck** (Raven "shuffle 2 back" = 2 events; Phoenix self = 1). Incidental library reorders don't count.
  - **F3 — Plague Rat** "remove everything from an adjacent crossroad" = the **entire stack, both players' occupants** (incl. Eggs/Landmarks); removed units fire Deathrattles.
  - **F4 — Skunk bounce** = return the enemy unit to the opponent's **hand**; **NOT a removal** (no Deathrattle, no remove trigger, doesn't count as removed); any unit beneath is revealed; the returned card is **locked — unplayable through the owner's next turn.**
  - **F5 — Rat** = optional; **no strength cap** (kills any adjacent enemy for one hand card). The paid card is a **remove** (fires remove triggers) but **not** a Deathrattle. → see Remove Pile model below.
  - **F6 — HQ-adjacency** ("next to the opponent's base") = membership in the enemy HQ's front-crossroad (`connects`) list. Map A: column 4 for HQ_B.
  - **F7 — Keeper of the Stash** = snapshot food → set to 0; **+2× the snapshot two owner-turns later**; you **keep earning normally** during the window (new income isn't swallowed); can't food-win/pay costs from the banked amount until it returns; 2-turn scheduler.
  - **F8 — Lemming** (reworded): place all hand Lemmings on random **empty** crossroads **adjacent to the triggering Lemming** (seeded RNG); leftover stay in hand; auto-placed copies' Battlecries fizzle.
  - **F9 — Return vs Remove Pile (wording convention):** "**…instead**" (Opossum) = the removal is **replaced** — never enters the Remove Pile, fires no trigger, doesn't count as removed. "**When this is removed, [do X]**" (Phoenix) = it **genuinely is removed** (fires the remove trigger) **then** relocated; moving it into the deck is a shuffle (fires the shuffle trigger). hellhound pulls a unit **out of** the Remove Pile to hand (+2 per E).
  - **F10 — Filtered draws are RANDOM, not tutors** ("draw a Rodent / a legendary / 2 Birds / a unit str≥6"): pick **uniformly at random among matching deck cards** (seeded RNG) into hand; **no choice, no deck inspection, no reshuffle**; fizzle if none. **Exception:** the Cheetah / Prince-Leo twins fetch the **specific named** sibling "from hand or deck" (designed pair, not an open tutor). *No open tutors in the pool for now.*
  - **F11 — Recurring turn-timed triggers** fire every time their window occurs while in play, **including the turn the unit was played** if the window is still ahead; "your turn" = **owner only**. (Golden egg corrected to "at the start of **your** turn".) Chipmunk's +5 is a one-shot scheduled payout.
  - **F12 — Oxpecker** reads the **fixed 30-card starting decklist** (a constant — same payout every time), **counts per copy**, **printed base strength ≥6** (dynamic cards with no fixed base don't count).
  - **F13 — Andean Condor** (also closes **I**): **reveal both decks' top cards publicly** (momentary, logged event); compare **printed base strength** (dynamic-no-base = 0); **strictly greater → draw yours**, else nothing; empty opponent deck = strength 0, empty own deck = fizzle.
  - **⚠ Remove Pile model (emerged from F5):** there is **one shared Remove Pile** — no separate "discard pile." **"Remove"** = any card sent there (from hand, deck, or board). **Two trigger tiers:** a **remove trigger** (fires on *any* removal) vs a **Deathrattle** (the narrower case of a *unit leaving the board*). *Reconciliation TODO: rename `overview.md` §3.7 "Discard" → **Remove Pile** and sweep "discard" wording across all docs/data.*
- **G. Once-per-turn caps.** Many value/food triggers state no cap (Queen Adira, Egg-deck food snakes, Jackal, etc.). Decide defaults; flag as tuning dials.
- **H. Food economy re-tuning.** New numbers everywhere (20-costs, 20-food Landmarks, Gazelle +20, Egg Eater 10…) vs `win_food` 100 and region 10/20. The whole shared scale needs re-derivation in sim.
- **I. Hidden-info / per-seat view — RESOLVED (2026-06-28).** No open tutors exist (F10 → filtered draws are random, no deck inspection). The only reveal is **Andean Condor** (F13): a momentary public reveal of both decks' top cards, logged as an event and deterministic. Nothing else leaks hidden info beyond the standard per-seat view.
- **J. Completeness.** ~15 open card slots/effects + most legendary "named individual" names still TBD. Decide whether to review-then-fill, or fill-then-implement.
