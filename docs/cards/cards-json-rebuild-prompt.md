# Coding-agent instruction — Rebuild `cards.json` + data layer from the 7 reworked decks

**This is Phase 1 of "#5".** Phase 1 = correct, loadable, validated **static data** for the 98-design
reworked pool + the 7 premade decklists + green structural tests. **Phase 2 (separate prompt) = the
effect registry / card logic.** Do not implement effect logic here.

## Mission
Replace the legacy 55-card pool with the **98-design reworked pool** (7 premade 4-4-6 decks) as
**static data**, and migrate the data layer (loader, validation, deck construction, tests) to the new
schema — so Phase 2 can wire effects on top.

## Read first (authoritative & binding)
1. `docs/cards/decks/README.md` — deck index **and** the resolved decisions **A–J**. Binding. Especially
   **B** (schema: `type` + flat `tags` list incl. roles), **A** (every card globally unique, lives in
   exactly one deck), **C** (`Landmark` = the lone non-unit type; `Egg` is a unit), **D** (keywords;
   Apex Predator), **E** (strength model), **F** (event/op rulings), and the **Remove Pile** rename.
2. `docs/cards/decks/*.md` — the 7 deck files = **source of truth** for the card list (legendary names are
   now provisionally assigned). Each = 4 legendary ×1 + 4 rare ×2 + 6 common ×3 = 30.
3. `docs/rules/keywords.md` — canonical keywords (Flight, Immovable, Fragile, Apex Predator, Battlecry,
   Deathrattle). `Costs X food` is a **placement cost, not a keyword**. Strength "+X" is a text
   convention, not a keyword.
4. `docs/cards/cards.md` §2–4 — theme + conventions. **§5–9 are LEGACY — ignore** (do not reconcile to them).
5. Current code: `animal_kingdom/engine/cards.py` (Card dataclass + validation + loader),
   `animal_kingdom/data/cards.json` (old schema to evolve), `animal_kingdom/decks.py`,
   `animal_kingdom/engine/config.py`, and the `.tag` read-sites in `engine/statics.py` + `engine/effects.py`.

Do **not** diff against the old 55-card pool.

## Deliverables

### 1. `animal_kingdom/data/cards.json` — 98 records (one per design)
Fields per record:
- `id` — snake_case, **globally unique** (e.g. `prince_leo`, `queen_marabunta`, `gray_wolf`); derive from name.
- `name` — printed name (e.g. `"Queen Marabunta"`, `"Carmilla, the Devourer"`).
- `deck` — owning deck slug (one of: `cats_midrange`, `egg_control`, `colony_food_swarm`, `ramp`,
  `food_otk`, `aggro_hq_rush`, `canine_buff_tempo` — align to the deck filenames).
- `rarity` — `legendary` | `rare` | `common`.
- `type` — `unit` | `landmark`. **`landmark` only for Fig Tree and Watering Hole.** Eggs are `unit` (dec. C).
- `tags` — **flat list** of family + role tags (dec. B). Families: `Cat, Canine, Colony, Snake, Lizard,
  Bird, Rodent, Arachnid, Bear, Megafauna, Egg, Fish`. Roles: `Queen, Worker`. `[]` for tagless (`—`).
  Multi-tag allowed. **Retired tags forbidden:** no `Reptile` (→ Snake/Lizard), no `Insect` (→ Colony/Arachnid).
- `base_strength` — int 0–10, **or** the string `"dynamic"` (only the two no-printed-base cards:
  **Goliath** `=` and **Chameleon** `±∞`).
- `dynamic_strength` — rule-name string, present **iff** `base_strength == "dynamic"`. Mint:
  `removed_units_count` (Goliath = size of the Remove Pile), `chameleon` (±∞ bypass). The "+X per tag"
  cards (Champion of the Hive, Guard Hornet, African Wild Dog, Lobo, Verminus) keep their **printed int**
  base — their bonus is a Phase-2 anthem in `strength.py`, NOT a data dynamic.
- `keywords` — subset of the **static** keywords `{Flight, Immovable, Fragile, Apex Predator}`.
  `Battlecry`/`Deathrattle` are trigger prefixes printed in `text` (hooks wired in Phase 2) — do **not**
  store them as keywords. Follow `keywords.md`.
