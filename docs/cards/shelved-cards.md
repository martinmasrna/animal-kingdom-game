# Shelved Cards

Cards pulled out of an active deck and kept so their designs aren't lost. Two kinds:

- **The reserve**: cards still in `animal_kingdom/data/cards.json` with `"deck": "reserve"`, excluded from play. Their effect code lives in `engine/effects.py`; re-home one by changing its `deck`.
- **Out of the data**: the food_otk cuts below exist only as JSON in this file (their effect handlers are still registered in `effects.py`); re-home one by pasting it back.

## The reserve

Ids differ from names on several cards; the id is what goes in a decklist.

| Card (id) | Family | Rarity | Str | Text | Why it's here |
|---|---|---|---:|---|---|
| Eagle (`eagle`) | Bird | common | 5 | Flight. | Egg Control, 2026-09-30: cut for the Eggs. |
| Viper (`viper`) | Snake | common | 3 | Roar: an adjacent enemy gets -3 strength. | Egg Control, 2026-09-30: cut for the Eggs. Martin's note from play: the effect belongs on a flier. |
| Anaconda (`anaconda`) | Snake | common | 7 | Apex Predator. | Egg Control rebuild, 2026-09-28. |
| Eon, food engine (`eon_food_engine`) | Snake | legendary | 7 | Whenever a card is drawn, shuffled or removed, gain 1 food. | The old Eon; Eon is now the Ouroboros. |
| Unnamed Giant (`unnamed_giant`) | — | legendary | 10 | Apex Predator. Your regions produce no food. | Ramp pass, 2026-09-29: a strictly worse Borealis. |
| Shuck (`shuck`) | Canine | legendary | 6 | Roar: return a removed Canine to your hand. Give it +2 strength. | Canine's hand-buff half, see below. |
| Arctic Fox (`arctic_fox`) | Canine | rare | 3 | — | A bare placeholder for a rare Canine. |
| Unnamed Canine (`unnamed_canine`) | Canine | common | 3 | Roar: if this has 5 or more strength, draw a card. | The draw-at-5 threshold payoff, see below. |

---

---

## From the 2026-07-05 food_otk → pure-OTK overhaul

food_otk was three half-decks in a trenchcoat (a food-OTK package, a wall package, and a sacrifice package). The overhaul kept the OTK core and cut the other two. The wall bodies (Giant Tortoise) and the sacrifice/deathrattle cards below came out. Their effect handlers are still registered in `effects.py`, so re-homing is just a cards.json paste (+ tests).

### → future **Aristocrats (Spider)** deck

Carmilla and Black Widow are **Arachnids**, and the whole sacrifice/deathrattle package is a textbook *aristocrats* engine: remove your own units on purpose to convert them into cards and food. That's a coherent, flavourful archetype waiting to be built — a Spider/Arachnid family whose payoff is *feeding on its own*:

- **Carmilla, the Devourer** (L, Arachnid) — the sacrifice payoff (eat up to 3 friendlies, draw each).
- **Black Widow** (C, Arachnid) — the repeatable sac-for-value outlet.
- **Gazelle** / **Impala** — "when removed" fodder: sacrifice bait that pays food / cards on death.
- **Opossum** — recursion (Deathrattle: return to hand), replays the sac loop.
- **Pufferfish** — defensive sac (trades itself + the coverer, draws).

To finish the deck you'd want more Arachnids (a web/trap keyword?), and a couple more "when removed" and "sacrifice N friendlies" payoffs. Filed as an expansion candidate.

### Giant Tortoise → **Ramp** (or a defensive deck)

A plain STR-7 wall with Armor. Re-home it in a deck with a slot for an armored wall (the decks are locked 4-4-6, so it needs a swap, not a free add).

### Card JSON (paste back to re-home)

