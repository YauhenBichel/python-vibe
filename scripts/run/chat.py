#!/usr/bin/env python3
"""Ask python-vibe through its harness (Ollama generate → guard → fallback)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.models import SPECS  # noqa: E402
from harness.guard.fallbacks import PYTHON_VIBE_FALLBACK  # noqa: E402
from harness.model.ollama_generate import OllamaGenerate  # noqa: E402
from harness.guard.python_vibe import PythonVibeGuard  # noqa: E402
from harness.guard.run import complete  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    args = parser.parse_args()
    spec = SPECS["python-vibe"]
    generate = OllamaGenerate(spec.ollama_base, spec.system)
    outcome = complete(generate, PythonVibeGuard(), PYTHON_VIBE_FALLBACK, args.prompt)
    print(outcome.output or "")
    print(
        json.dumps(
            {
                "verdict": outcome.verdict,
                "fallback": outcome.fallback,
                "ruleset": outcome.ruleset_version,
                "findings": [f.rule_id for f in outcome.findings],
            }
        ),
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
