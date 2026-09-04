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


def refuse_bot_merge(pull: dict) -> str:
    """Why this pull request needs a person. "" when nothing objects."""
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
        return (
            f"{what} {was} to {now} is a major version bump. That is where "
            "breaking changes are allowed to live, and the title never "
            "says so. Read the release notes and merge it by hand."
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
