"""Weight-artifact construction: wraps `bots.learned_eval.LinearEval` with the provenance
(git revision, wall-clock timestamp, training run id, free-form notes) every tracked artifact
under `animal_kingdom/data/learned/` carries.

This module is about the *published* weight artifact only - the thing
`bots.learned_eval.load_eval()` reads. Per-run training checkpoints/manifests/curves
(`results/learn/<run_id>/`) are a separate, run-level concern owned by `learn/train.py`
(mirrors `sim/benchmark_set.py`'s run-key checkpoint/resume convention, not this module).
"""

from __future__ import annotations

import subprocess
import time
from typing import Any, Mapping, Optional, Sequence

from ..bots.learned_eval import LinearEval


def git_rev() -> Optional[str]:
    """The current commit hash, or None if not in a git checkout / git isn't on PATH."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=True,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def build_artifact(
    weights: Sequence[float],
    feature_set: str,
    *,
    bias: float = 0.0,
    run_id: Optional[str] = None,
    notes: str = "",
    extra_provenance: Optional[Mapping[str, Any]] = None,
) -> LinearEval:
    """A `LinearEval` with standard provenance stamped on. Doesn't write anything - call
    `.save(path)` on the result, or use `promote_checkpoint` below."""
    provenance: dict[str, Any] = {
        "git_rev": git_rev(),
        "created_unix": time.time(),
        "run_id": run_id,
        "notes": notes,
    }
    if extra_provenance:
        provenance.update(extra_provenance)
    return LinearEval(
        feature_set=feature_set,
        weights=tuple(float(w) for w in weights),
        bias=float(bias),
        provenance=provenance,
    )


def promote_checkpoint(
    weights: Sequence[float],
    feature_set: str,
    dest_path: str,
    *,
    bias: float = 0.0,
    run_id: Optional[str] = None,
    notes: str = "",
    extra_provenance: Optional[Mapping[str, Any]] = None,
) -> LinearEval:
    """Build a provenanced artifact from trained weights and write it to `dest_path`
    (conventionally `animal_kingdom/data/learned/<name>.json`). Returns the artifact so a
    caller can log/print its summary without re-reading the file."""
    artifact = build_artifact(
        weights, feature_set, bias=bias, run_id=run_id, notes=notes,
        extra_provenance=extra_provenance,
    )
    artifact.save(dest_path)
    return artifact
