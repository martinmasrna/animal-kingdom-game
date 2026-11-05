# The engine in the browser: status

A practice match against a bot played entirely in the browser: the engine and the bot compiled to WebAssembly, the bot
thinking in a Web Worker on the player's device, no server round trip per move, and the match sent to the server when
it ends so it counts and is kept. Branch `engine/wasm`.

## Where it stands

1. **The crate builds for wasm32** (done). `engine_rs/wasm.sh` builds it (`--no-default-features --features wasm`,
   profile `wasm`) and binds it with wasm-bindgen into `animal_kingdom/web/static/wasm/` (`ak_engine.js`,
   `ak_engine_bg.wasm`, `manifest.json`). The Python glue stays behind the default `python` feature; the native and
   Python builds are unchanged. Three things differ on wasm32 only: no mimalloc (its C doesn't build there), the bots'
   clock is the browser's `Date.now()` (`src/clock.rs`; `std::time::Instant::now` panics there), and the whole-turn
   search (`atomic`) runs its jobs on one thread. The module (`src/wasm.rs`): `Engine(cards, maps, config, map)`,
   `newGame`, `fromJson`, a state's `legalActions`, `applyAction`, `applyLogged`, `toJson` (the dict the Python engine
   serialises), `takeEvents`, `view(seat)`, and `Bot(spec, seed, evaluator)` with `choose`. `view` is
   `src/view.rs`: the engine's part of `match.py`'s `_game_view`, so the client draws from the same view the server
   sends without a second copy of the rules in JavaScript.
2. **Parity** (done). `node tools/engine_rs/wasm_oracle.mjs --limit 100`: the 100 newest logged human games that replay
   on today's cards, through the wasm build and the Python engine side by side (`tools/engine_rs/wasm_trace.py` streams
   the Python side), the serialised position, the legal actions and both seats' views compared after every action.
   2026-11-05: 100 of 100 agree, 3,403 actions, 3,503 positions, 6 s. A changed number in a view fails it (checked by
   breaking one on purpose). `fuzz.py --all-cards --games 40` on the native module after the change: 40 of 40.
3. **The client** — in progress.
4. **Numbers** — not measured yet.

## Source hash

`engine_rs/build.rs` embeds a hash of the crate's game sources, everything but the glue (`src/py.rs`, `src/wasm.rs`)
and the timing binary (`tools/engine_rs/wasm_hash.py` computes the same); `ak_engine.source_hash()` on the server and
`sourceHash()` in the browser. The client plays locally only when the two agree, else it plays the match on the server
as today: a wasm built from other engine sources than the server's never plays a different game. Rebuild with
`engine_rs/wasm.sh` after any change under `engine_rs/` and commit `static/wasm/` with it; until then `?local=1`
quietly plays on the server.

## Set up (once per machine)

`rustup target add wasm32-unknown-unknown`, then `cargo install wasm-bindgen-cli --version 0.2.130` (the version in
`engine_rs/Cargo.lock`). wasm-opt (binaryen) is optional: `wasm.sh` runs it when it is on the path.
