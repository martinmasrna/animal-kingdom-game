#!/bin/sh
# The bot benchmark: builds the Rust binary if the source changed, then runs it from the game folder.
#   tools/bot_bench/bench.sh run --x turn:budget=20000 --y greedy --seeds 20 --name my-run
# See tools/bot_bench/README.md.
set -e
cd "$(dirname "$0")/../.."
(cd engine_rs && PATH="/opt/homebrew/bin:$PATH" cargo build --release --no-default-features --bin bot_bench --quiet)
exec engine_rs/target/release/bot_bench "$@"
