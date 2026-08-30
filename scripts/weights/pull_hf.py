#!/usr/bin/env python3
"""Download public weights from https://huggingface.co/YauhenBichel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.huggingface_store import ensure_adapters, optional_token, pull_folder  # noqa: E402
from finetune.models import SPECS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=sorted(SPECS))
    parser.add_argument(
        "--what",
        choices=("adapters", "fused"),
        default="adapters",
    )
    args = parser.parse_args()
    spec = SPECS[args.model]
    if args.what == "adapters":
        dest = ensure_adapters(spec)
    else:
        dest = pull_folder(spec, spec.fused_path, token=optional_token())
    print(dest)


if __name__ == "__main__":
    main()
