#!/usr/bin/env python3
"""Measure python-vibe on tasks of increasing size, and check the result.

Tiers exist so improvement can be seen where it happens. A change that
helps one-file work and not two-file work should show exactly that.

  tier 1  one function, one existing file, no test
  tier 2  one function and a test for it, two files
  tier 3  a new module, a function, and a test that imports it

Each case runs the code afterwards. "Worked" means the function does the
job, not that a file was written.

  python scripts/bench.py                 # every tier, needs Ollama
  python scripts/bench.py --tier 1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from harness import Agent, AgentOptions  # noqa: E402

LOADER = '''
import importlib.util, pathlib
def load(name):
    for path in sorted(pathlib.Path(".").rglob("*.py")):
        if "__init__" in path.name or path.name.startswith("test"):
            continue
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception:
            continue
        if callable(getattr(module, name, None)):
            return getattr(module, name)
    raise AssertionError(name + " not found in any module")
'''

APP = (
    '"""Order arithmetic."""\n\n\n'
    "def compute_total(prices: list[int]) -> int:\n"
    "    return sum(prices)\n"
)
TEST = (
    "import unittest\n\n"
    "from src.orders import compute_total\n\n\n"
    "class TestOrders(unittest.TestCase):\n"
    "    def test_compute_total_sums_the_prices(self) -> None:\n"
    "        prices = [1, 2]\n"
    "        got = compute_total(prices)\n"
    "        self.assertEqual(got, 3)\n"
)
BASE = {
    "src/__init__.py": "",
    "src/orders.py": APP,
    "tests/__init__.py": "",
    "tests/test_orders.py": TEST,
}


@dataclass
class Case:
    key: str
    tier: int
    task: str
    check: str
    suite_must_pass: bool = False
    files: dict = field(default_factory=dict)


CASES = [
    Case("double", 1, "add a function double(n) that returns n times two",
         "assert load('double')(4) == 8\n"),
    Case("largest", 1, "add a function largest(values) that returns the biggest value",
         "assert load('largest')([3, 9, 2]) == 9\n"),
    Case("initials", 1,
         "add a function initials(name) that returns the first letter of each word, upper case",
         "got = load('initials')('ada lovelace')\nassert got.upper() == 'AL', got\n"),
    Case("average", 2,
         "add a function average(values) that returns the mean, and a unit test",
         "assert load('average')([2, 4]) == 3\n", suite_must_pass=True),
    Case("clamp", 2,
         "add a function clamp(value, low, high) that keeps a value inside a range, and a unit test",
         "f = load('clamp')\nassert f(5, 1, 3) == 3 and f(0, 1, 3) == 1\n",
         suite_must_pass=True),
    Case("slugify", 3,
         "create a new module with a function slugify(text) that lowercases and joins words with a dash, and a unit test for it",
         "assert load('slugify')('Hello There') == 'hello-there'\n",
         suite_must_pass=True),
    Case("wordcount", 3,
         "create a new module with a function word_count(text) that counts words, and a unit test for it",
         "assert load('word_count')('a b c') == 3\n", suite_must_pass=True),
]


def run(case: Case, model: str, steps: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        for rel, body in {**BASE, **case.files}.items():
            dest = project / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(body, encoding="utf-8")
        started = time.time()
        try:
            result = Agent(
                AgentOptions(project=project, task=case.task, model=model, steps=steps)
            ).run()
        except Exception as exc:  # noqa: BLE001
            return {"case": case.key, "tier": case.tier, "worked": "error",
                    "why": f"{type(exc).__name__}: {exc}"}
        proc = subprocess.run([sys.executable, "-c", LOADER + case.check], cwd=project,
                              capture_output=True, text=True, timeout=60, check=False)
        worked = proc.returncode == 0
        why = ""
        if not worked:
            tail = (proc.stderr or proc.stdout).strip().splitlines()
            why = tail[-1][:60] if tail else "check failed"
        suite = ""
        if case.suite_must_pass:
            run_tests = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                cwd=project, capture_output=True, text=True, timeout=90, check=False,
            )
            suite = "green" if run_tests.returncode == 0 else "red"
            if worked and suite == "red":
                worked, why = False, "suite red"
        return {"case": case.key, "tier": case.tier,
                "worked": "yes" if worked else "no", "why": why, "suite": suite,
                "steps": len(result.steps), "writes": list(result.writes),
                "seconds": round(time.time() - started, 1)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=int, action="append", default=[])
    parser.add_argument("--model", default=AgentOptions(project=Path(".")).model)
    parser.add_argument("--steps", type=int, default=10)
    args = parser.parse_args()
    cases = [c for c in CASES if not args.tier or c.tier in args.tier]
    rows = [run(case, args.model, args.steps) for case in cases]
    for row in rows:
        print(json.dumps(row), flush=True)
    for tier in sorted({row["tier"] for row in rows}):
        same = [r for r in rows if r["tier"] == tier]
        ok = sum(1 for r in same if r["worked"] == "yes")
        print(f"tier {tier}: {ok}/{len(same)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
