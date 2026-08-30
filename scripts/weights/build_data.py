#!/usr/bin/env python3
"""Build mlx-lm JSONL splits from the python-vibe seed pairs."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.paths import DATA_ROOT  # noqa: E402
from finetune.python_vibe import all_pairs as python_pairs  # noqa: E402
from finetune.splits import write_splits  # noqa: E402
from finetune.systems import PYTHON_VIBE_SYSTEM  # noqa: E402


def main() -> None:
    py = python_pairs()
    counts = write_splits(py, PYTHON_VIBE_SYSTEM, DATA_ROOT / "python-vibe")
    print("python-vibe", counts, "from", len(py), "pairs")
    print("wrote", DATA_ROOT)


if __name__ == "__main__":
    main()
