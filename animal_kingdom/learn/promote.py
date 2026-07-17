"""python -m animal_kingdom.learn.promote: publish a training checkpoint as a weight artifact.

Reads a `learn/train.py` run directory's `checkpoint.json` (weights + run_key) and writes it
out as a `bots.learned_eval.LinearEval` JSON artifact - conventionally
`animal_kingdom/data/learned/<name>.json`, loadable by name via `load_eval("<name>")` /
`--eval=<name>` on any `*_learned` bot kind. This is real code, not a file copy: the
checkpoint stores the raw `[weights..., bias]` vector and the run's `run_key` (config +
git rev + schema hash at *training* time); promotion splits out the bias, re-derives the
CURRENT `feature_schema_hash` (validated by `LinearEval` itself), and stamps fresh provenance
(source checkpoint path, training iteration, training git rev, promotion git rev/timestamp).

Usage:
    python -m animal_kingdom.learn.promote results/learn/rung0_v1 \\
        --out animal_kingdom/data/learned/rung0.json --notes "rung0 session-1 sanity run"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import artifacts


def promote(run_dir: Path, dest_path: Path, *, notes: str = "") -> "artifacts.LinearEval":
    ckpt_path = run_dir / "checkpoint.json"
    if not ckpt_path.exists():
        raise SystemExit(f"no checkpoint at {ckpt_path}")
    saved = json.loads(ckpt_path.read_text())
    run_key = saved["run_key"]
    weights = saved["weights"]
    feature_set = run_key["config"]["feature_set"]

    artifact = artifacts.build_artifact(
        weights[:-1], feature_set, bias=weights[-1], run_id=run_dir.name, notes=notes,
        extra_provenance={
            "source_checkpoint": str(ckpt_path),
            "training_iteration": saved["iteration"],
            "training_git_rev": run_key.get("git_rev"),
            "training_config": run_key["config"],
        },
    )
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    artifact.save(str(dest_path))
    return artifact


def main(argv: Optional[Sequence[str]] = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("run_dir", type=Path, help="a learn/train.py --out directory")
    p.add_argument("--out", type=Path, required=True,
                   help="destination artifact path, e.g. animal_kingdom/data/learned/rung0.json")
    p.add_argument("--notes", default="", help="free-form provenance note")
    args = p.parse_args(argv)

    artifact = promote(args.run_dir, args.out, notes=args.notes)
    print(f"promoted {args.run_dir}/checkpoint.json (iteration "
          f"{artifact.provenance['training_iteration']}) -> {args.out}", file=sys.stderr)
    print(f"feature_set={artifact.feature_set}  ||w||={sum(w * w for w in artifact.weights) ** 0.5:.4f}  "
          f"bias={artifact.bias:.4f}", file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1:])
