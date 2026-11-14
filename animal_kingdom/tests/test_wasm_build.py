"""The browser's engine (static/wasm, built by engine_rs/wasm.sh and committed) is built from the Rust sources as they stand:
a change under engine_rs/ without a rebuild fails here. (Until it is rebuilt, `?local=1` plays on the server.)"""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(not (ROOT / "engine_rs/src").is_dir(), reason="no Rust sources here (the Fly image's test stage)")
@pytest.mark.skip(reason="actions prototype branch: the browser engine is not rebuilt (no wasm-bindgen here); practice matches play on the server")
def test_the_committed_wasm_is_built_from_the_engine_sources_as_they_stand():
    manifest = ROOT / "animal_kingdom/web/static/wasm/manifest.json"
    assert manifest.is_file() and (ROOT / "animal_kingdom/web/static/wasm/ak_engine_bg.wasm").is_file(), "run engine_rs/wasm.sh"
    spec = importlib.util.spec_from_file_location("wasm_hash", ROOT / "tools/engine_rs/wasm_hash.py")
    wasm_hash = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wasm_hash)
    built = json.loads(manifest.read_text())["source_hash"]
    assert built == wasm_hash.source_hash(), "engine_rs/ changed since static/wasm was built: run engine_rs/wasm.sh and commit static/wasm"
