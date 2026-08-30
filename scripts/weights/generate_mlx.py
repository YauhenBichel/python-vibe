#!/usr/bin/env python3
"""Ask the python-vibe LoRA on MLX, then run PythonVibeGuard.

Needs Homebrew Python 3.13 + mlx-lm (not 3.14). Adapters stay gitignored.

  PYTHONPATH=src python scripts/weights/generate_mlx.py "jsonl reader that skips bad lines"
  PYTHONPATH=src python scripts/weights/generate_mlx.py "jsonl reader" --best
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.huggingface_store import BEST_ADAPTER, ensure_adapters  # noqa: E402
from finetune.models import SPECS  # noqa: E402
from harness.guard.fallbacks import PYTHON_VIBE_FALLBACK  # noqa: E402
from harness.guard.python_vibe import PythonVibeGuard  # noqa: E402
from harness.guard.run import complete  # noqa: E402

BEST_STEP = "0000100_adapters.safetensors"


def _stage_best(adapter_dir: Path) -> Path:
    ckpt = adapter_dir / BEST_STEP
    if not ckpt.is_file():
        sys.exit(f"no best checkpoint: {ckpt}")
    staging = adapter_dir.parent / "python-vibe-100"
    staging.mkdir(parents=True, exist_ok=True)
    dest = staging / "adapters.safetensors"
    cfg = staging / "adapter_config.json"
    src_cfg = adapter_dir / "adapter_config.json"
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    dest.symlink_to(ckpt.resolve())
    if src_cfg.is_file():
        if cfg.is_symlink() or cfg.is_file():
            cfg.unlink()
        cfg.symlink_to(src_cfg.resolve())
    return staging


def _adapter_dir(spec_path: Path, best: bool) -> Path:
    if not spec_path.is_dir():
        sys.exit(
            f"no adapters at {spec_path}. Train first or copy "
            "adapters/python-vibe from the MLX run."
        )
    if best:
        return _stage_best(spec_path)
    if not (spec_path / "adapters.safetensors").is_file():
        sys.exit(f"no adapters.safetensors in {spec_path}")
    return spec_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument(
        "--best",
        action="store_true",
        help=f"use {BEST_STEP} (val was best around step 100)",
    )
    parser.add_argument("--max-tokens", type=int, default=400)
    args = parser.parse_args()

    spec = SPECS["python-vibe"]
    local = ensure_adapters(spec)
    if args.best and (local / BEST_ADAPTER).is_file():
        adapter = _adapter_dir(local, True)
    else:
        adapter = _adapter_dir(local, False)

    try:
        from mlx_lm import generate, load
    except ImportError:
        sys.exit("mlx_lm missing. Use the Python 3.13 venv from requirements.txt")

    model, tokenizer = load(spec.mlx_base, adapter_path=str(adapter))

    def generate_once(prompt: str) -> str:
        messages = [
            {"role": "system", "content": spec.system},
            {"role": "user", "content": prompt},
        ]
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        return generate(model, tokenizer, prompt=text, max_tokens=args.max_tokens)

    outcome = complete(generate_once, PythonVibeGuard(), PYTHON_VIBE_FALLBACK, args.prompt)
    print(outcome.output or "")
    print(
        json.dumps(
            {
                "surface": "mlx-lora",
                "adapter": str(adapter),
                "verdict": outcome.verdict,
                "fallback": outcome.fallback,
                "findings": [f.rule_id for f in outcome.findings],
            }
        ),
        file=sys.stderr,
    )
    if not outcome.output:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
