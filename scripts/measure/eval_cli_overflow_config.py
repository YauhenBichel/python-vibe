#!/usr/bin/env python3
"""Config-overflow job × three repeats on llama3.1:8b.

  PYTHONPATH=src python scripts/measure/eval_cli_overflow_config.py

Starts from a list+show+comment+page= tree. Typed: add a config file
via Path.home. Pass means overflow_gaps no longer lists config.
Default --steps 12.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA  # noqa: E402
from harness import Agent, AgentOptions  # noqa: E402
from harness.scan.app_spec import overflow_gaps, required_gaps  # noqa: E402

TASK = "add a config file via Path.home"
REPEATS = 3
STEPS = 12

_IMPL = """\
import argparse
import json
import os
import urllib.request


def list_pulls(owner, repository):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repository}/pulls?page=1"
    )
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def show_pull(owner, repository, number):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repository}/pulls/{number}"
    )
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def comment_on(owner, repository, number, body):
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        f"https://api.github.com/repos/{owner}/{repository}/issues/{number}/comments",
        data=json.dumps({"body": body}).encode(),
        method="POST",
    )
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    listed = sub.add_parser("list")
    listed.add_argument("owner")
    listed.add_argument("repository")
    shown = sub.add_parser("show")
    shown.add_argument("owner")
    shown.add_argument("repository")
    shown.add_argument("number", type=int)
    noted = sub.add_parser("comment")
    noted.add_argument("owner")
    noted.add_argument("repository")
    noted.add_argument("number", type=int)
    noted.add_argument("body")
    args = parser.parse_args()
    if args.cmd == "list":
        print(list_pulls(args.owner, args.repository))
    elif args.cmd == "show":
        print(show_pull(args.owner, args.repository, args.number))
    else:
        print(comment_on(args.owner, args.repository, args.number, args.body))


if __name__ == "__main__":
    main()
"""

_TEST = """\
import json
import os
import unittest
from unittest.mock import patch

from pkg.pr_review import list_pulls


class TestListPulls(unittest.TestCase):
    def test_list_pulls_returns_titles(self) -> None:
        payload = [{"title": "Fix login", "number": 1}]
        with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
            with patch("urllib.request.urlopen") as fake:
                fake.return_value.__enter__.return_value.read.return_value = (
                    json.dumps(payload).encode()
                )
                got = list_pulls("owner", "repo")
        self.assertEqual(got, payload)
"""


def _seed(dest: Path) -> None:
    pkg = dest / "pkg"
    tests = dest / "tests"
    pkg.mkdir()
    tests.mkdir()
    (pkg / "__init__.py").write_text('"""exports"""\n', encoding="utf-8")
    (pkg / "pr_review.py").write_text(_IMPL, encoding="utf-8")
    (tests / "__init__.py").write_text("", encoding="utf-8")
    (tests / "test_pr_review.py").write_text(_TEST, encoding="utf-8")


def _run_one(model: str, steps: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp)
        _seed(dest)
        assert not required_gaps(dest, "design and develop a small cli app for reviewing github PRs")
        result = Agent(
            AgentOptions(
                project=dest,
                task=TASK,
                model=model,
                keep_no_record=True,
                steps=steps,
            )
        ).run()
        extra = [gap.key for gap in overflow_gaps(dest, TASK)]
        return {
            "ok": "config" not in extra,
            "overflow_missing": extra,
            "stopped": result.stopped,
            "writes": list(result.writes),
            "summary": result.summary[:160],
        }


def main() -> None:
    model = DEFAULT_EVERYDAY_OLLAMA
    steps = STEPS
    if "--model" in sys.argv:
        model = sys.argv[sys.argv.index("--model") + 1]
    if "--steps" in sys.argv:
        steps = int(sys.argv[sys.argv.index("--steps") + 1])
    rows = []
    for _repeat in range(REPEATS):
        row = _run_one(model, steps)
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    passed = sum(int(row["ok"]) for row in rows)
    print(
        json.dumps(
            {"model": model, "task": TASK, "passed": passed, "n": len(rows)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
