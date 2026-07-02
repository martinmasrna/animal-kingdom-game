# Engine Build — Handoff Instructions

> **Audience:** the coding agent implementing the game engine.
> **Status:** Phase 0 + Phase 1 of the project. Build the headless engine, data, bots, and a simulation harness. **Do not** build the web/UI layer yet — but structure everything so it drops on top cleanly later (see §4).

---

## 1. Purpose

The end goal is **balance data**: run thousands of simulated games between bot players and measure whether the card pool and archetypes are balanced. A human-playable app comes later. Your job is the foundation: a clean, headless **rules engine** as a reusable library, plus bots and a simulation harness on top of it.

You are **not** designing the game — the design is fixed in the docs below. You are implementing it faithfully and flagging (not silently resolving) any ambiguity.

---

## 2. Source-of-truth documents

Read these first. They are authoritative; this handoff does not repeat their content.

| Doc | Contains |
|---|---|
| `docs/rules/overview.md` | Core rules: setup, turn structure, placement legality, strength/covering, stacks, connection-to-HQ, effects, food/regions, victory conditions, deckbuilding, match structure. |
| `docs/cards/cards.md` | The full card pool (~57 units across Aggro / Control / Combo / Midrange / General), keywords (Flight, Immovable, Fragile, "Battlecry" = when-placed), tags, and design conventions. **Each card's effect text is the spec you must implement.** |
| `docs/rules/maps.md` | Map format + Map A "Savanna Crossing" (the first test map), plus the shared setup rules and the food scale. |
| `docs/STATUS.md` | Open design decisions. Several constants are deliberately untuned (see §11). |

If this handoff and a source doc ever conflict, **the source doc wins** — flag the conflict.

---

## 3. Scope

**In scope (build this):**
1. **Data** — structured card data for the full `cards.md` pool, and map data for Map A.
2. **Engine** — headless rules library: state, legal-action generation, action application, the card-effect trigger system, win/exhaustion checks.
3. **Bots** — a random bot and a greedy heuristic bot, behind one interface.
4. **Simulation harness** — run N games, collect the metrics in §10.
5. **Text renderer + CLI** — render a game state as ASCII and play bot-vs-bot (and hotseat) in the terminal, for sanity-checking the engine.
6. **Tests** — see §12.

**Out of scope (do NOT build now):**
- Web server / HTTP / WebSocket API.
- Any graphical or web UI.
- ML/RL bots, MCTS (greedy heuristic is enough for now).
- Networking, accounts, persistence beyond local sim logs.

Keep the boundaries in §4 so the deferred web layer is a thin add-on later.

---

## 4. Architecture principles (the important part)

The single most important decision: **the engine is a pure, transport-agnostic library.** Everything else is just a different caller of it (sims in-process, a CLI, and later a web server).

Hard rules:

1. **No I/O in the core.** The engine never prints, reads input, touches the network, or accesses the clock/RNG globally. All randomness goes through an injected, seedable RNG. All output is return values.
2. **Pure transition function.** The core is essentially:
   - `legal_actions(state) -> list[Action]`
   - `apply_action(state, action) -> state` (return a new/updated state; make cloning cheap and correct — sims and any future lookahead bot will clone states a lot).
   - `is_terminal(state) -> Optional[Result]`
3. **The same action interface drives bots and (future) humans.** A bot picks from `legal_actions`; a UI will render `legal_actions` as the clickable options. Build it once.
4. **Actions and state are serializable** to plain dicts/JSON. This one representation is your API payload, your replay log, and your sim log.
5. **Per-seat views from day one.** Implement `state.view_for(player)` that strips hidden information (opponent's hand *contents* and both decks' order/contents become counts only; board, discard, and food totals are public). Even though the first CLI is hotseat/full-information, build this now — retrofitting hidden-info filtering later is painful.
6. **Determinism.** Given the same seed and the same action sequence, a game must replay identically. Essential for reproducing balance results and debugging.

If you honor these six, adding FastAPI + a TS frontend later is a thin wrapper, not a rewrite.

---

## 5. Tech stack & project layout

- **Language:** Python 3.11+.
- **Core engine: standard library only** (no third-party deps). Keep it importable and fast.
- **Analysis layer may use** `pandas` (and optionally `matplotlib`) — isolate these in the sim/analysis modules, not the engine.
- **Data files: JSON** (dependency-free). Static card fields live in JSON; card *effect logic* lives in Python (see §6.3).
- **Tests:** `pytest`.
- Use `pyproject.toml`; core deps empty, an `[analysis]` extra for pandas.

