"""The Rust engine's source hash, as engine_rs/build.rs embeds it (AK_SOURCE_HASH): FNV-1a 64 over Cargo.toml and every
src/**/*.rs in path order but the glue (src/py.rs, src/wasm.rs) and the timing binary (src/bin/). engine_rs/wasm.sh writes it into static/wasm/manifest.json beside the browser build.

    python3 tools/engine_rs/wasm_hash.py              # prints the hash of the sources as they stand
    python3 tools/engine_rs/wasm_hash.py --write FILE  # writes {"source_hash", "engine_rs_commit", "dirty"} to FILE

The hash says which game a build plays; the commit (the last one that touched engine_rs/ when it was built, with
"dirty" when engine_rs/ had uncommitted changes, as when the build is committed with them) is for people.
animal_kingdom/tests/test_wasm_build.py fails when the sources no longer give the manifest's hash.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "engine_rs"


def source_hash(root: Path = ROOT) -> str:
    rel = ["Cargo.toml"] + sorted(r for r in (p.relative_to(root).as_posix() for p in (root / "src").rglob("*.rs"))
                                  if r not in ("src/py.rs", "src/wasm.rs") and not r.startswith("src/bin/"))
    h = 0xcbf29ce484222325
    for r in rel:
        for chunk in (r.encode(), b"\0", (root / r).read_bytes().replace(b"\r", b""), b"\0"):
            for x in chunk:
                h = ((h ^ x) * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--write":
        git = lambda *a: subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        Path(sys.argv[2]).write_text(json.dumps({"source_hash": source_hash(), "engine_rs_commit": git("log", "-1", "--format=%H", "--", "."),
                                                 "dirty": bool(git("status", "--porcelain", "--", "."))}) + "\n")
    else:
        print(source_hash())
