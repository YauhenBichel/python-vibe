#!/usr/bin/env python3
"""Write data/agent-loop JSONL from seed tool traces (not 2k live logs).

  PYTHONPATH=src python scripts/weights/build_agent_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.agent_traces import all_pairs, system_prompt  # noqa: E402
from finetune.splits import write_splits  # noqa: E402


def load_extra(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        return []
    pairs: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        user = row.get("user") or row.get("prompt")
        assistant = row.get("assistant") or row.get("draft")
        if user and assistant:
            pairs.append((str(user), str(assistant)))
    return pairs


def main() -> None:
    dest = ROOT / "data" / "agent-loop"
    extra = dest / "extra.jsonl"
    pairs = all_pairs() + load_extra(extra)
    counts = write_splits(pairs, system_prompt(), dest)
    print(dest, counts, "extra", extra.is_file())
    print(
        "Seed + optional extra.jsonl (gitignored). "
        "Record with: scripts/run/agent.py --record data/agent-loop/extra.jsonl"
    )


if __name__ == "__main__":
    main()