Suggested layout (adjust if you have a better structure, but keep the engine isolated and dependency-free):

```
animal_kingdom/
  engine/
    state.py        # GameState, unit instances, per-seat views, (de)serialization
    actions.py      # Action types (Draw, Place, ...)
    rules.py        # legal_actions, apply_action, connection, covering, win checks
    effects.py      # trigger/event system + per-card effect handlers
    cards.py        # card registry: load JSON static data + bind effect handlers
    maps.py         # map loading + region/adjacency helpers
    config.py       # tunable constants (food F values, thresholds) in one place
  data/
    cards.json
    maps.json
  bots/
    base.py         # Bot interface
    random_bot.py
    greedy_bot.py
  sim/
    runner.py       # run N games
    metrics.py      # aggregate results
  render/
    text.py         # ASCII board/state renderer
  cli.py            # play bot-vs-bot or hotseat in terminal
  tests/
pyproject.toml
README.md
```

---

## 6. Data model

### 6.1 Game state (must capture all of these)
- The **map** (or a reference to it) and, per crossroad, the **stack** of units (ordered bottom→top; only the top is visible/controls the crossroad — see `overview.md` Stacks).
- **HQ** ownership and captured status.
- Per player: **hand**, **deck** (ordered, face-down), **discard** (shared, public), **food** total.
- **Whose turn** it is, a **turn counter**, and **first/second player** identity.
- **Per-turn bookkeeping:** units placed this turn (for "if you have already placed another unit this turn", e.g. Army Ant), and once-per-turn trigger flags (e.g. Vulture).
- **Pending delayed effects** — a scheduler keyed by turn (Egg "after 2 turns", Hibernating Bear "two turns later", Rabbit "start of your next turn"). See §8.

Each **unit instance** = card id + owner + a unique instance id + any per-instance state (e.g. "placed on turn T" for Armadillo, delayed-timer bookkeeping).

### 6.2 Card static data (`cards.json`)
One record per card with the fields from `cards.md`: `id`, `name`, `tag` (may be null/`—`), `rarity` (common/rare/legendary), `base_strength` (integer, or a marker like `"dynamic"` for Nile Crocodile / Anaconda / Chameleon), `keywords` (e.g. `["Flight"]`, `["Immovable"]`, `["Fragile"]`), and a short `text` (the printed reminder). Port the **entire** pool.

### 6.3 Effect registry (Python)
Card *logic* cannot live in JSON. Maintain a registry mapping `card id -> effect handlers`. A card's handlers subscribe to the relevant events/modifiers (§8). The JSON gives static stats and text; the registry gives behavior. This split keeps a future TS client able to read card stats/text from JSON while logic stays server-side.

### 6.4 Map data (`maps.json`)
Encode Map A exactly per `docs/rules/maps.md` §4.3: crossroads, edges (orthogonal grid + HQ front edges), HQ connections, regions (corners + food), and `win_food`. Provide helpers: `neighbors(crossroad)`, `adjacent(a,b)` (= connected by an edge), region-control check (player occupies all corners), and connectivity (§7).

---

## 7. Core rules to implement (see `overview.md` for exact wording)

- **Turn actions:** either **Draw 2** or **Place one unit** (some effects grant extra draws/placements within the turn).
- **Legal placement:** empty crossroad, own-occupied crossroad, enemy unit of strictly lower strength (covering), or an enemy HQ — and the location must be **connected to the active player's HQ** unless modified (Flight ignores connection). A player **cannot** place on their own HQ.
- **Connection:** a path from the player's HQ through crossroads they currently occupy to the destination. Implement as graph traversal over own-occupied crossroads.
- **Covering / strength:** covering an enemy needs **strictly greater** effective strength; placing on your own unit has no strength requirement. Stacks: only the top unit is visible/counts; removing it reveals the one beneath.
- **Regions & food:** at the **end of each player's turn**, they gain food from every region they fully control. Crossing `win_food` wins.
- **Victory:** capture enemy HQ, reach `win_food`, or win on **exhaustion** (opponent can neither draw nor place). Check victory after each action's resolution and after end-of-turn food.

