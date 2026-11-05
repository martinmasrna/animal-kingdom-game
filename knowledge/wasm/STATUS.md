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
**Local play is the default (Martin, 2026-11-05).** Every practice match against a bot plays in the browser when the
source hashes agree, the server match the fallback as before; `?local=0` plays it on the server, for debugging. Why: a
turn without a round trip, the bot on the player's own device instead of the shared server CPU, and no connection
needed during play. Its three costs are accepted: about 600 KB to download for an Expert match, a match lost on reload,
and a bot's hand the player could read in a practice match. `web/test/localplay.test.mjs` proves it with no human:
from home with no flag, a match against the bot played to its end by clicks on the game screen, no match socket and no
request a move, then in the history; and with the hashes made to differ, the same match on the server, in the history
too. A test server keeps no replays, so the replay of a browser's log is checked in `test_web_local.py`.

3. **The client** (done). Home's Play against a bot starts the match in the browser
   (`static/local/match.js`): `/api/local/setup` gives the decks, the seats and the bot's spec; the client holds the
   game, feeds the same game screen the views the server would send (the engine's part from the wasm `view`, the
   match's part, seats, move history and numbered events, built the way `match.py` builds them), takes the screen's
   messages in place of the socket (act, played, concede, rematch), and the bot thinks in a Web Worker
   (`static/local/worker.js`) at the server's pace (it waits for the screen to play its last move out, then the same
   beat; after 20 s the Easy bot's move is played, as on the server). When the game ends the log goes to
   `/api/local/match`: the server replays it through a real `Match` (`web/local.py`), seed and first player as the
   browser had them, every action validated by the Python engine, so it is saved as any match is (game log, history,
   replay); a log the engine refuses is refused whole. A log that can't be sent (offline) waits in localStorage and goes
   with the next match. No socket and no request a move (`web/test/local.test.mjs` checks it). Without the flag, or
   when the hashes differ, nothing changes: the match plays on the server.
   Not done: a local match lives in the page (a reload loses it); offline play needs the page and the art already
   loaded; the player's browser holds the whole game, the bot's hand included, so a local practice match can be read
   or edited by its player (the server checks only that the moves were legal: fine for practice, not for anything ranked).
4. **Numbers** (2026-11-05, a cloud container: 4 cores of a 2.8 GHz Xeon, headless Chromium 153; Martin's laptop will
   differ). `tools/engine_rs/wasm_bench.py` then `wasm_bench.mjs`:
   - **Size:** the wasm is 1.47 MB, 477 KB gzipped, 354 KB as the brotli copy the server sends over HTTPS
     (`ak_engine_bg.wasm.br`; plain HTTP, localhost, gets the 1.47 MB). wasm-opt would take it to 1.27 MB raw and
     458 KB gzipped: not worth requiring. A match also fetches the engine doc (76 KB of JSON, the cards) and the
     Expert's evaluator with its setup (171 KB), both uncompressed: about 600 KB in all for an Expert match.
   - **Load:** in a fresh browser from localhost, fetch and compile 39 ms, the engine ready in 68 ms. Over a real
     connection add the download of those 600 KB (half a second at 10 Mbit/s).
   - **The Expert's time per move:** 141 positions from the 40 newest human games, each chosen by a fresh bot. On the
     server's engine (the Rust module the server's bots run, one core): median 384 ms, mean 602 ms, slowest 4.7 s. In
     the browser (a Web Worker): median 516 ms, mean 817 ms, slowest 6.4 s. The browser is 1.36x slower, and chose the
     same move in 141 of 141 positions (none reached the 8 s deepening budget on either side). Without the budget, the
     same work: 1.35x. So the Expert ships locally.
   - **Normal:** median 1 ms on both, mean 8 ms against 6 ms (1.44x), the same move 141 of 141.
   - **A move of the player's:** the engine's part (apply and view) is 0.5 ms in the browser; on the server act and view
     take 0.4 ms in Python. The rest of a move on screen is the drawing, the same either way (about 13 ms here). What
     local play removes is the network round trip a move and the wait for a shared server CPU, not engine time.

## Source hash

`engine_rs/build.rs` embeds a hash of the crate's game sources, everything but the glue (`src/py.rs`, `src/wasm.rs`)
and the timing binary (`tools/engine_rs/wasm_hash.py` computes the same); `ak_engine.source_hash()` on the server and
`sourceHash()` in the browser. The client plays locally only when the two agree, else it plays the match on the server
as today: a wasm built from other engine sources than the server's never plays a different game. Rebuild with
`engine_rs/wasm.sh` after any change under `engine_rs/` and commit `static/wasm/` with it; until then `?local=1`
quietly plays on the server.

**The build is committed, not built on each machine** (`static/wasm/`: `ak_engine.js`, `ak_engine_bg.wasm`, its brotli
copy, `manifest.json`). Why: the Fly image serves the client's static files from the commit and builds no wasm (its
Dockerfile stays as it is), and the Windows PC has no Rust toolchain. The manifest names the source hash the build plays
and, for people, the engine_rs commit it was built from (`engine_rs_commit`, `dirty` when built from uncommitted
changes). `animal_kingdom/tests/test_wasm_build.py` fails when the sources under `engine_rs/` no longer give the
manifest's hash, so a Rust change without a rebuild shows in the fast tier (it skips where there are no Rust sources:
the Fly image's test stage). Two of the local-match browser tests (`web/test/local.test.mjs`) need the server's engine
too, the venv's `ak_engine`, built from the same sources: when it isn't (a venv built from main has no source hash, the
cause of the two 20 s timeouts on the Mac on 0ee7abe), they skip and say how to rebuild it
(`cd engine_rs && ../.venv/bin/maturin develop --release`); the third checks the fallback to the server and always runs.

## Set up (once per machine)

`rustup target add wasm32-unknown-unknown`, then `cargo install wasm-bindgen-cli --version 0.2.130` (the version in
`engine_rs/Cargo.lock`). wasm-opt (binaryen) is optional: `wasm.sh` runs it when it is on the path.
