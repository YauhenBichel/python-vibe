#!/usr/bin/env python3
"""Local gate that matches CI: unit tests + harness smoke.

  PYTHONPATH=src python scripts/measure/validate.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    tests = subprocess.call(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
        cwd=ROOT,
        env=env,
    )
    if tests != 0:
        sys.exit(tests)
    smoke = subprocess.call(
        [sys.executable, str(ROOT / "scripts" / "measure" / "smoke.py")],
        cwd=ROOT,
        env=env,
    )
    if smoke != 0:
        sys.exit(smoke)
    gate = subprocess.call(
        [sys.executable, str(ROOT / "scripts" / "measure" / "eval_everyday.py")],
        cwd=ROOT,
        env=env,
    )
    sys.exit(gate)


if __name__ == "__main__":
    main()
