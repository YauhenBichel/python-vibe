#!/usr/bin/env python3
"""Name an Ollama model that is the everyday brain, not the 0.5B base.

Stand-in (this week): FROM llama3.1:8b + agent system prompt.
After you train python-vibe-8b and fuse: pass --from-gguf or --from-fused.

  ollama pull llama3.1:8b
  PYTHONPATH=src python scripts/weights/export_ollama.py
  PYTHONPATH=src python scripts/weights/export_ollama.py --create

Linux GGUF of a fused MLX folder needs llama.cpp convert (not bundled):

  python convert_hf_to_gguf.py fused/python-vibe-8b --outfile fused/everyday.gguf
  PYTHONPATH=src python scripts/weights/export_ollama.py --from-gguf fused/everyday.gguf --create
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.agent_system import AGENT_SYSTEM  # noqa: E402
from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA  # noqa: E402


def write_modelfile(*, base: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f"FROM {base}\n\nSYSTEM \"\"\"\n{AGENT_SYSTEM.strip()}\n\"\"\"\n",
        encoding="utf-8",
    )
    return dest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-base", default=DEFAULT_EVERYDAY_OLLAMA)
    parser.add_argument("--from-gguf", type=Path)
    parser.add_argument("--from-fused", type=Path)
    parser.add_argument("--name", default="python-vibe-everyday")
    parser.add_argument("--create", action="store_true", help="ollama create")
    args = parser.parse_args()
    if args.from_gguf:
        base = str(args.from_gguf.expanduser().resolve())
        if not Path(base).is_file():
            sys.exit(f"no GGUF: {base}")
    elif args.from_fused:
        base = str(args.from_fused.expanduser().resolve())
        if not Path(base).is_dir():
            sys.exit(f"no fused folder: {base}")
    else:
        base = args.from_base
    dest = ROOT / "modelfiles" / "everyday"
    write_modelfile(base=base, dest=dest)
    print("wrote", dest, "FROM", base)
    if args.create:
        ollama = shutil.which("ollama")
        if not ollama:
            sys.exit("ollama not on PATH")
        subprocess.check_call([ollama, "create", args.name, "-f", str(dest)])
        print("ollama run", args.name)


if __name__ == "__main__":
    main()
