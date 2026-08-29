"""Carry out one action against the project.

Each branch returns the text to show the model and the file path the action
applied to. The path is kept by the loop so that a later action which does
not name a file still refers to the file most recently used.

This module makes no decisions about whether an action should run. Those
decisions are in `harness.agent.policy`.
"""

from __future__ import annotations

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


def run_action(
    project: Path, turn, last_path: str, scope: str, target=None, task: str = ""
) -> tuple[str, str]:
    path = turn.path or last_path
    used_scope = turn.scope or scope
    loaded = skill_from_action(turn.action, turn.name, turn.path, project)
    if loaded is not None:
        return render_skill(loaded, target, project), last_path
    if turn.action == "skill":
        return (
            "skill needs Name:. "
            f"{render_catalog(list_skills(project))}",
            last_path,
        )
    if turn.action == "locate":
        return locate_py(project, turn.query or turn.name, used_scope)
    if turn.action == "map":
        return map_py(project, used_scope), last_path
    if turn.action == "layout":
        base = resolve_scope(project, used_scope) if used_scope else project
        return render_layout(base), last_path
    if turn.action == "plan":
        return (
            f"plan noted:\n{turn.summary or '(empty plan)'}\n"
            "Take the first explore action now.",
            last_path,
        )
    if turn.action == "glob":
        return glob_py(project, turn.pattern or "**/*.py", scope=used_scope), last_path
    if turn.action == "grep":
        return grep_py(project, turn.query, scope=used_scope), last_path
    if turn.action == "read":
        if not path:
            return "read needs Path:", last_path
        return read_py(project, path), path
    if turn.action == "edit":
        if not path:
            return "edit needs Path:", last_path
        if not turn.source:
            return "edit needs a ```python block", path
        blocked = PythonVibeGuard().check(turn.source)
        if blocked.verdict != "pass":
            return f"harness blocked: {[f.rule_id for f in blocked.findings]}", path
        return edit_py(project, path, turn.source, task=task), path
    if turn.action == "patch":
        if not path:
            return "patch needs Path: (or read that file first)", last_path
        return patch_py(
            project, path, turn.find, turn.replace, turn.append, task=task
        ), path
    if turn.action == "run":
        return run_python(project, turn.argv), last_path
    if turn.action == "issue":
        return read_issue(
            project, turn.number or turn.name or turn.query
        ), last_path
    if turn.action == "branch":
        return make_branch(project, turn.name or turn.summary), last_path
    if turn.action == "commit":
        return commit_changes(project, turn.summary), last_path
    if turn.action == "push":
        return push_branch(project), last_path
    if turn.action == "pr" and (turn.number or turn.name or turn.query).strip().isdigit():
        return read_pr(
            project, (turn.number or turn.name or turn.query).strip()
        ), last_path
    if turn.action == "pr":
        return create_pr(
            project, turn.title or turn.summary, turn.body or turn.append
        ), last_path
    if turn.action == "merge":
        return merge_pr(
            project, turn.number or turn.name or turn.query, allowed=True
        ), last_path
    return f"unknown Action {turn.action}. Use {ACTIONS}.", last_path
