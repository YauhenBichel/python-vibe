#!/usr/bin/env python3
"""Rebuild scratch/batch-review.md from JSONL. No model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from harness.observe.report_md import write_report  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jsonl", type=Path, default=ROOT / "scratch" / "batch-review.jsonl")
    parser.add_argument("--out", type=Path, default=ROOT / "scratch" / "batch-review.md")
    parser.add_argument("--project", default="(from last batch)")
    args = parser.parse_args()
    if not args.jsonl.is_file():
        sys.exit(f"no jsonl: {args.jsonl}")
    dest = write_report(args.jsonl, args.out, project=args.project)
    print(dest)


if __name__ == "__main__":
    main()
