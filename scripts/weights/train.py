#!/usr/bin/env python3
"""Run mlx_lm.lora for python-vibe."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs" / "python-vibe.yaml"
EVERYDAY = ROOT / "configs" / "python-vibe-8b.yaml"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--everyday",
        action="store_true",
        help="train the 7B-class tool-loop LoRA (configs/python-vibe-8b.yaml)",
    )
    parser.add_argument("--iters", type=int, default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="continue from adapters/python-vibe/adapters.safetensors",
    )
    args = parser.parse_args()

    exe = shutil.which("mlx_lm.lora")
    if not exe:
        sys.exit("mlx_lm.lora not on PATH. Create the 3.13 venv and pip install -r requirements.txt")

    config = EVERYDAY if args.everyday else CONFIG
    cmd = [exe, "--config", str(config), "--train"]
    if args.iters is not None:
        cmd.extend(["--iters", str(args.iters)])
    if args.resume:
        adapter = ROOT / "adapters" / "python-vibe" / "adapters.safetensors"
        if not adapter.is_file():
            sys.exit(f"no adapter to resume: {adapter}")
        cmd.extend(["--resume-adapter-file", str(adapter)])
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT)


if __name__ == "__main__":
    main()
