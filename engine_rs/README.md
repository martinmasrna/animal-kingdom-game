# The engine in Rust

The Python engine (`animal_kingdom/engine`) and bots (`animal_kingdom/bots`) are the specification; this crate is the same game and the same players, compiled. One set of rules, one card table (`data/cards.json`), one Config (handed over as a dict), and the bots' search, seeds and tie-breaks reproduced move for move.

## Build

```
brew install rust                      # once
cd engine_rs && ../.venv/bin/maturin develop --release
```

That installs the module `ak_engine` into the venv. `cargo build --release --no-default-features --bin bench` builds the standalone timing binary without the Python glue.

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

## Layout

`state.rs` (the position, its cache, serialisation), `rules.rs`, `effects.rs` (the effect stack and its operations), `cards.rs` (every card's hooks, the THEN table), `statics.rs`, `strength.rs`, `data.rs` (cards, maps, config), `rng.rs` (CPython's `random.Random`, bit for bit), `value.rs` (the step data), `bots/` (features and evaluation, greedy, the determinized search for turn and referee, worlds), `py.rs` (the Python module), `bin/bench.rs`.
