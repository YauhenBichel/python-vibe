#!/usr/bin/env python3
"""Upload fused weights (or adapters) to https://huggingface.co/YauhenBichel."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.huggingface_store import push_card, push_folder, require_token  # noqa: E402
from finetune.models import SPECS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=sorted(SPECS))
    parser.add_argument(
        "--what",
        choices=("fused", "adapters", "card"),
        default="fused",
        help=(
            "fused is the big artifact; adapters are the small LoRA files; "
            "card uploads only README.md and leaves the weights alone"
        ),
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="create/update a public repo (default is private)",
    )
    args = parser.parse_args()
    spec = SPECS[args.model]
    if args.what == "card":
        print(push_card(spec, token=require_token()))
        return
    if args.what == "adapters":
        from finetune.huggingface_store import stage_adapter_bundle

        folder = stage_adapter_bundle(spec)
    else:
        folder = spec.fused_path
    url = push_folder(spec, folder, private=not args.public, token=require_token())
    print(url)


if __name__ == "__main__":
    main()
