"""Limited git and gh. Deterministic. No model. No force. No main."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from harness.paths import SECRET_NAMES
from harness.ship.bot_pr import refuse_bot_merge
from harness.ship.identity import co_author_line, with_co_author
from harness.ship.ticket import identity_from_user_json, parse_ticket, render_ticket

PROTECTED = frozenset({"main", "master"})
_BRANCH = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._/-]{0,79}$")
CO_AUTHOR = co_author_line()
# Says on the pull request itself which tool did the work, the way a
# commit trailer does for a commit.
PR_FOOTER = (
    "\n\n---\nOpened with [py-harness](https://github.com/YauhenBichel/py-harness).\n"
    f"{CO_AUTHOR}\n"
)
_TIMEOUT = 45


def _run(
    project: Path,
    argv: list[str],
    *,
    env: dict[str, str] | None = None,
    keep_all: bool = False,
) -> tuple[int, str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    # The person stays the author, so the commit is theirs and appears in
    # their history. python-vibe is recorded as a co-author instead, which
    # GitHub renders on the commit, so it is visible where it was used.
    try:
        proc = subprocess.run(
            argv,
            cwd=project,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
            check=False,
            env=merged,
        )
    except FileNotFoundError:
        return 127, f"{argv[0]} is not on PATH"
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    out = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if keep_all:
        return proc.returncode, out
    # Command output is cut from the front, because the end of a git or gh
    # message is the part that says what happened. JSON has to be kept
    # whole or it will not parse, which is what `keep_all` is for.
    return proc.returncode, out[-4000:]


def git_root(project: Path) -> Path | None:
    code, out = _run(project, ["git", "rev-parse", "--show-toplevel"])
    if code != 0:
        return None
    try:
        return Path(out.splitlines()[0]).resolve()
    except (IndexError, OSError):
        return None


def _in_project(project: Path) -> str:
    root = git_root(project)
    if root is None:
        return "not a git repository"
    if root != project.resolve():
        return f"git root is {root}, not {project} — refuse"
    return ""


def current_branch(project: Path) -> str:
    code, out = _run(project, ["git", "rev-parse", "--abbrev-ref", "HEAD"])
    return out.splitlines()[0] if code == 0 and out else ""


def github_viewer(project: Path) -> str:
    """The signed-in `gh` login, or empty when gh is missing or logged out."""
    code, out = _run(project, ["gh", "api", "user"], keep_all=True)
    if code != 0:
        return ""
    login, _name, _email = identity_from_user_json(out)
    return login


def _view(project: Path, kind: str, number: str) -> str:
    """Read one issue or pull request, and say where it points in this project.

    Uses the signed-in gh user so comments from other users on the same
    ticket are visible — the same account that can see them in the browser.
    """
    if not number.isdigit():
        return f"{kind} needs Number: (digits)"
    fields = "number,title,body,state,comments"
    if kind == "pr":
        fields += ",files,reviews"
    code, out = _run(
        project, ["gh", kind, "view", number, "--json", fields], keep_all=True
    )
    if code != 0:
        return out or f"gh {kind} view {number} failed"
    ticket = parse_ticket(
        out,
        project,
        kind="pull request" if kind == "pr" else "issue",
        viewer=github_viewer(project),
    )
    if ticket is None:
        return out[:3500]
    return render_ticket(ticket)[:3500]


def read_issue(project: Path, number: str) -> str:
    return _view(project, "issue", number)


def read_pr(project: Path, number: str) -> str:
    return _view(project, "pr", number)


def read_ticket(project: Path, number: str, *, prefer: str = "issue") -> str:
    """Read an issue, or a pull request when the task named a PR."""
    first = read_pr if prefer == "pr" else read_issue
    second = read_issue if prefer == "pr" else read_pr
    out = first(project, number)
    failed = "failed" in out.lower() or "could not" in out.lower() or "needs Number" in out
    if failed:
        other = second(project, number)
        if "failed" not in other.lower() and "could not" not in other.lower():
            return other
    return out


def make_branch(project: Path, name: str) -> str:
    blocked = _in_project(project)
    if blocked:
        return blocked
    name = name.strip().lstrip("/")
    if not _BRANCH.match(name) or name in PROTECTED or name.startswith("-"):
        return (
            "bad branch name. Use proceed/short-slug "
            "(letters, digits, . _ / -). Not main or master."
        )
    code, out = _run(project, ["git", "checkout", "-B", name])
    return out or f"now on {name}" if code == 0 else out


def commit_changes(project: Path, summary: str) -> str:
    blocked = _in_project(project)
    if blocked:
        return blocked
    message = " ".join(summary.strip().split())
    if len(message) < 8:
        return "commit needs Summary: of at least 8 characters (why, not what)"
    _run(project, ["git", "add", "-A"])
    for rel in SECRET_NAMES:
        path = project / rel
        if path.exists() or path.is_symlink():
            _run(project, ["git", "reset", "-q", "--", rel])
    code, staged = _run(project, ["git", "diff", "--cached", "--name-only"])
    names = [line for line in staged.splitlines() if line.strip()] if code == 0 else []
    if any(Path(name).name in SECRET_NAMES for name in names):
        return "refusing to commit secret filenames"
    if not names:
        return "nothing to commit"
    code, out = _run(project, ["git", "commit", "-m", with_co_author(message)])
    return out or "committed" if code == 0 else out


def push_branch(project: Path) -> str:
    blocked = _in_project(project)
    if blocked:
        return blocked
    branch = current_branch(project)
    if not branch or branch in PROTECTED:
        return f"refusing to push {branch or 'detached'} (not main/master)"
    code, remotes = _run(project, ["git", "remote"])
    if code != 0 or "origin" not in remotes.split():
        return "no origin remote. Add origin or push yourself."
    code, out = _run(project, ["git", "push", "-u", "origin", "HEAD"])
    return out or "pushed" if code == 0 else out


def create_pr(project: Path, title: str, body: str) -> str:
    blocked = _in_project(project)
    if blocked:
        return blocked
    branch = current_branch(project)
    if branch in PROTECTED:
        return "refusing to open a PR from main/master. Action: branch first."
    title = " ".join(title.strip().split())
    if len(title) < 8:
        return "pr needs Title: of at least 8 characters"
    text = (body.strip() or title) + PR_FOOTER
    code, out = _run(
        project,
        ["gh", "pr", "create", "--title", title, "--body", text],
    )
    return out or "opened pull request" if code == 0 else out


PR_FIELDS = "title,mergeable,mergeStateStatus,statusCheckRollup,author"


def read_pr_state(project: Path, number: str) -> dict:
    """What GitHub currently says about this pull request. {} when unknown."""
    code, out = _run(
        project,
        ["gh", "pr", "view", number, "--json", PR_FIELDS],
        keep_all=True,
    )
    if code != 0:
        return {}
    try:
        loaded = json.loads(out)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def merge_pr(project: Path, number: str, *, allowed: bool) -> str:
    if not allowed:
        return "merge only when the task says merge"
    if not number.isdigit():
        return "merge needs Number: (PR digits)"
    blocked = _in_project(project)
    if blocked:
        return blocked
    state = read_pr_state(project, number)
    # An empty read means gh could not answer. Merging anyway would make
    # every check here optional the moment the network hiccups.
    if not state:
        return f"cannot read #{number} from GitHub, so not merging it"
    refused = refuse_bot_merge(state, project)
    if refused:
        return f"not merging #{number}: {refused}"
    code, out = _run(
        project,
        [
            "gh",
            "pr",
            "merge",
            number,
            "--merge",
            "--subject",
            f"Merge pull request #{number}",
            "--body",
            with_co_author(f"Merged #{number}."),
        ],
    )
    return out or f"merged #{number}" if code == 0 else out
