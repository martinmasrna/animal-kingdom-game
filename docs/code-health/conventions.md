# Code conventions observed in the repository

These describe existing practice. “Recommendation” marks a real inconsistency.

## Boundaries

- `engine/` owns state, legal moves, effects, strength, validation, and serialization. It is stdlib-only and imports no bots, presentation, or simulation modules.
- Cards/maps are JSON-backed frozen value objects. Behavior is keyed in `effects.EFFECTS`; live static and strength rules live in `statics.py` and `strength.py`.
- Bot policies are generalist. They use tags, keywords, board geometry, and public information, never deck slugs or archetypes. Search uses determinization for unknown zones.
- `sim/` schedules seeded games and aggregates records; `recording/` persists cohorts; `render/` returns markup; `cli.py` owns terminal I/O; `tui/` owns Textual.

**Recommendation:** define engine purity precisely. Current game-loop code is transport-free, while resource/config loaders read files. Say “pure after construction” or move those adapters outward.

## State, actions, and effects

- `GameState` mutates in place; branching callers use `clone()`.
- Cards, maps, config, actions, views, and results are frozen or immutable projections. `UnitInstance` is deliberately mutable and carries counters/flags; clones copy it.
- Effects are JSON-shaped op dictionaries on `effect_stack`, interpreted by `OPS`. Choice-producing operations return `PendingRequest`; never put closures in serializable state.
- Card triggers belong in `EFFECTS[card_id]`; broadly applicable behavior belongs in helpers/rules/statics/strength. Distinguish card design, hand instance, board instance, and board top.

**Recommendation:** bind placements to the exact eligible instance now that instances can have locks and counters.

## Determinism and hidden information

- Use carried seeded `random.Random` for chance; clone and serialization preserve its state. Sort unordered collections before order-sensitive work or RNG use.
- Per-seat views expose opponent counts, not identities/order. Open-decklist inference must be invariant to the hidden hand/deck split; determinization sorts the unseen multiset before shuffling.
- Simulations use stable seeds, both mover seats for non-mirrors, and ordered results under process pools.

## Data and balance values

- Card-intrinsic values such as base strength, food cost, rarity, tags, keywords, and text live in `cards.json`.
- Tunable effect magnitudes belong in frozen `Config` and are threaded through state; use `Config.sweep()` for variants.
- Text/data consistency tests must cover any independently authored printed number and resolver.

**Recommendation:** extend the existing food/cost guards to all numeric effects. Current effect handlers still contain hard-coded draw/count values.

## Errors and tests

- Validate input JSON at loaders and raise contextual domain `ValueError` subclasses. Use `ValueError` for library inputs, `SystemExit` for CLI/user-file errors, and `EngineError` for engine operations.
- Tests are organized by subsystem. Rule/effect scenarios use explicit boards; engine tests also cover fuzzing, determinism, cloning, serialization, and per-seat visibility.
- Regressions should encode the actual bug shape, including ordering, instance state, and determinization where relevant. Tests must stay deterministic; long simulations are measurement, not unit tests.

**Recommendation:** validate legal actions at the engine public boundary and add focused CLI/analysis smoke tests before pursuing broad coverage targets.
