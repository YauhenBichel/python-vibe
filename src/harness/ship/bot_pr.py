"""Whether a pull request opened by a bot may be merged without a reader.

Dependency bots open the same pull request shape every week, and most of
them are dull enough to merge on sight. The one that is not dull looks
exactly like the ones that are.

`Bump actions/github-script from 7 to 9` reads like the rest. Its
release notes say `require('@actions/github')` stops working and that
`getOctokit` becomes an injected parameter, so a workflow that used
either breaks on merge. The title carries none of that. What it does
carry is `7` and `9`, and a first number that changed is the whole
signal: a major bump is where breaking changes are allowed to live.

So this refuses on the shape of the version, on a red or unfinished
check, and on anything GitHub already says is not mergeable. It never
approves; it only fails to object.
"""

from __future__ import annotations

import re
from pathlib import Path

# The bot writes two shapes, and reading only one of them missed a
# major bump entirely. Actions get "bump x from 7 to 9"; Python
# requirements get "update x requirement from >=0.26.0 to >=1.29.0".
_BUMP = re.compile(
    r"\b(?:bump|update)\s+(?P<what>\S+)"
    r"(?:\s+requirement)?"
    r"\s+from\s+(?P<old>[<>=~^!]*\s*v?[\w.\-]+)"
    r"\s+to\s+(?P<new>[<>=~^!]*\s*v?[\w.\-]+)",
    re.I,
)
# A requirement carries its comparator: `>=0.26.0` is version 0, not a
# string starting with a bracket.
_LEADING_NUMBER = re.compile(r"^[<>=~^!\s]*v?(\d+)")


def bump_in(title: str) -> tuple[str, str, str] | None:
    """(what, old version, new version) from a bot's title, or None."""
    found = _BUMP.search(title or "")
    if not found:
        return None
    return found.group("what"), found.group("old"), found.group("new")


def is_a_major_bump(old: str, new: str) -> bool:
    """Did the first number change?

    Unparseable versions are not called major. Refusing everything this
    cannot read would make the check about the parser rather than about
    the risk, and the other reasons still apply.
    """
    before, after = _LEADING_NUMBER.match(old), _LEADING_NUMBER.match(new)
    if not before or not after:
        return False
    return before.group(1) != after.group(1)