- `food_cost` — int ≥ 0, **only** where the text says "Costs X food" (Ramp's 20-cost bodies). Else omit/0.
- `text` — the printed card text, verbatim from the deck file.

### 2. Loader + validation — `engine/cards.py`
- Migrate `Card`: **`tag: Optional[str]` → `tags: frozenset[str]`**; add `type: str`, `deck: str`,
  `food_cost: int = 0`.
- `KEYWORDS` → add `Apex Predator` (static set). Add `TAGS` allow-set and `TYPES = {"unit","landmark"}`.
  `DYNAMIC_STRENGTHS` → `{"removed_units_count","chameleon"}` (drop legacy `control_count`/`discard_count`).
- **`COPY_LIMITS`: `common` 4 → 3** (locked 4-4-6: legendary 1 / rare 2 / common 3).
- Extend `validate_card_record`: `type ∈ TYPES`; `landmark ⇒ id ∈ {fig_tree, watering_hole}`; every tag in
  `TAGS`; `food_cost` int ≥ 0; `deck` present; `dynamic_strength ∈ DYNAMIC_STRENGTHS`. Keep "parse, don't
  validate; loader is the trust boundary" and per-record error messages.

### 3. Premade decks — `decks.py`
- Add `PREMADE_DECKS: dict[str, list[str]]` (deck slug → 30 card ids), expanding each design by
  `COPY_LIMITS[rarity]` (4×1 + 4×2 + 6×3 = 30) and a `load_premade_deck(slug)` helper.
- Decide `make_vanilla_deck`'s fate (keep working against the new pool, or retire if unused). Keep `cli.py`
  loading a valid deck.

### 4. Migrate `.tag` → `.tags` (breaking change)
Grep `.tag` and convert every read: `placer.tag == "Cat"` → `"Cat" in placer.tags`, etc. Sites include
`engine/statics.py` (Cougar, Snow Leopard, the cover checks) and `engine/effects.py` (the `play_extra`
"cat" constraint) and `decks.py`. Pure mechanical semantics swap.

### 5. Tests — `tests/`
Add structural tests for the new pool, and update old tests that assumed the old pool / `Card.tag`:
- 98 designs load; exactly 7 decks; each deck = 14 designs (4 leg + 4 rare + 6 common); each expands to 30.
- IDs **and** names globally unique.
- `base_strength` domain; `dynamic_strength` present iff dynamic; only Goliath + Chameleon are dynamic.
- `keywords ⊆ {Flight,Immovable,Fragile,Apex Predator}`; `tags ⊆` allow-set, no retired tags; `type` domain;
  landmark only the 2 cards; `food_cost` present only where `text` contains "Costs".

## Scope guards — do NOT do here (Phase 2 / later)
- **No card effect logic.** No new `EFFECTS` hooks, `OPS`, `statics` predicates, `strength.py`
  anthems/counters/dynamic computation, scheduler payloads, or new mechanics (Apex Predator placement,
  sacrifice/Deathrattle, bounce/lock, random-filtered draw, store-and-double, remove-stack, Colony role
  queries, shuffle/draw/remove→food, hand-card buffs).
- The existing **M2a handlers** key old-pool ids. Keep `effects.py`/`statics.py` **importable** (do the
  `.tag`→`.tags` migration) but leave old `EFFECTS`/`OPS` entries dormant. If `tests/test_effects.py` (or
  others) assert old-pool behavior the new data breaks, mark them
  `@pytest.mark.skip(reason="effects re-implemented for the reworked pool in Phase 2")` — note each skip;
  do not force-fix them.
- **No balance tuning** — don't finalize `config.py` food constants (G/H is a deferred sim job).
- **No legendary-name or flavor changes** (provisional names are fixed for this build).

## Recommended secondary deliverable (planning only, no logic)
`docs/engine/effect-worklist-reworked.md` — catalog every new card's required effect, grouped like
`m2b-worklist.md` (reuses-existing-op vs new-mechanic), to scope Phase 2.

## Process & conflict rules
- README decisions A–J and `keywords.md` are binding. On conflict: the **deck file wins** for card
  *content*; the **decision/keyword doc wins** for *schema/rules*.
- Run the full test suite; keep it green (minus documented skips). Don't commit or push unless asked.
  End with a summary: files changed, deck/card counts, and any ambiguity you resolved.

## Ambiguities to resolve with judgment (note your choice)
- `archetype` field: drop in favor of `deck`, or set per deck identity (Cats=midrange, Egg=control,
  Colony=combo, Ramp=control, Food OTK=combo, Aggro HQ=aggro, Canine=aggro/tempo). Don't block on it.
- Whether to keep `make_vanilla_deck`.
