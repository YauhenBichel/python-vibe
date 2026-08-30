#!/usr/bin/env python3
"""Run python-vibe over a set of everyday tasks and record what happened.

Each case starts from a fresh copy of `demo/orders`, so one case never sees
another's changes and the checked-in project is never modified.

    python scripts/run/demo.py                 # every case, needs Ollama
    python scripts/run/demo.py --offline       # only the cases that use no model
    python scripts/run/demo.py --case question
    python scripts/run/demo.py --markdown docs/demo.md

Nothing here is staged. The results are whatever the model did, including
the cases it fails.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from harness import Agent, AgentOptions  # noqa: E402
from harness.scan.layout import render_layout  # noqa: E402
from harness.scan.project_brief import classify_project, render_brief  # noqa: E402
from harness.skillkit.catalog import list_skills, pick_skills  # noqa: E402

DEMO_PROJECT = ROOT / "demo" / "orders"


@dataclass(frozen=True)
class Case:
    """One everyday task, and what the demo is trying to show with it.

    Fields:
        key: short name, used by --case.
        title: what a person would call this job.
        task: the words handed to the agent.
        shows: the behaviour this case is meant to demonstrate.
        needs_model: False for the cases the harness answers on its own.
        options: extra AgentOptions fields, such as allow_writes.
        check: Python run inside the finished project. Exit 0 means the work
            really happened. An agent reporting success is not evidence:
            one run fixed the bug correctly and then described writing a
            test it never wrote.
        expect_no_writes: the case passes only if nothing was changed.
    """

    key: str
    title: str
    task: str
    shows: str
    needs_model: bool = True
    options: dict = field(default_factory=dict)
    check: str = ""
    expect_no_writes: bool = False


CASES: tuple[Case, ...] = (
    Case(
        "brief", "Size up an unfamiliar repo", "",
        "How big the project is, which files are in it, and which skills\n"
        "would apply. No model is called.",
        needs_model=False,
    ),
    Case(
        "layout", "Find out why a tree is hard to read", "",
        "Two files importing each other, a folder with too many files in\n"
        "it, one file much larger than the rest, and missing tests.",
        needs_model=False,
    ),
    Case(
        "question", "Ask what a function does",
        "what does compute_total return?",
        "The function is found and read for the model before its first turn.",
        options={"allow_writes": False},
        expect_no_writes=True,
    ),
    Case(
        "bugfix", "Fix a bug no test covers",
        "find a real NameError in src/orders.py and fix it",
        "Naming a file in the task opens that file, and no other file may\n"
        "then be changed.",
        check="from src.orders import total_with_tax\n"
              "assert total_with_tax([10]) == 12.0",
    ),
    Case(
        "add-feature", "Add a function and a test",
        "add a function total_lines(prices) that counts the prices, and a unit test",
        "The function is added, then a test for it, then the tests are run.",
        check="from src.orders import total_lines\n"
              "assert total_lines([1, 2, 3]) == 3",
    ),
    Case(
        "write-tests", "Cover something that has no test",
        "write tests for apply_discount in src/orders.py",
        "One test is added that sets up its inputs, calls the function, and\n"
        "checks the result. The import line is corrected automatically.",
        check="import pathlib\n"
              "body = pathlib.Path('tests/test_orders.py').read_text()\n"
              "assert 'apply_discount' in body, 'no test names apply_discount'",
    ),
    Case(
        "rename", "Give an opaque name a real one",
        "rename calc to multiply in src/util.py",
        "The new name is written where the function is defined, not in the\n"
        "first file that mentions it.",
        check="from src.util import multiply\nassert multiply(2, 3) == 6",
    ),
    Case(
        "review", "Review one file without changing it",
        "review src/orders.py for bugs",
        "A review reports what it finds. Any attempt to edit is refused.",
        expect_no_writes=True,
    ),
    Case(
        "dry-run", "See what it would do, change nothing",
        "fix the NameError in src/orders.py",
        "With writes turned off, every change is refused before it happens.",
        options={"allow_writes": False},
        expect_no_writes=True,
    ),
    Case(
        "vague", "Give it a task that says nothing",
        "clean this up",
        "The task names no file and no function, so it asks instead of\n"
        "guessing.",
        expect_no_writes=True,
    ),
    Case(
        "scoped", "Stay inside one folder on a bigger tree",
        "what does render_line return?",
        "Searching and listing stay inside the folder given by --scope.",
        options={"scope": "src"},
    ),
    Case(
        "cover-service", "Write tests for a class that has none",
        "write tests for OrderService in src/orders_service.py",
        "A class with no tests gets a new test file, not a rewrite of an\n"
        "already-covered function.",
        check="import pathlib, unittest\n"
              "root = pathlib.Path('.')\n"
              "hits = [p for p in root.rglob('test*.py') "
              "if 'OrderService' in p.read_text() or 'orders_service' in p.read_text()]\n"
              "assert hits, 'no test mentions OrderService'\n"
              "loader = unittest.defaultTestLoader\n"
              "suite = unittest.TestSuite()\n"
              "for path in hits:\n"
              "    name = path.with_suffix('').as_posix().replace('/', '.')\n"
              "    suite.addTests(loader.loadTestsFromName(name))\n"
              "assert unittest.TextTestRunner(verbosity=0).run(suite).wasSuccessful()",
    ),
    Case(
        "controller-bug", "Fix a NameError in a controller",
        "find the NameError in src/orders_controller.py and fix it",
        "The planted typo is `stauts` in OrdersController.status.",
        check="from src.orders_controller import OrdersController\n"
              "OrdersController().status()",
    ),
)


def _fresh_copy(into: Path) -> Path:
    project = into / "orders"
    shutil.copytree(
        DEMO_PROJECT,
        project,
        ignore=shutil.ignore_patterns("*.bak", "__pycache__"),
    )
    return project


def _offline_result(case: Case, project: Path) -> dict:
    if case.key == "brief":
        brief = classify_project(project)
        catalog = list_skills(project)
        return {
            "output": render_brief(brief),
            "skills_available": [item.name for item in catalog],
        }
    return {"output": render_layout(project)}


def run_case(case: Case, *, model: str, steps: int) -> dict:
    started = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        project = _fresh_copy(Path(tmp))
        row: dict = {
            "case": case.key,
            "title": case.title,
            "task": case.task,
            "shows": case.shows,
            "needs_model": case.needs_model,
            "command": case_command(case),
        }
        if not case.needs_model:
            row.update(_offline_result(case, project))
            row["seconds"] = round(time.time() - started, 1)
            return row
        row["skills_picked"] = [
            item.name for item in pick_skills(case.task, list_skills(project))
        ]
        options = AgentOptions(
            project=project,
            task=case.task,
            model=model,
            steps=steps,
            # Nobody is at a keyboard during the demo, so a question comes
            # back as a result instead of blocking.
            **case.options,
        )
        try:
            result = Agent(options).run()
        except (ValueError, OSError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            row["seconds"] = round(time.time() - started, 1)
            return row
        verdict, why = verify(case, project, list(result.writes))
        row.update(
            {
                "ok": result.ok,
                "verified": verdict,
                "verify_detail": why,
                "stopped": result.stopped,
                "actions": [step.action or "unparsed" for step in result.steps],
                "refusals": [text for text in result.refusals],
                "writes": list(result.writes),
                "summary": (result.summary or "").strip(),
                "diff": _diff(project),
            }
        )
    row["seconds"] = round(time.time() - started, 1)
    return row


def verify(case: Case, project: Path, writes: list[str]) -> tuple[str, str]:
    """Check the work independently of what the agent said about it.

    Returns a verdict and, when it failed, why. "not checked" means the case
    is about behaviour rather than an outcome in the files.
    """
    if case.expect_no_writes:
        if writes:
            return "failed", f"expected no changes, got {', '.join(writes)}"
        return "passed", ""
    if not case.check:
        return "not checked", ""
    proc = subprocess.run(
        [sys.executable, "-c", case.check],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if proc.returncode == 0:
        return "passed", ""
    detail = (proc.stderr or proc.stdout).strip().splitlines()
    return "failed", detail[-1] if detail else "check exited non-zero"


def _diff(project: Path) -> list[str]:
    """Which files differ from the checked-in demo project, and how."""
    changed: list[str] = []
    for path in sorted(project.rglob("*.py")):
        rel = path.relative_to(project).as_posix()
        if path.name.endswith(".bak"):
            continue
        original = DEMO_PROJECT / rel
        if not original.is_file():
            changed.append(f"+ {rel} (new file)")
            continue
        if path.read_text(encoding="utf-8") != original.read_text(encoding="utf-8"):
            changed.append(f"~ {rel}")
    return changed


def render_markdown(rows: list[dict], model: str) -> str:
    lines = [
        "---",
        "title: Demo",
        "description: python-vibe run over eleven everyday tasks on one small "
        "project. Real output, including the cases it does not finish.",
        "permalink: /demo/",
        "date: 2026-08-29",
        "---",
        "",
        "# Demo",
        "",
        f"Every case below was run against `demo/orders`, a small project "
        f"with a few deliberate problems in it, using `{model}` through "
        "Ollama on one laptop. Each case started from a fresh copy, so no "
        "case could see another one's changes.",
        "",
        "Reproduce it:",
        "",
        "```bash",
        "ollama pull llama3.1:8b",
        "python scripts/run/demo.py --markdown docs/demo.md",
        "```",
        "",
        "Two columns matter. **Agent says** is whether it reported that it "
        "had finished. **Checked** is a separate test run against the files "
        "afterwards. The two do not always agree. In one run the bug was "
        "fixed correctly, and the report described writing a test that was "
        "never written.",
        "",
        "The model does not give the same answer twice. Rebuilding this "
        "page changes which cases pass. `write-tests` and `rename` have "
        "each both passed and failed on different runs, while `bugfix`, "
        "`dry-run` and `vague` have not yet failed. Read the table as one "
        "run, not as a score.",
        "",
        "Four results do not depend on the model. The first two cases need "
        "no model at all. `dry-run` changes nothing, because every change "
        "is refused before it happens. `vague` stops and asks which file to "
        "work on. `review` reports without editing.",
        "",
        "## Summary",
        "",
        "| Case | Task | Agent says | Checked | Steps | Files changed |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        if not row["needs_model"]:
            lines.append(
                f"| [{row['case']}](#{row['case']}) | {row['title']} "
                f"| no model needed | — | — | none |"
            )
            continue
        finished = "yes" if row.get("ok") else f"no ({row.get('stopped', 'error')})"
        steps = len(row.get("actions", []))
        writes = ", ".join(f"`{item}`" for item in row.get("writes", [])) or "none"
        lines.append(
            f"| [{row['case']}](#{row['case']}) | {row['title']} "
            f"| {finished} | {row.get('verified', '—')} | {steps} | {writes} |"
        )
    for row in rows:
        lines.extend(_render_case(row))
    return "\n".join(lines) + "\n"


def case_command(case: Case) -> str:
    """The command a reader can copy to reproduce this case.

    Built from the options the case actually ran with. A fixed list of
    case names drifted from them: the dry-run case printed a plain
    `run`, so copying the line let it write, under a caption saying
    writes were off.
    """
    writes = case.options.get("allow_writes", True)
    verb = "ask" if case.task.rstrip().endswith("?") else "run"
    flags = "" if verb == "ask" or writes else " --dry-run"
    scope = case.options.get("scope", "")
    if scope:
        flags += f" --scope {scope}"
    return f'python-vibe {verb}{flags} ./orders "{case.task}"'


def _render_case(row: dict) -> list[str]:
    out = ["", f"## {row['case']}", "", f"**{row['title']}.** {row['shows']}", ""]
    if row["task"]:
        out += ["```", row["command"], "```", ""]
    if not row["needs_model"]:
        out += ["```", row["output"].rstrip(), "```"]
        if row.get("skills_available"):
            out += ["", "Skills available: " + ", ".join(
                f"`{name}`" for name in row["skills_available"]
            )]
        return out
    if row.get("error"):
        return out + [f"Failed to run: `{row['error']}`"]
    if row.get("skills_picked"):
        out.append(
            "Skills loaded: "
            + ", ".join(f"`{name}`" for name in row["skills_picked"])
        )
        out.append("")
    out.append("Actions: " + " → ".join(f"`{a}`" for a in row["actions"]))
    out.append("")
    if row["refusals"]:
        out.append("Refused by the harness:")
        out.append("")
        for text in row["refusals"]:
            out.append(f"- {text.strip()}")
        out.append("")
    if row["writes"]:
        out.append("Changed: " + ", ".join(f"`{w}`" for w in row["writes"]))
        out.append("")
    if row["diff"]:
        out.append("Files differing from the checked-in project:")
        out.append("")
        for entry in row["diff"]:
            out.append(f"- `{entry}`")
        out.append("")
    verdict = row.get("verified", "not checked")
    if verdict != "not checked":
        detail = f" — {row['verify_detail']}" if row.get("verify_detail") else ""
        out.append(f"Separate check: **{verdict}**{detail}")
        out.append("")
    out.append(f"What it reported ({row['stopped']}, {row['seconds']}s):")
    out.append("")
    out.append("```")
    out.append(row["summary"] or "(no summary)")
    out.append("```")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="llama3.1:8b")
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument(
        "--offline", action="store_true", help="skip every case that calls a model"
    )
    parser.add_argument("--markdown", type=Path, help="write a page instead of JSON")
    args = parser.parse_args()

    cases = [c for c in CASES if not args.case or c.key in args.case]
    if args.offline:
        cases = [c for c in cases if not c.needs_model]
    if not cases:
        print("no cases selected", file=sys.stderr)
        return 2

    rows: list[dict] = []
    for case in cases:
        print(f"--- {case.key}: {case.title}", file=sys.stderr, flush=True)
        rows.append(run_case(case, model=args.model, steps=args.steps))

    if args.markdown:
        args.markdown.write_text(render_markdown(rows, args.model), encoding="utf-8")
        print(f"wrote {args.markdown}")
    else:
        print(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
