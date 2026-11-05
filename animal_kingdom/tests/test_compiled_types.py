"""The live image compiles the engine and the search with mypyc (deploy/Dockerfile), which refuses code mypy refuses: a
merge that type-checks nowhere else fails the deploy after the build, twice, on Fly (2026-11-05: an unannotated dict in
turn_search.py). This checks the same files the same way, in under a second, before anything ships."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def compiled_files() -> list[str]:
    step = re.search(r"RUN python -m mypyc (.*?)&& rm -rf build", (ROOT / "deploy/Dockerfile").read_text(), re.S).group(1)
    return [w for w in step.replace("\\", " ").split() if w.endswith(".py")]


def test_the_compiled_modules_type_check_as_mypyc_needs():
    pytest.importorskip("mypy")
    files = compiled_files()
    assert len(files) >= 10, "the Dockerfile's mypyc step was not found"
    r = subprocess.run([sys.executable, "-m", "mypy", "--ignore-missing-imports", "--no-incremental", *files],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-3000:]
