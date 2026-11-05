#!/bin/sh
# The browser build of the engine and bots: the crate for wasm32 without the Python glue (feature `wasm`, profile
# `wasm`), bound by wasm-bindgen into an ES module the client loads (static/wasm/ak_engine.js + ak_engine_bg.wasm),
# shrunk by wasm-opt when it is installed, with a brotli copy beside it (ak_engine_bg.wasm.br: the server sends it to a
# browser that takes br, about a quarter of the bytes; web/test/wasm.test.mjs holds it equal to the .wasm). Writes static/wasm/manifest.json with the hash of the sources it was built
# from (tools/engine_rs/wasm_hash.py), which the client checks before playing locally.
#
# Once: rustup target add wasm32-unknown-unknown && cargo install wasm-bindgen-cli --version <the lock's wasm-bindgen>
# Run from anywhere: engine_rs/wasm.sh
set -e
cd "$(dirname "$0")"
OUT=../animal_kingdom/web/static/wasm
cargo build --profile wasm --target wasm32-unknown-unknown --no-default-features --features wasm --lib
wasm-bindgen --target web --no-typescript --out-dir "$OUT" target/wasm32-unknown-unknown/wasm/ak_engine.wasm
if command -v wasm-opt >/dev/null 2>&1; then
    wasm-opt -O3 --enable-bulk-memory --enable-nontrapping-float-to-int --enable-sign-ext --enable-mutable-globals \
        "$OUT/ak_engine_bg.wasm" -o "$OUT/ak_engine_bg.wasm"
fi
node -e "const z = require('zlib'), f = require('fs'), p = process.argv[1];
  f.writeFileSync(p + '.br', z.brotliCompressSync(f.readFileSync(p), { params: { [z.constants.BROTLI_PARAM_QUALITY]: 11 } }))" "$OUT/ak_engine_bg.wasm"
python3 ../tools/engine_rs/wasm_hash.py --write "$OUT/manifest.json"
ls -l "$OUT"
