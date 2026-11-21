#!/usr/bin/env bash
# Build the rules engine (the Python module ak_engine) into the repo's venv.
#
#   engine_rs/build.sh             # build
#   engine_rs/build.sh --if-stale  # build only when the module is missing or older than its source; says nothing when fresh
#
# Needs the Rust toolchain (brew install rust, or https://rustup.rs) and maturin in the venv (.venv/bin/pip install maturin).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
venv="$here/../.venv"
py="$venv/bin/python"
[[ -x "$py" ]] || py="$venv/Scripts/python.exe"

if [[ "${1:-}" == "--if-stale" ]]; then
  built="$("$py" -c "import ak_engine; print(ak_engine.__file__)" 2>/dev/null || true)"
  if [[ -n "$built" && -z "$(find "$here/src" "$here/Cargo.toml" "$here/Cargo.lock" -newer "$built" -print -quit 2>/dev/null)" ]]; then
    exit 0
  fi
  echo "building the rules engine (engine_rs/): its source is newer than the built module" >&2
fi

export PATH="$venv/bin:/opt/homebrew/bin:$HOME/.cargo/bin:$PATH"
if ! command -v cargo >/dev/null; then
  echo "the rules engine needs the Rust toolchain to build: brew install rust (or https://rustup.rs), then engine_rs/build.sh" >&2
  exit 1
fi
"$py" -c "import maturin" 2>/dev/null || "$py" -m pip install -q "maturin>=1.5,<2"
cd "$here"
if ! out="$(VIRTUAL_ENV="$venv" "$py" -m maturin develop --release 2>&1)"; then
  echo "$out" | grep -E -A12 "^error" | head -40 >&2
  echo "the rules engine did not build (engine_rs/build.sh)" >&2
  exit 1
fi
