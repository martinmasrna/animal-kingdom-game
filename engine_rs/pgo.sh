#!/usr/bin/env bash
# Profile-guided build of the Python module (2026-10-23: about 9% off the Expert's move, no code change). An instrumented
# timing binary plays a few Expert games across deck pairs, the profiles are merged, and `maturin develop --release` builds
# the venv's `ak_engine` with them. The profile is local (engine_rs/target/pgo/, never committed): the Fly image builds
# without it, and it must be regenerated after a rustc upgrade (the profile format follows rustc's LLVM).
#   engine_rs/pgo.sh            from the repo root, with the venv built (../.venv/bin/maturin, Homebrew llvm for llvm-profdata)
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(cd "$here/.." && pwd)"
P="$here/target/pgo"; D="$repo/animal_kingdom/data"
PROFDATA="$(ls /opt/homebrew/opt/llvm/bin/llvm-profdata 2>/dev/null || command -v llvm-profdata || true)"
[[ -n "$PROFDATA" ]] || { echo "llvm-profdata not found (brew install llvm)"; exit 1; }
rm -rf "$P/data"; mkdir -p "$P/data" "$P/decks"
cfg="$P/config.json"
(cd "$repo" && .venv/bin/python -c "import dataclasses, json; from animal_kingdom.engine.config import Config; print(json.dumps(dataclasses.asdict(Config.default())))" > "$cfg")
for d in cats fish removal colony hoofed giants; do
  (cd "$repo" && .venv/bin/python -c "from animal_kingdom.web.match import deck_list; print(','.join(deck_list('$d')))" > "$P/decks/$d.txt")
done
EX="$(cd "$repo" && .venv/bin/python -c 'import re; from animal_kingdom.web.match import EXPERT; print(re.sub(r"referee_learned:eval=[^,]*,", "referee:", EXPERT).replace("time_budget=8", "time_budget=0"))')"
echo "instrumented build"
(cd "$here" && RUSTFLAGS="-Cprofile-generate=$P/data" CARGO_TARGET_DIR="$P/target-gen" cargo build --release --no-default-features --bin bench 2>&1 | tail -1)
B="$P/target-gen/release/bench"
for pair in "cats fish" "removal colony" "hoofed giants" "colony cats" "giants removal" "fish hoofed"; do
  read -r a b <<< "$pair"
  "$B" "$D/cards.json" "$D/maps.json" "$cfg" "$(cat "$P/decks/$a.txt")" "$(cat "$P/decks/$b.txt")" 31 "$EX" "$EX" 1 | tail -1
done
"$PROFDATA" merge -o "$P/merged.profdata" "$P/data"
echo "profile: $(du -h "$P/merged.profdata" | cut -f1)"
echo "building the venv module with the profile"
(cd "$here" && RUSTFLAGS="-Cprofile-use=$P/merged.profdata -Cllvm-args=-pgo-warn-missing-function" ../.venv/bin/maturin develop --release 2>&1 | grep -v "^warning" | tail -2)
echo "done: ak_engine in the venv is profile-guided; rerun the oracles (tools/engine_rs) before anything uses it"
