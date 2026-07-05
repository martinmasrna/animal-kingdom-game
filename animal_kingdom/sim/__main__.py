"""Compatibility entry point for the unified balance simulation CLI.

``./report`` is the canonical command. This module preserves existing
``python -m animal_kingdom.sim --games ...`` invocations while delegating all parsing,
simulation, progress, and output behavior to the same implementation.
"""

from __future__ import annotations

import sys
from typing import Sequence

from .report import main as unified_main


def main(argv: Sequence[str] | None = None) -> None:
    unified_main(argv, default_format="files")


if __name__ == "__main__":
    main(sys.argv[1:])
