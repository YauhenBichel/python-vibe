"""Carry out one action against the project.

Each branch returns the text to show the model and the file path the action
applied to. The path is kept by the loop so that a later action which does
not name a file still refers to the file most recently used.

This module makes no decisions about whether an action should run. Those
decisions are in `harness.agent.policy`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pathlib import Path

from harness.act.tools import (
    edit_py,
    glob_py,
    grep_py,
    map_py,
    patch_py,
    read_py,
    run_python,
)
from harness.guard.python_vibe import PythonVibeGuard
from harness.locate import locate_py
from harness.scan.layout import render_layout
from harness.scan.project_brief import resolve_scope
from harness.ship.git_ship import (
    commit_changes,
    create_pr,
    make_branch,
    merge_pr,
    push_branch,
    read_issue,
    read_pr,
)
from harness.skillkit.catalog import (
    list_skills,
    render_catalog,
    render_skill,
    skill_from_action,
)

ACTIONS = (
    "glob|grep|read|edit|patch|run|map|plan|skill|locate|layout|ask|done|"
    "issue|branch|commit|push|pr|merge"
)
WRITE_ACTIONS = frozenset({"edit", "patch", "run"})
SHIP_ACTIONS = frozenset({"issue", "branch", "commit", "push", "pr", "merge"})


@dataclass(frozen=True)
class Ask:
    """One action the model asked for, and everything it may act on.

    Fields:
        project: the folder the run may read and write inside.
        turn: the parsed action, with whichever fields it carried.
        path: the file this action lands on — the one it named, or the
            last one touched.
        last_path: what to report when the action changes no file.
        scope: the folder to stay inside, if the run was given one.
        target: the skill target, when a skill is being rendered.
        task: what the user asked for, in their own words.
    """

    project: Path
    turn: object
    path: str
    last_path: str
    scope: str
    target: object
    task: str


def _locate(ask: Ask) -> tuple[str, str]:
    return locate_py(ask.project, ask.turn.query or ask.turn.name, ask.scope)


def _map(ask: Ask) -> tuple[str, str]:
    return map_py(ask.project, ask.scope), ask.last_path


def _layout(ask: Ask) -> tuple[str, str]:
    base = resolve_scope(ask.project, ask.scope) if ask.scope else ask.project
    return render_layout(base), ask.last_path


def _plan(ask: Ask) -> tuple[str, str]:
    return (
        f"plan noted:\n{ask.turn.summary or '(empty plan)'}\n"
        "Take the first explore action now."
    ), ask.last_path


def _glob(ask: Ask) -> tuple[str, str]:
    pattern = ask.turn.pattern or "**/*.py"
    return glob_py(ask.project, pattern, scope=ask.scope), ask.last_path


def _grep(ask: Ask) -> tuple[str, str]:
    return grep_py(ask.project, ask.turn.query, scope=ask.scope), ask.last_path


def refuse_outside_scope(project: Path, scope: str, rel: str) -> str:
    """Refuse a write to a file outside the folder the run was given.

    `--scope` says "work only inside this folder". It was threaded into
    locate, map, glob and grep — every read — and never reached patch or
    edit, so the one flag a person uses to fence the tool off from the
    rest of a project did not fence the part that changes files.

    A real run showed what that costs. Given `--scope scripts`, it left
    scope at step five, appended nonsense to `tests/whole/test_bench.py`,
    and ended with the suite broken and the asked-for function never
    written.

    This guards the actions the model chooses. A repair the harness
    applies itself still goes where it goes — a cover test belongs in
    `tests/` whatever the scope is — and that is deliberate.
    """
    # An empty scope needs no special case: `resolve_scope` answers the
    # project root for it, and every path in the project is inside that.
    if not rel:
        return ""
    try:
        base = resolve_scope(Path(project), scope)
    except ValueError:
        # A scope that cannot be resolved is reported where it is set.
        return ""
    root = Path(project).resolve()
    try:
        (root / rel).resolve().relative_to(base)
    except ValueError:
        return (
            f"{rel} is outside this run's scope ({scope}). Stay inside "
            f"{scope}/ — or re-run without --scope if the change really "
            "belongs elsewhere."
        )
    return ""


def _read(ask: Ask) -> tuple[str, str]:
    if not ask.path:
        return "read needs Path:", ask.last_path
    return read_py(ask.project, ask.path), ask.path


def _edit(ask: Ask) -> tuple[str, str]:
    if not ask.path:
        return "edit needs Path:", ask.last_path
    outside = refuse_outside_scope(ask.project, ask.scope, ask.path)
    if outside:
        return outside, ask.last_path
    if not ask.turn.source:
        return "edit needs a ```python block", ask.path
    blocked = PythonVibeGuard().check(ask.turn.source)
    if blocked.verdict != "pass":
        return (
            f"harness blocked: {[f.rule_id for f in blocked.findings]}",
            ask.path,
        )
    return edit_py(ask.project, ask.path, ask.turn.source, task=ask.task), ask.path


def _patch(ask: Ask) -> tuple[str, str]:
    if not ask.path:
        return "patch needs Path: (or read that file first)", ask.last_path
    outside = refuse_outside_scope(ask.project, ask.scope, ask.path)
    if outside:
        return outside, ask.last_path
    return patch_py(
        ask.project,
        ask.path,
        ask.turn.find,
        ask.turn.replace,
        ask.turn.append,
        task=ask.task,
    ), ask.path


def _run(ask: Ask) -> tuple[str, str]:
    return run_python(ask.project, ask.turn.argv), ask.last_path


def _skill(ask: Ask) -> tuple[str, str]:
    return (
        f"skill needs Name:. {render_catalog(list_skills(ask.project))}",
        ask.last_path,
    )


def _named(ask: Ask) -> str:
    """The issue or pull request number an action carried."""
    return (ask.turn.number or ask.turn.name or ask.turn.query or "").strip()


def _issue(ask: Ask) -> tuple[str, str]:
    return read_issue(ask.project, _named(ask)), ask.last_path


def _branch(ask: Ask) -> tuple[str, str]:
    return make_branch(ask.project, ask.turn.name or ask.turn.summary), ask.last_path


def _commit(ask: Ask) -> tuple[str, str]:
    return commit_changes(ask.project, ask.turn.summary), ask.last_path


def _push(ask: Ask) -> tuple[str, str]:
    return push_branch(ask.project), ask.last_path


def _pr(ask: Ask) -> tuple[str, str]:
    """A number reads that pull request; anything else opens one."""
    number = _named(ask)
    if number.isdigit():
        return read_pr(ask.project, number), ask.last_path
    return create_pr(
        ask.project,
        ask.turn.title or ask.turn.summary,
        ask.turn.body or ask.turn.append,
    ), ask.last_path


def _merge(ask: Ask) -> tuple[str, str]:
    return merge_pr(ask.project, _named(ask), allowed=True), ask.last_path


# One entry per action the model may take. This was nineteen
# `if turn.action == ...` tests in a row, which hid both the list and
# the fact that a new action has to be added to it: forgetting meant a
# silent "unknown Action" rather than an error anyone would notice.
# `ask` and `done` are answered by the loop before it gets here.
HANDLERS: dict[str, Callable[[Ask], tuple[str, str]]] = {
    "locate": _locate,
    "map": _map,
    "layout": _layout,
    "plan": _plan,
    "glob": _glob,
    "grep": _grep,
    "read": _read,
    "edit": _edit,
    "patch": _patch,
    "run": _run,
    "skill": _skill,
    "issue": _issue,
    "branch": _branch,
    "commit": _commit,
    "push": _push,
    "pr": _pr,
    "merge": _merge,
}


def run_action(
    project: Path, turn, last_path: str, scope: str, target=None, task: str = ""
) -> tuple[str, str]:
    """Carry out one action, and say which file it left the run on."""
    loaded = skill_from_action(turn.action, turn.name, turn.path, project)
    if loaded is not None:
        return render_skill(loaded, target, project), last_path
    handler = HANDLERS.get(turn.action)
    if handler is None:
        return f"unknown Action {turn.action}. Use {ACTIONS}.", last_path
    return handler(
        Ask(
            project=project,
            turn=turn,
            path=turn.path or last_path,
            last_path=last_path,
            scope=turn.scope or scope,
            target=target,
            task=task,
        )
    )
