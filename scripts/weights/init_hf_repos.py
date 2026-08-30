#!/usr/bin/env python3
"""Create empty model repos on https://huggingface.co/YauhenBichel with cards."""

from __future__ import annotations

import argparse
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.huggingface_store import push_folder, require_token, write_card  # noqa: E402
from finetune.models import SPECS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", action="store_true")
    args = parser.parse_args()
    token = require_token()
    for spec in SPECS.values():
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            write_card(spec, dest)
            url = push_folder(spec, dest, private=not args.public, token=token)
            print(url)


if __name__ == "__main__":
    main()
