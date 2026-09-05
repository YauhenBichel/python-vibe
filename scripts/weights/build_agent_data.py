#!/usr/bin/env python3
"""Write data/agent-loop JSONL from the seed traces and any recorded runs.

  PYTHONPATH=src python scripts/weights/build_agent_data.py
  PYTHONPATH=src python scripts/weights/build_agent_data.py --from ~/work/other

Runs record their turns to `.python-vibe/traces.jsonl` inside whatever
project they ran in. That is where the training data comes from now, and
for a while it was not where this script looked: it read only
`data/agent-loop/extra.jsonl`, the file the old `--record` flag wrote,
so every turn recorded by default landed somewhere nothing read.

`--from` gathers traces from another project, because the runs worth
training on happen wherever the work is, not only here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.agent_traces import all_pairs, system_prompt  # noqa: E402
from finetune.splits import write_splits  # noqa: E402
from harness.observe.trace_record import default_trace_path  # noqa: E402


def failed_runs(path: Path) -> set[str]:
    """Ids of runs that ended badly, from the row each run writes last.

    About a third of runs fail. Their turns look exactly like the turns
    of a run that did the job, so without this the training set teaches
    spending twenty steps and writing nothing alongside the work.
    """
    if not path.is_file():
        return set()
    bad: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "ok" in row and str(row.get("ok")).lower() != "true":
            bad.add(str(row.get("run") or ""))
    bad.discard("")
    return bad


def load_turns(path: Path, *, keep_failed: bool = False) -> list[tuple[str, str]]:
    """(prompt, reply) pairs from one recorded file. Empty when absent."""
    if not path.is_file():
        return []
    skip = set() if keep_failed else failed_runs(path)
    pairs: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("run") or "") in skip and row.get("run"):
            continue
        if "ok" in row:
            # The closing row of a run says how it ended; it is not a
            # turn anybody should learn to imitate.
            continue
        user = row.get("user") or row.get("prompt")
        assistant = row.get("assistant") or row.get("draft")
        if user and assistant:
            pairs.append((str(user), str(assistant)))
    return pairs


def recorded_files(extra_roots: list[Path]) -> list[Path]:
    """Every trace file worth reading, in the order they are read."""
    found = [
        ROOT / "data" / "agent-loop" / "extra.jsonl",
        ROOT / "data" / "agent-loop" / "collected.jsonl",
        ROOT / default_trace_path(ROOT).relative_to(ROOT),
    ]
    found.extend(default_trace_path(root.expanduser()) for root in extra_roots)
    return found


def gather(paths: list[Path], *, keep_failed: bool = False) -> list[tuple[str, str]]:
    """Every recorded pair, in order, each one once.

    The same turn appears twice when somebody points `--record` at a
    file this already reads, or names a project with `--from` that is
    also the one being built in. Training on it twice weights it twice.
    """
    seen: set[tuple[str, str]] = set()
    found: list[tuple[str, str]] = []
    for path in paths:
        turns = load_turns(path, keep_failed=keep_failed)
        print(f"  {path}: {len(turns)} turn(s)")
        for pair in turns:
            if pair not in seen:
                seen.add(pair)
                found.append(pair)
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep-failed",
        action="store_true",
        help="include turns from runs that ended badly",
    )
    parser.add_argument(
        "--from",
        dest="roots",
        action="append",
        default=[],
        type=Path,
        metavar="PROJECT",
        help="also read .python-vibe/traces.jsonl from this project",
    )
    args = parser.parse_args()

    dest = ROOT / "data" / "agent-loop"
    recorded = gather(recorded_files(args.roots), keep_failed=args.keep_failed)
    pairs = all_pairs() + recorded
    counts = write_splits(pairs, system_prompt(), dest)
    print(dest, counts, "recorded", len(recorded))
    print(
        "Seed plus every turn recorded by a run. Runs record by default; "
        "pass --no-record to a run that should leave none."
    )


if __name__ == "__main__":
    main()