### 7.1 Two distinct effect systems — keep them separate
1. **Static modifiers** evaluated *during* `legal_actions` and resolution — they change legality, strength, or targeting. Examples: Flight (ignore connection), Honey Badger / Spotted Hyena / Snow Leopard (covering-rule changes), Giant Tortoise (can't be covered), Immovable (can't be removed/moved by effects), Black Panther / Pangolin (can't be targeted by enemy effects), Armadillo (can't be removed until your next turn), Fragile, and **dynamic strength** (§9).
2. **Triggered effects** dispatched via the event system (§8) when something happens. Examples: all "When placed" battlecries, death triggers, on-covered traps, reactive removal, food-gain riders.

Do not try to force static modifiers through the event bus, or legal-action generation through triggers. They are different mechanisms.

---

## 8. Trigger / event system

Card effects subscribe handlers to event types; the engine dispatches events as it mutates state. Cover at least these (derived from the current pool — verify against `cards.md`):

| Event | Fires when | Example cards |
|---|---|---|
| `ON_PLACE` (Battlecry) | a unit is placed | most "When placed…" cards |
| `ON_PLACE_ONTO_ENEMY` | a placement covers an enemy unit | Piranha, Boa Constrictor |
| `ON_REMOVE` / death | a unit leaves play to discard | Cape Buffalo, Hedgehog; Opossum (returns to hand instead) |
| `ON_COVERED` | an enemy unit is placed on top of this unit | Pufferfish, Porcupine-style traps |
| `ON_ENEMY_PLACED_ADJACENT` | an enemy unit is placed on an adjacent crossroad | Hippopotamus |
| `ON_ENEMY_REMOVED` (once/turn) | any enemy unit is removed | Vulture |
| `ON_FOOD_GAINED` | controller gains food | Queen Bee |
| `START_OF_TURN` | a player's turn begins | Beaver; delayed-effect resolution |
| delayed / scheduled | N turns after an event | Egg, Hibernating Bear, Rabbit |

Design the dispatcher so adding a card = registering handlers, with no changes to core loop code. Define and document **resolution order** for simultaneous triggers (e.g. a placement that both triggers a battlecry and covers an enemy) and make it deterministic.

---

## 9. Dynamic strength

Strength is **not** always static. Implement `effective_strength(state, unit) -> int` computed from state, used everywhere strength matters (covering checks, removal thresholds, region holding):

- **Nile Crocodile** = number of units you control.
- **Anaconda** = number of units in the discard.
- **Chameleon** = `±∞` semantics (can be placed on any unit, and any unit can be placed on it) — model carefully; it bypasses the covering comparison both ways.
- **Snow Leopard** (anthem) modifies *other* Cats' placement permissions.
- **Wildebeest** = base +2 while you control a region.

Decide and document **when** dynamic strength is snapshotted (e.g. evaluated live at comparison time vs. captured on placement) and keep it consistent.

---

## 10. Bots & simulation

### 10.1 Bot interface
```python
class Bot:
    def choose(self, view: StateView, legal: list[Action]) -> Action: ...
```
Bots receive only the **per-seat view** (§4.5), never hidden info. Implement:
- **RandomBot** — picks a uniformly random legal action. Doubles as an engine fuzzer.
- **GreedyBot** — a board-evaluation heuristic + 1-ply lookahead over legal actions. Evaluation should consider: food progress vs threshold, board presence/connection, threat to the enemy HQ, threat to your own HQ, and card economy. Keep the eval weights in one place so they're tunable.

### 10.2 Simulation harness
Run N games for given (roster A, roster B, map, seed) and aggregate. For the first pass, fixed archetype decks are fine (full deckbuilding/per-map removal can come later). Collect:
- **Archetype matchup matrix** (validates the intended rock-paper-scissors in `cards.md` §3.5).
- **Win-condition split**: HQ capture vs food vs exhaustion.
- **First-player win rate** (target ≈ 50% with the 3/4 opening-hand split — `maps.md` §5).
- **Average game length** (turns).
- **Per-card win-rate delta**: presence in wins vs losses.

Output machine-readable (CSV/JSON) for analysis in pandas.

> **Caveat to honor:** balance conclusions are only as good as the bots. A greedy bot underplays Combo (multi-turn payoffs) and sequencing chains (Wild Dogs / Domestic Cat). Note this in the harness output; do not let it silently bias conclusions.

