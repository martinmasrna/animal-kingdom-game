# Card Balance — To-Do

Design decisions from the 200-game full 7×7 matchup simulation. The simulation used the
Greedy Bot, so these are directional signals rather than final human-play balance conclusions.
New-card candidates referenced here are consolidated in
[`../cards/card-candidates.md`](../cards/card-candidates.md).

## Locked changes

**✅ APPLIED 2026-07-04** (all items below, in one batch — cards.json/config.py/effects.py;
suite green at 308 passed/1 xfailed). Deck-shape math checked: aggro_hq_rush and egg_control
both stay 4-4-6/30 (Stoop's legendary slot backfilled by the new Aggro legendary; egg's two
vacated rare slots — Black Swan promoted out, Vulture shelved out — backfilled by Goliath
(demoted in) + Stoop (moved in)). Names are provisional pending the flavor pass, per the
notes below. See `docs/cards/decks/midrange-cats.md`, `aggro-hq-rush.md`, `egg-control.md`,
and `../cards/card-candidates.md` for the per-deck writeups.

- [x] **Prince Leo:** strength 4 → **3**.
- [x] **Princess Lea:** strength 4 → **3**.
- [x] **Queen Adira:** strength 6 → **5**.
- [x] **Skunk:** strength 2 → **4**.
- [x] **Aggro Hornet placeholder:**
  - Add **Flight**.
  - Replace its effect with: “Battlecry: You may remove another [this card] from your hand
    or deck. If you do, destroy an adjacent enemy unit.”
  - Final species/name remains a separate flavor decision.
- [x] **Stoop:** move from Aggro to Egg Control and change from legendary to **rare**;
  strength 6 → **4**; removal threshold “strength 6 or less” → **“strength 4 or less.”**
  Replace the legendary individual name with a generic bird identity in the flavor pass.
  *(Renamed "Peregrine Falcon"; internal id kept as `stoop` — id is invisible plumbing, only
  the printed name needed the generic-species treatment.)*
- [x] **Black Swan:** change from rare to **legendary**; keep strength 3; replace its effect
  with: “The first time each turn you draw Black Swan, your opponent removes a random card
  from their hand.” *(Implemented as a hard cap in `effects.py`, not a `Config` toggle — it's
  now printed text, not a sim dial.)*
- [x] **Goliath:** change from legendary to **rare**.
- [x] **Vulture:** shelve from Egg Control's initial 14-card package. Retain it as a candidate
  for the archetype's larger card pool rather than removing the design. *(cards.json record
  removed; `config.py`'s `vulture_food`/`cap_vulture` and `effects.py`'s handler left dormant
  for reactivation; see `card-candidates.md`.)*
- [x] **New Aggro legendary:** strength **4** with **Flight** and: “The first time an enemy
  unit covers this, return that enemy unit to its owner's hand.”
  - This retaliation is usable once each time this card enters play; track whether it has
    triggered on that unit instance.
  - Returning the coverer reveals this unit again on top of its crossroad.
  - Final species and legendary name remain a separate flavor decision. *(Provisional name:
    "Gale", id `gale`. Immovable coverers resist the bounce per the existing keyword physics
    ruling, but still consume the one-time charge; Stealth coverers are NOT protected, since
    this is an automatic/non-chosen trigger, matching the existing Stealth ruling.)*

## Reviewed — no change

- **Raksha:** keep strength 4 and its current anthem. It is a legendary centerpiece of the
  Canine strategy, so a high drawn win rate is expected.
- **Clarion:** keep strength 4 and its current Battlecry for the same reason.
- **Impala and Gazelle:** do not add Fragile. Being removed when covered does not fit their
  flavor well enough, and it would let ordinary friendly covering bypass the deck's intended
  sacrifice outlets.

## Open for design

No unresolved card-balance designs from this review.

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

Do not make another broad balance pass before testing the locked changes above. The Greedy Bot
is useful for gross outliers, but card-drawn win rate is especially vulnerable to game-length,
draw-timing, and pilot-policy bias.

- [ ] **Re-run Cats after the three locked strength reductions.** If Cats remain clearly above
  the field, change only one additional lever at a time. Test in this order:
  1. King Theron's cover-trigger once per turn.
  2. Snow Leopard strength 6 → 5.
  3. Jaguar's removal threshold 5 → 4.
  Do not apply these together; the current data cannot identify which part of the shell is
  responsible.
- [ ] **Prototype Colony's five-unit gates at four units.** Run one isolated experiment changing
  Guard Hornet, Soldier Ant, and Nurse Bumblebee from “5 or more Colony units” to “4 or more.”
  Colony currently tends to lose before its threshold cards switch on. Keep the shared threshold
  consistent during the experiment, then inspect each card before locking anything.
- [ ] **Watch Methuselah rather than nerfing it again immediately.** Its +12.5-point drawn impact
  is the loudest current signal, but the recurring food amount was already reduced to 5 and needs
  clean post-change data.
- [ ] **Watch Greywhisker as a role-compression card.** Food, replacement draw, and an extra
  placement on one STR 1 body may make it an automatic inclusion in future low-curve decks even
  if Food OTK itself remains weak. Test it outside its native package before changing it.
- [x] **Gazelle Deathrattle combo-consistency watch — superseded/resolved.** This item predates
  both the 2026-07-02 doubling (20→40) and the 2026-07-04 OTK-lean trim (40→30); the underlying
  question (does Carmilla + 3 Gazelles reliably one-shot?) was answered directly in
  `../balance/backlog.md` ("Watch: Carmilla OTK too consistent/early? — RESOLVED"): essentially
  never assembles (≤0.5% of games) at the settled ruleset, and 3×30=90 is now under `win_food`
  even in that rare case. Not a live concern.
- [ ] **Audit two-copy Goliath.** Moving it to rare improves access to Egg Control's scaling
  finisher. Measure late-game effective strength and how often Snake Egg finds both copies before
  considering a cap or formula change.
