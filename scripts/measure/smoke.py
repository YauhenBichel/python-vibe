#!/usr/bin/env python3
"""Prove python-vibe works: harness always, Ollama/MLX only if asked.

  PYTHONPATH=src python scripts/measure/smoke.py
  PYTHONPATH=src python scripts/measure/smoke.py --live
  PYTHONPATH=src python scripts/measure/smoke.py --mlx
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from harness.guard.fallbacks import PYTHON_VIBE_FALLBACK  # noqa: E402
from harness.guard.python_vibe import PythonVibeGuard  # noqa: E402
from harness.paths import venv_python  # noqa: E402
from harness.guard.run import complete  # noqa: E402

PROMPT = "jsonl reader that skips bad lines"


def _harness() -> None:
    guard = PythonVibeGuard()
    ok = "print(1)\n"
    assert guard.check(ok).verdict == "pass", "ordinary draft must pass"
    assert guard.check("   ").verdict == "block", "empty draft must block"
    drafts = iter(["", "from pathlib import Path\nprint(Path('.'))\n"])
    out = complete(lambda _p: next(drafts), guard, PYTHON_VIBE_FALLBACK, PROMPT)
    assert out.output and not out.fallback, out
    print("harness: pass")


def _live() -> None:
    from finetune.models import SPECS
    from harness.model.ollama_generate import OllamaGenerate

    spec = SPECS["python-vibe"]
    generate = OllamaGenerate(spec.ollama_base, spec.system)
    if not generate.healthy():
        sys.exit(f"ollama {generate.host} is down")
    try:
        outcome = complete(generate, PythonVibeGuard(), PYTHON_VIBE_FALLBACK, PROMPT)
    except RuntimeError as exc:
        sys.exit(str(exc))
    print(outcome.output or "")
    print(
        json.dumps(
            {
                "surface": "ollama",
                "model": spec.ollama_base,
                "verdict": outcome.verdict,
                "fallback": outcome.fallback,
                "findings": [f.rule_id for f in outcome.findings],
            }
        ),
        file=sys.stderr,
    )
    if not outcome.output:
        sys.exit("live ollama returned empty output")
    print("live: pass")


def _mlx_python() -> str:
    extra = os.environ.get("MLX_PYTHON", "")
    candidates = [
        sys.executable,
        str(venv_python(ROOT / ".venv")),
        *([extra] if extra else []),
    ]
    for exe in candidates:
        if not Path(exe).is_file():
            continue
        probe = subprocess.run(
            [exe, "-c", "import mlx_lm"], capture_output=True, text=True
        )
        if probe.returncode == 0:
            return exe
    sys.exit("no Python with mlx_lm. Use the Homebrew 3.13 venv from requirements.txt")


def _mlx() -> None:
    script = ROOT / "scripts" / "weights" / "generate_mlx.py"
    cmd = [_mlx_python(), str(script), PROMPT, "--best"]
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    print("+", " ".join(cmd), flush=True)
    raise SystemExit(subprocess.call(cmd, cwd=ROOT, env=env))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="one generate through Ollama + PythonVibeGuard",
    )
    parser.add_argument(
        "--mlx",
        action="store_true",
        help="one generate through the LoRA (MLX) + PythonVibeGuard",
    )
    args = parser.parse_args()
    _harness()
    if args.live:
        _live()
    if args.mlx:
        _mlx()


if __name__ == "__main__":
    main()