# CANCELLED, SKIPPED and STALE are deliberately absent from both sets
# below. A cancelled run did not fail; it gave no answer, usually
# because a newer push superseded it. Naming it as a failure refused two
# pull requests whose checks had passed.
_FAILED = {"FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "STARTUP_FAILURE"}
_RUNNING = {"PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED", "WAITING", ""}


def latest_of_each(pull: dict) -> list[dict]:
    """One entry per check name: the most recent run of it.

    A pull request keeps every run of a check, not just the current one.
    Pushing again cancels the run in flight and starts another, so the
    rollup holds a cancelled entry and a successful entry under the same
    name. Reading them all as equal reported "checks are failing: readme"
    on two pull requests whose readme check had passed forty seconds
    after being superseded.
    """
    newest: dict[str, dict] = {}
    for check in pull.get("statusCheckRollup") or []:
        name = str(check.get("name") or check.get("context") or "a check")
        when = str(check.get("completedAt") or check.get("startedAt") or "")
        seen = newest.get(name)
        if seen is None or when >= str(
            seen.get("completedAt") or seen.get("startedAt") or ""
        ):
            newest[name] = check
    return [newest[name] for name in sorted(newest)]


def _check_state(pull: dict) -> tuple[list[str], list[str]]:
    """(failing, unfinished) check names, counting each check once."""
    failing, unfinished = [], []
    for check in latest_of_each(pull):
        name = str(check.get("name") or check.get("context") or "a check")
        conclusion = (check.get("conclusion") or "").upper()
        state = (check.get("state") or check.get("status") or "").upper()
        if conclusion in _FAILED:
            failing.append(name)
        elif conclusion in {"", "NEUTRAL"} and state in _RUNNING:
            unfinished.append(name)
    return sorted(set(failing)), sorted(set(unfinished))


def refuse_bot_merge(pull: dict, project: Path | None = None) -> str:
    """Why this pull request needs a person. "" when nothing objects.

    `project` lets a major bump be answered rather than only refused.
    Refusing every one of them scored nought for five here: five action
    bumps were merged, every workflow stayed green, and the rule caught
    nothing. A refusal nobody needs is a refusal that gets switched off.

    What the pull request's own checks prove is that the workflows they
    ran still work. If every workflow using the bumped action ran green
    here, the thing that would break has already been exercised. If some
    did not — `Pages` is skipped on a pull request, `Celebrate merge`
    only runs on merge — then nothing was proved and a person reads it.
    """
    failing, unfinished = _check_state(pull)
    if failing:
        return f"checks are failing: {', '.join(failing)}"
    if unfinished:
        return f"checks have not finished: {', '.join(unfinished)}"
    mergeable = (pull.get("mergeable") or "").upper()
    if mergeable == "CONFLICTING":
        return "this branch conflicts with the base branch"
    # The durable reason comes before the transient one. A major bump is
    # true whatever GitHub is still working out, and it is the answer the
    # person needs; being told to ask again would waste the trip.
    bump = bump_in(str(pull.get("title") or ""))
    if bump and is_a_major_bump(bump[1], bump[2]):
        what, was, now = bump
        unproven = (
            unproven_workflows(project, pull, what) if project is not None else None
        )
        if unproven == []:
            # Every workflow that uses it ran green on this very pull
            # request. There is nothing left for a person to check.
            return ""
        where = f" It is used by {', '.join(unproven)}, which this pull " \
                "request did not run." if unproven else ""
        return (
            f"{what} {was} to {now} is a major version bump. That is where "
            "breaking changes are allowed to live, and the title never "
            f"says so.{where} Read the release notes and merge it by hand."
        )
    state = (pull.get("mergeStateStatus") or "").upper()
    if state in {"BLOCKED", "DIRTY", "BEHIND", "DRAFT"}:
        return f"GitHub will not merge it yet: {state.lower()}"
    # GitHub works mergeability out when asked, not in advance, so the
    # first read of a fresh pull request often says nothing. Nothing is
    # not the same as yes.
    if mergeable in {"", "UNKNOWN"} or state in {"", "UNKNOWN"}:
        return "GitHub has not worked out yet whether this merges; ask again"
    return ""


# Where a repository keeps the workflows a bumped action might appear in.
WORKFLOW_DIR = Path(".github/workflows")
_WORKFLOW_NAME = re.compile(r"^name:\s*(.+?)\s*$", re.M)


def workflows_using(project: Path, action: str) -> dict[str, str]:
    """{workflow name: file name} for every workflow naming this action.

    An action is bumped by its repository path, `actions/checkout`, and
    that is exactly the string a workflow writes in its `uses:` line.
    """
    found: dict[str, str] = {}
    root = Path(project) / WORKFLOW_DIR
    if not root.is_dir():
        return found
    for path in sorted(root.glob("*.y*ml")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if action not in text:
            continue
        named = _WORKFLOW_NAME.search(text)
        found[named.group(1) if named else path.stem] = path.name
    return found


def workflows_that_passed(pull: dict) -> set[str]:
    """Workflows this pull request actually ran green.

    A check that was skipped or cancelled proves nothing about the
    workflow it belongs to, which is the whole point: `Pages / build`
    comes back SKIPPED on a pull request, so a green run says nothing
    about whether the page still deploys.
    """
    passed: set[str] = set()
    failed: set[str] = set()
    for check in latest_of_each(pull):
        name = str(check.get("workflowName") or "")
        if not name:
            continue
        if (check.get("conclusion") or "").upper() == "SUCCESS":
            passed.add(name)
        else:
            failed.add(name)
    return passed - failed


def unproven_workflows(project: Path, pull: dict, action: str) -> list[str] | None:
    """Workflows using this action that the pull request did not exercise.

    Empty means every workflow touching the action ran green here, so
    the bump is already tested by the thing that would break.

    **None means no workflow uses it at all**, which is not the same
    thing and must not be read as one. A Python dependency appears in no
    workflow, so an empty list would have waved through every
    `huggingface-hub 0 to 1` on the grounds that nothing it touches
    failed — when nothing it touches was looked at.
    """
    using = workflows_using(project, action)
    if not using:
        return None
    green = workflows_that_passed(pull)
    return sorted(name for name in using if name not in green)
