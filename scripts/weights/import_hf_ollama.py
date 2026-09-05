#!/usr/bin/env python3
"""Download a Hub GGUF that Ollama does not ship, then `ollama create`.

  PYTHONPATH=src python3 scripts/weights/import_hf_ollama.py --list
  PYTHONPATH=src python3 scripts/weights/import_hf_ollama.py --name opencoder
  PYTHONPATH=src python3 scripts/weights/import_hf_ollama.py --name swe-agent-lm
  PYTHONPATH=src python3 scripts/weights/import_hf_ollama.py --all

Then:

  python-vibe --model opencoder:8b run "add a function clamp and a unit test"
  python-vibe --model swe-agent-lm:7b run "add a function clamp and a unit test"

Default stays llama3.1:8b. These tags are a measure lane, not a switch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.hf_ollama import IMPORTS, import_many, names  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--name", choices=(*names(), "all"))
    parser.add_argument("--all", action="store_true", help="import every catalog tag")
    parser.add_argument("--quant", default=None, help="GGUF quant, default Q4_K_M")
    parser.add_argument(
        "--no-create",
        action="store_true",
        help="download only; skip ollama create",
    )
    args = parser.parse_args()
    if args.list or (args.name is None and not args.all):
        for key in names():
            spec = IMPORTS[key]
            print(
                f"{spec.key}\t{spec.ollama_tag}\t"
                f"{spec.gguf_repo}\t~{spec.about_gb}GB\t{spec.license}"
            )
        if args.name is None and not args.all:
            return
    keys = names() if args.all or args.name == "all" else [args.name]
    for spec, gguf in import_many(
        keys, quant=args.quant, create=not args.no_create
    ):
        print(spec.ollama_tag, gguf)
        if not args.no_create:
            print("python-vibe --model", spec.ollama_tag, "run …")


if __name__ == "__main__":
    main()