```json
{"id": "carmilla", "name": "Carmilla, the Devourer", "deck": "food_otk", "rarity": "legendary", "type": "unit", "tags": ["Arachnid"], "base_strength": 5, "keywords": [], "text": "Roar: remove up to 3 friendly units. Draw a card for each."}
{"id": "giant_tortoise", "name": "Giant Tortoise", "deck": "food_otk", "rarity": "rare", "type": "unit", "tags": [], "base_strength": 7, "keywords": ["Armor"], "text": "Armor."}
{"id": "opossum", "name": "Opossum", "deck": "food_otk", "rarity": "rare", "type": "unit", "tags": [], "base_strength": 2, "keywords": [], "text": "Roar: gain 5 food and draw 1 card. Deathrattle: return this to your hand."}
{"id": "black_widow", "name": "Black Widow", "deck": "food_otk", "rarity": "common", "type": "unit", "tags": ["Arachnid"], "base_strength": 3, "keywords": [], "text": "Roar: remove an adjacent friendly unit to draw 1."}
{"id": "pufferfish", "name": "Pufferfish", "deck": "food_otk", "rarity": "common", "type": "unit", "tags": ["Fish"], "base_strength": 2, "keywords": [], "text": "When an enemy unit is placed on top of this, remove that enemy unit and this unit. Draw 1 card."}
{"id": "impala", "name": "Impala", "deck": "food_otk", "rarity": "common", "type": "unit", "tags": [], "base_strength": 2, "keywords": [], "text": "When this is removed, draw 2."}
{"id": "gazelle", "name": "Gazelle", "deck": "food_otk", "rarity": "common", "type": "unit", "tags": [], "base_strength": 2, "keywords": [], "text": "When this is removed, gain 30 food."}
```

> **Note:** the `deck` field above still reads `"food_otk"`; update it when re-homing (e.g. `"aristocrats_spider"` for the Spider deck). The effect handlers (`_carmilla_place`, `_black_widow_place`, `_gazelle_remove`, `_impala_remove`, `_opossum_place`, `_pufferfish_covered`) remain in `effects.py`. The JSON predates later text rules: Opossum's "Deathrattle:" (no longer a keyword) and the 80-character limit need a rewrite when it comes back.

---

## Canine's hand-buff half

The Canine deck was split into two archetypes. Canine kept **tokens and board buffs** (go wide, pump the board). The other half, **hand buffs / go tall**, was pulled out to seed a future deck: Shuck and the draw-at-5 Unnamed Canine are its seed pieces in the reserve.

### → future **hand-buff (Primates?)** deck

The mechanical thesis, and *why* it must be its own deck: **"if this has ≥N strength" roars fire on entry — before any board buff can apply — so they can only be satisfied by buffing the card in hand first.** A threshold-payoff package therefore *requires* a hand-buff engine and cannot coexist with Canine's board-buff plan. That's a whole second archetype: pump units in hand, then deploy a pre-grown threat (which, unlike Canine's go-wide plan, can cover a big body from an empty board). Candidate flavor: **primates** — "train/develop the creature before it enters play" reads as intelligence/tool-use.

Seed pieces (designs, not final cards):

- **Shuck** (reserve): recursion and a hand buff, "Roar: return a removed [family] to your hand, give it +2 strength."
- **Unnamed Canine** (reserve): the threshold payoff, "Roar: if this has 5 or more strength, draw a card." The founding member of the "≥N strength" package.
- **A hand-buff Roar**: "give +1 strength to all [family] in your hand" (once Red Wolf's effect; the Canine that carried it is now Dhole, with a different effect).
- **New hand-buff common** (proposed) — "STR 3, Roar: give +2 strength to two units in your hand." Works from an empty board — the go-tall catch-up tool.
- **Reused threshold package** — mirror Colony's "5+ units" / OTK's "gained 10 food" payoff trio, but keyed on **strength** ("if this has ≥X strength: remove / draw / +str"). Keying on strength (not unit count) keeps it distinct from Colony and doubles down on the buff identity.

Status: **not built.** When it is, re-home Shuck and Unnamed Canine by changing their `deck` from `reserve` to the new slug (add it to `DECK_SLUGS`), and build to the standard 4-4-6. See [`docs/rules/mental-model.md`](../rules/mental-model.md) for why strength/covering — not HP — drives whether a pre-grown threat can cover a given body.
