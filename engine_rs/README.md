# The engine in Rust

The Python engine (`animal_kingdom/engine`) and bots (`animal_kingdom/bots`) are the specification; this crate is the same game and the same players, compiled. One set of rules, one card table (`data/cards.json`), one Config (handed over as a dict), and the bots' search, seeds and tie-breaks reproduced move for move.

## Build

```
brew install rust                      # once
cd engine_rs && ../.venv/bin/maturin develop --release
```

That installs the module `ak_engine` into the venv. `cargo build --release --no-default-features --bin bench` builds the standalone timing binary without the Python glue (it prints ms per action and state clones per action).

`engine_rs/pgo.sh` builds the venv module profile-guided (about 9% off the Expert's move): an instrumented timing binary plays Expert games across six deck pairs, the profiles are merged with Homebrew llvm's `llvm-profdata`, and `maturin develop --release` builds with them. The profile stays local under `engine_rs/target/pgo/`; the Fly image builds without it. Rerun the oracles after it like after any build.

## Speed, and where it goes

The Expert's move on the timing binary (one core, the hand evaluation, Expert against Expert): 24.4 ms at the end of the first night, 17 ms after the 2026-10-23 pass, 15.7 ms profile-guided. A profile of the move: the search copies the position about 14,000 times an action (once per candidate the greedy policy evaluates, in both engines), and that copying is about a quarter of the time; allocation and freeing of the Python-shaped effect steps about a tenth; the board cache, strength and the evaluation a few percent each; the rest is the rules themselves. What was tried and measured on the way: a lazy board cache (slower: the check on every read costs more than the recomputes it saves), the step maps inline instead of on the heap (slower: the state grows by their inline size and every clone pays it), per-evaluation vectors inline (no change). What is left is structural: apply-evaluate-undo on one position instead of a copy per candidate, worth perhaps 15% for a rewrite of every mutation in the effect system.

## Use

- `AK_RUST_BOTS=1` makes `sim.runner.make_bot` return a `RustBot` (`animal_kingdom/bots/rust_bot.py`) for every bot kind; the benchmark (`tools/bot_bench/bench.sh`), self-play (`animal_kingdom.learn.selfplay`) and every sim honour it. `AK_PY_BOTS=1` forces the Python bots.
- `ak_engine.Engine(cards_json, maps_json, config_json, map_id)`, `engine.new_game(deck_a, deck_b, seed, first_player, stacked)`, `engine.from_dict(state_dict)`; a `State` has `clone`, `legal_actions`, `apply_action(dict, validate)`, `apply_logged`, `is_terminal`, `to_dict`, `events`, `extract(player, feature_set)`, `evaluate(player, overrides_json)`.
- `ak_engine.Bot(spec, seed, evaluator_json)` with `choose(state)`, `root_scores(state)`, `stats()`; `ak_engine.play_game(...)` plays a whole game in Rust and records the self-play feature rows.

## Proof

Every change is reproven by the four oracles in `tools/engine_rs/`:

- `oracle.py`: every logged game replayed through both engines, the serialised position and the legal-action list compared after every action.
- `fuzz.py --all-cards`: random games over every card, a random legal action each step, the same comparison.
- `bot_oracle.py`: the same positions and seeds, the Python bot and the Rust bot must choose the same move with the same root scores (greedy, turn, the Expert).
- `feature_oracle.py`: the rung-2 feature vector and the Expert's evaluation agree to 1e-9.

The two engines are meant to agree to the bit, not to a tolerance: a tie deep in the search broken on a last-bit difference sends the two searches down different lines (the slot network's Expert disagreed with Python on one position in twenty, by ten points, with identical features everywhere). The one source found so far was serde_json's default float parsing, best-effort rather than correctly rounded, which put some network weights an ulp off Python's; the crate's `float_roundtrip` feature closes it. The root ordering still rounds its sort key, and the bot oracle still allows 1e-9 on a decided line near ±4e8, where the two engines' arithmetic differs in the last bits.

## Layout

`state.rs` (the position, its cache, serialisation), `rules.rs`, `effects.rs` (the effect stack and its operations), `cards.rs` (every card's hooks, the THEN table), `statics.rs`, `strength.rs`, `data.rs` (cards, maps, config), `rng.rs` (CPython's `random.Random`, bit for bit), `value.rs` (the step data), `bots/` (features and evaluation, greedy, the determinized search for turn and referee, worlds), `py.rs` (the Python module), `bin/bench.rs`.
