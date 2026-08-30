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

# "Bump x from 7 to 9", "chore(deps): bump x from 1.2.3 to 1.3.0".
_BUMP = re.compile(
    r"\bbump\s+(?P<what>\S+)\s+from\s+(?P<old>v?[\w.\-]+)\s+to\s+(?P<new>v?[\w.\-]+)",
    re.I,
)
_LEADING_NUMBER = re.compile(r"^v?(\d+)")


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


def _check_state(pull: dict) -> tuple[list[str], list[str]]:
    """(failing, unfinished) check names."""
    failing, unfinished = [], []
    for check in pull.get("statusCheckRollup") or []:
        name = str(check.get("name") or check.get("context") or "a check")
        conclusion = (check.get("conclusion") or "").upper()
        state = (check.get("state") or check.get("status") or "").upper()
        if conclusion in {"FAILURE", "TIMED_OUT", "CANCELLED", "ACTION_REQUIRED"}:
            failing.append(name)
        elif conclusion in {"", "NEUTRAL"} and state in {
            "PENDING", "IN_PROGRESS", "QUEUED", "EXPECTED", "WAITING", ""
        }:
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
