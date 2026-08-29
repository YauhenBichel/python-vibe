"""Command line interface for the harness.

One command with subcommands, so a user does not have to know which file in
`scripts/` to run:

    python -m harness brief  ~/app
    python -m harness layout ~/app
    python -m harness ask    ~/app "what does compute_total return?"
    python -m harness run    ~/app "add multiply(a, b) and a test"
    python -m harness serve    --project ~/app
    python -m harness mcp      --project ~/app
    python -m harness editors  cursor --allow-writes
    python -m harness commit   ~/app "why the change landed"
    python -m harness route    "what does compute_total return?"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from harness.agent import Agent, AgentOptions
from harness.agent.options import DEFAULT_MAX_TOKENS, DEFAULT_STEPS
from harness.scan.layout import render_layout
from harness.scan.project_brief import classify_project, render_brief_for_person
from harness.skillkit.catalog import list_skills


def _printer(verbose: bool):
    def emit(kind: str, text: str) -> None:
        if not text:
            return
        if kind == "draft":
            print(f"\n{text}\n", flush=True)
        elif verbose or kind in {"refused", "engine"}:
            print(text[:2000], file=sys.stderr)

    return emit


def _prompt_user(question) -> str:
    """The agent asked. Put it to the person actually sitting here."""
    print(f"\n{question.render()}", file=sys.stderr)
    try:
        answer = input("> ").strip()
    except EOFError:
        return ""
    if question.options and answer.isdigit():
        index = int(answer) - 1
        if 0 <= index < len(question.options):
            return question.options[index]
    return answer


def _options(args, *, interactive: bool) -> AgentOptions:
    return AgentOptions(
        project=args.project,
        task=getattr(args, "task", "") or "",
        model=args.model,
        engine=args.engine,
        scope=args.scope,
        skills=tuple(args.skill or ()),
        steps=args.steps,
        max_tokens=args.max_tokens,
        allow_writes=getattr(args, "allow_writes", True),
        record=getattr(args, "record", None),
        on_event=_printer(args.verbose),
        on_question=_prompt_user if interactive else None,
    )


def _add_agent_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scope", default="", help="work only inside this folder")
    parser.add_argument("--skill", action="append", default=[], metavar="NAME")
    parser.add_argument("--model", default=AgentOptions(project=Path(".")).model)
    parser.add_argument("--engine", default="ollama")
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--record", type=Path)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")


def _program_name() -> str:
    """What to print in usage: the installed command, or the module form."""
    name = Path(sys.argv[0]).name
    if name.startswith("python-vibe"):
        return "python-vibe"
    return "python -m harness"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=_program_name())
    subs = parser.add_subparsers(dest="command", required=True)

    brief = subs.add_parser("brief", help="summarise a project. Needs no AI model.")
    brief.add_argument("project", type=Path)
    brief.add_argument("--scope", default="")

    layout = subs.add_parser("layout", help="report what makes a project hard to read. Needs no AI model.")
    layout.add_argument("project", type=Path)

    route = subs.add_parser(
        "route", help="which local model suits a task. Needs no AI model."
    )
    route.add_argument("task")

    ask = subs.add_parser("ask", help="answer a question about the project. Changes nothing.")
    ask.add_argument("project", type=Path)
    ask.add_argument("task")
    _add_agent_flags(ask)

    run = subs.add_parser("run", help="make a change, then run the tests")
    run.add_argument("project", type=Path)
    run.add_argument("task")
    run.add_argument(
        "--dry-run",
        dest="allow_writes",
        action="store_false",
        help="say what it would change, without changing anything",
    )
    _add_agent_flags(run)

    serve = subs.add_parser("serve", help="serve on this machine only. Changes nothing unless --allow-writes.")
    serve.add_argument("--project", type=Path, required=True)
    serve.add_argument("--port", type=int, default=8090)
    serve.add_argument(
        "--allow-writes",
        action="store_true",
        help="allow callers to change files inside --project",
    )
    serve.add_argument("--model", default=AgentOptions(project=Path(".")).model)

    mcp = subs.add_parser(
        "mcp",
        help="let an editor call python-vibe. Changes nothing unless --allow-writes.",
    )
    mcp.add_argument("--project", type=Path, required=True)
    mcp.add_argument("--allow-writes", action="store_true")
    mcp.add_argument("--model", default=AgentOptions(project=Path(".")).model)

    commit = subs.add_parser(
        "commit",
        help="record current changes. You stay the author; python-vibe is co-author.",
    )
    commit.add_argument("project", type=Path)
    commit.add_argument("summary", help="why, not what (at least 8 characters)")

    editors = subs.add_parser(
        "editors",
        help="write ready-made editor settings into a project",
    )
    editors.add_argument("kind", choices=("vscode", "continue", "cursor", "zed"))
    editors.add_argument(
        "--project",
        type=Path,
        default=Path("."),
        help="folder to jail (default: current directory)",
    )
    editors.add_argument(
        "--allow-writes",
        action="store_true",
        help="let the editor's run tool change files (cursor MCP only)",
    )
    editors.add_argument(
        "--global",
        dest="user_wide",
        action="store_true",
        help="merge into ~/.cursor/mcp.json so every workspace can call it",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "brief":
        project = args.project.expanduser().resolve()
        print(
            render_brief_for_person(
                classify_project(project, args.scope), scope=args.scope
            )
        )
        # The full catalogue is written for the model, in the model's own
        # syntax. Printing it here buries the answer the person asked for.
        count = len(list_skills(project))
        print()
        print(
            f"python-vibe has {count} skills it can apply. It picks them from "
            "the wording of your task; you do not choose them."
        )
        return 0

    if args.command == "layout":
        print(render_layout(args.project.expanduser().resolve()))
        return 0

    if args.command == "route":
        from harness.model.route import route_advice

        print(route_advice(args.task))
        return 0

    if args.command == "serve":
        from harness.server import serve

        return serve(
            args.project.expanduser().resolve(),
            port=args.port,
            allow_writes=args.allow_writes,
            model=args.model,
        )

    if args.command == "mcp":
        from harness.mcp_stdio import serve_stdio

        return serve_stdio(
            args.project.expanduser().resolve(),
            allow_writes=args.allow_writes,
            model=args.model,
        )

    if args.command == "commit":
        from harness.ship.git_ship import commit_changes

        print(commit_changes(args.project.expanduser().resolve(), args.summary))
        return 0

    if args.command == "editors":
        from harness.editor_kit import install_editors, next_steps

        try:
            written = install_editors(
                args.project,
                args.kind,
                allow_writes=getattr(args, "allow_writes", False),
                user_wide=getattr(args, "user_wide", False),
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        for path in written:
            print(path)
        print()
        print(
            next_steps(
                args.kind,
                allow_writes=getattr(args, "allow_writes", False),
                user_wide=getattr(args, "user_wide", False),
            )
        )
        return 0

    interactive = sys.stdin.isatty()
    if args.command == "ask":
        args.allow_writes = False
    try:
        result = Agent(_options(args, interactive=interactive)).run()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    else:
        print(result.summary)
    return 0 if result.ok else 1
