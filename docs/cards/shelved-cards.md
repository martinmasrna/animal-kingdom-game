# Shelved Cards

Cards pulled out of an active deck but kept here so their designs (and their effect code,
which still lives in `engine/effects.py`) aren't lost. Re-home them by pasting the JSON back
into `animal_kingdom/data/cards.json` with an updated `deck` slug.

---

## From the 2026-07-05 food_otk → pure-OTK overhaul

food_otk was three half-decks in a trenchcoat (a food-OTK package, a wall package, and a
sacrifice package). The overhaul kept the OTK core and cut the other two. The wall bodies
(Giant Tortoise) and the sacrifice/deathrattle cards below came out. Their effect handlers
are still registered in `effects.py`, so re-homing is just a cards.json paste (+ tests).

### → future **Aristocrats (Spider)** deck

Carmilla and Black Widow are **Arachnids**, and the whole sacrifice/deathrattle package is a
textbook *aristocrats* engine: remove your own units on purpose to convert them into cards
and food. That's a coherent, flavourful archetype waiting to be built — a Spider/Arachnid
tribe whose payoff is *feeding on its own*:

- **Carmilla, the Devourer** (L, Arachnid) — the sacrifice payoff (eat up to 3 friendlies, draw each).
- **Black Widow** (C, Arachnid) — the repeatable sac-for-value outlet.
- **Gazelle** / **Impala** — "when removed" fodder: sacrifice bait that pays food / cards on death.
- **Opossum** — recursion (Deathrattle: return to hand), replays the sac loop.
- **Pufferfish** — defensive sac (trades itself + the coverer, draws).

To finish the deck you'd want more Arachnids (a web/trap keyword?), and a couple more
"when removed" and "sacrifice N friendlies" payoffs. Filed as an expansion candidate.

### Giant Tortoise → **Ramp** (or a defensive deck)

A plain STR-7 Immovable wall. Fits Ramp's immovable-megafauna identity; re-home there when
Ramp has a slot (it's currently a locked 4-4-6, so it needs a swap, not a free add).

### Card JSON (paste back to re-home)

```json
{"id": "carmilla", "name": "Carmilla, the Devourer", "deck": "food_otk", "rarity": "legendary", "type": "unit", "tags": ["Arachnid"], "base_strength": 5, "keywords": [], "text": "Battlecry: remove up to 3 friendly units. Draw a card for each."}
{"id": "giant_tortoise", "name": "Giant Tortoise", "deck": "food_otk", "rarity": "rare", "type": "unit", "tags": [], "base_strength": 7, "keywords": ["Immovable"], "text": "Immovable."}
{"id": "opossum", "name": "Opossum", "deck": "food_otk", "rarity": "rare", "type": "unit", "tags": [], "base_strength": 2, "keywords": [], "text": "Battlecry: gain 5 food and draw 1 card. Deathrattle: return this to your hand."}
{"id": "black_widow", "name": "Black Widow", "deck": "food_otk", "rarity": "common", "type": "unit", "tags": ["Arachnid"], "base_strength": 3, "keywords": [], "text": "Battlecry: remove an adjacent friendly unit to draw 1."}
{"id": "pufferfish", "name": "Pufferfish", "deck": "food_otk", "rarity": "common", "type": "unit", "tags": ["Fish"], "base_strength": 2, "keywords": [], "text": "When an enemy unit is placed on top of this, remove that enemy unit and this unit. Draw 1 card."}
{"id": "impala", "name": "Impala", "deck": "food_otk", "rarity": "common", "type": "unit", "tags": [], "base_strength": 2, "keywords": [], "text": "When this is removed, draw 2."}
{"id": "gazelle", "name": "Gazelle", "deck": "food_otk", "rarity": "common", "type": "unit", "tags": [], "base_strength": 2, "keywords": [], "text": "When this is removed, gain 30 food."}
```

> **Note:** the `deck` field above still reads `"food_otk"` — update it when re-homing (e.g.
> `"aristocrats_spider"` for the Spider deck). The effect handlers (`_carmilla_place`,
> `_black_widow_place`, `_gazelle_remove`, `_impala_remove`, `_opossum_place`,
> `_pufferfish_covered`) remain in `effects.py`.
