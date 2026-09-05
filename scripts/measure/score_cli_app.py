#!/usr/bin/env python3
"""Score one greenfield GitHub-CLI run against the app checklist.

    PYTHONPATH=src python scripts/measure/score_cli_app.py /tmp/pr-review-r1
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from harness.scan.app_spec import overflow_gaps, required_gaps  # noqa: E402

CLI = "design and develop a small cli app for reviewing github PRs"


def score(project: Path) -> dict:
    req = [gap.key for gap in required_gaps(project, CLI)]
    extra = [gap.key for gap in overflow_gaps(project, CLI)]
    files = sorted(
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_file() and ".python-vibe" not in path.parts
    )
    return {
        "required_missing": req,
        "overflow_missing": extra,
        "list_show_ready": not req,
        "files": files,
    }


def main() -> None:
    project = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    print(json.dumps(score(project), indent=2))


if __name__ == "__main__":
    main()
