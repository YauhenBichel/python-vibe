#!/usr/bin/env python3
"""Fuse LoRA adapters and write an Ollama Modelfile for the small cloud bases."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.models import SPECS  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=sorted(SPECS))
    parser.add_argument(
        "--ollama",
        action="store_true",
        help="ollama create <name> from the Modelfile (system prompt on the tiny base)",
    )
    parser.add_argument(
        "--hf",
        action="store_true",
        help="upload fused weights to HF_REPO or HF_USER/<slug> (never implied official account)",
    )
    parser.add_argument(
        "--public",
        action="store_true",
        help="with --hf, make the Hugging Face repo public",
    )
    args = parser.parse_args()
    spec = SPECS[args.model]

    fuse = shutil.which("mlx_lm.fuse")
    if not fuse:
        sys.exit("mlx_lm.fuse not on PATH")

    spec.fused_path.mkdir(parents=True, exist_ok=True)
    cmd = [
        fuse,
        "--model",
        spec.mlx_base,
        "--adapter-path",
        str(spec.adapter_path),
        "--save-path",
        str(spec.fused_path),
    ]
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=ROOT)

    modelfile = ROOT / "modelfiles" / args.model
    modelfile.parent.mkdir(parents=True, exist_ok=True)
    modelfile.write_text(
        f"FROM {spec.ollama_base}\n\nSYSTEM \"\"\"\n{spec.system.strip()}\n\"\"\"\n",
        encoding="utf-8",
    )
    print("wrote", modelfile)

    if args.ollama:
        ollama = shutil.which("ollama")
        if not ollama:
            sys.exit("ollama not on PATH")
        subprocess.check_call([ollama, "create", args.model, "-f", str(modelfile)])

    if args.hf:
        from finetune.huggingface_store import push_folder, require_token

        url = push_folder(
            spec, spec.fused_path, private=not args.public, token=require_token()
        )
        print(url)


if __name__ == "__main__":
    main()