---

## 11. Tunable constants (do NOT hard-code; centralize in `config.py`)

These are deliberately **untuned placeholders** (see `cards.md` §4.5 and `docs/STATUS.md`). Put them all in one config object the sim can sweep:
- Every `F` value on cards (one-off food gains/costs).
- Region outputs and `win_food` (Map A starts at 10 / 20 / 100 — `maps.md` §4).
- Spotted Hyena threshold `N`; Hibernating Bear doubling and delay; Egg/Rabbit timers.

The simulator's first real job is to tune these together on one shared scale.

---

## 12. Build order & acceptance criteria

Work in milestones; each should be runnable and tested before moving on.

- **M0 — Data & loading.** `cards.json` (full pool) + `maps.json` (Map A) load and validate (every card has required fields; every map region's corners exist; edges are symmetric). *Done when:* a loader test passes for the whole pool.
- **M1 — Vanilla engine.** State, `legal_actions`, `apply_action`, connection, covering, stacks, food production, all three win conditions — **with no card effects yet** (treat every card as a vanilla body). RandomBot vs RandomBot plays thousands of games to completion. *Done when:* fuzzing finds no illegal states or crashes, every game terminates (add a max-turn safety cap), and the text renderer shows a sane board.
- **M2 — Effects.** Trigger system + static modifiers + dynamic strength; implement **every** card in `cards.md`. *Done when:* each card has a unit test asserting its effect, and RandomBot fuzzing with the full pool stays legal/terminating.
- **M3 — Greedy bot + metrics.** GreedyBot and the sim harness producing the §10 metrics to CSV/JSON. *Done when:* a multi-thousand-game run emits the matchup matrix, win-condition split, first-player win rate, and per-card win-rate delta.

---

## 13. Testing requirements

- **Property/fuzz:** random-bot games never reach an illegal state and always terminate (max-turn cap). Same seed + same actions ⇒ identical replay (determinism).
- **Per-card golden tests:** one focused test per card asserting its effect in a constructed scenario (e.g. Boa Constrictor removes instead of stacking; Pufferfish trades 1-for-1 on cover; Nile Crocodile strength tracks board count; Hibernating Bear pays out two turns later; Vulture draws once per turn).
- **Rules tests:** connection (incl. Flight bypass), covering thresholds (strict vs equal-or-lower modifiers), stack reveal on removal, region control & food production, each win condition, hidden-info filtering in `view_for`.

---

## 14. Open rules questions — flag, don't silently guess

Where the docs are silent or ambiguous, implement the listed default, mark it with a clearly searchable `TODO(rules)` comment, and surface a consolidated list for the human. Do **not** invent rules quietly.

- **Hand limit vs Draw 2:** hand max is 8 (`overview.md`). What happens drawing 2 at 7 cards? *Default:* draw up to the limit; if the action can't be taken legally at full hand, it isn't offered. Flag.
- **Deck with 1 card on a Draw action.** *Default:* draw what's available (1). Flag.
- **Exhaustion exact trigger** and tie-breaking (`overview.md` §11.3). Implement as written; flag edge cases.
- **First-player determination:** coin flip via the injected seed. Flag if a fairer method is wanted.
- **Effect targeting choice:** the controller chooses among legal targets; bots pick per their policy. Confirm "may" vs "must" wording per card.
- **"Adjacent"** = connected by a single edge (no diagonals on Map A). Confirm.
- **Simultaneous region captures / multiple triggers:** define a deterministic resolution order and document it.
- **Dynamic-strength snapshot timing** (§9) — pick one rule, document it.

---

## 15. Definition of done (Phase 0/1)

1. Full card pool + Map A as validated data.
2. A dependency-free engine library honoring the §4 principles (pure transitions, serializable state/actions, per-seat views, seeded determinism).
3. Every `cards.md` card implemented and unit-tested.
4. Random + greedy bots behind one interface.
5. A sim harness emitting the §10 metrics to CSV/JSON over thousands of games.
6. A text renderer + CLI for bot-vs-bot and hotseat play.
7. A short `README.md`: how to run tests, a sim, and a CLI game.
8. A consolidated list of every `TODO(rules)` flag raised (§14) for the human to resolve.

Build the engine as a library first; the web app is a later, thin layer on top — keep it that way.
