"""Reject an action that has already been run with the same arguments.

A model that is unsure what to do next will often repeat its last search.
The tool returns the same output, the model is no better informed, and the
step budget is spent.

Read-only actions are keyed by their arguments. Patches are keyed by their
exact Find, Replace, and Append body rather than their path, because sending
the same mutation to another file is still repetition. Running the tests
again after a change remains progress and is never rejected here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

EXPLORE = frozenset({"glob", "grep", "read", "map", "locate", "plan", "skill"})
_NEXT = {
    "grep": "Action: read Path: one file from those hits.",
    "glob": "Action: read Path: one file from that list.",
    "map": "Action: grep Query: a symbol from the task.",
    "locate": "Action: read Path: the file it named, or Action: done.",
    "read": "Action: done with the answer, or Action: patch with a fix.",
    "plan": "Take the first explore action now.",
    "skill": "Copy the Action: block from the skill.",
}


def turn_key(turn) -> tuple[str, ...]:
    return (
        turn.action,
        turn.path.strip(),
        turn.query.strip(),
        turn.pattern.strip(),
        turn.scope.strip(),
        turn.name.strip(),
    )


def patch_key(turn) -> tuple[str, ...] | None:
    """The exact mutation a patch proposes, independent of destination."""
    if turn.action != "patch":
        return None
    body = tuple(
        getattr(turn, field, "") for field in ("find", "replace", "append")
    )
    if not any(body):
        return None
    return ("patch", *body)


@dataclass
class LoopGuard:
    """Remembers explore actions and patch bodies already seen in this run."""

    seen: set[tuple[str, ...]] = field(default_factory=set)

    def check(self, turn) -> str:
        if turn is None:
            return ""
        patch = patch_key(turn)
        if patch is not None:
            if patch in self.seen:
                return (
                    "already proposed that exact patch body. It was already "
                    "applied or refused; repeating it will not help. Read the "
                    "earlier result and take a different action."
                )
            self.seen.add(patch)
            return ""
        if turn.action not in EXPLORE:
            return ""
        key = turn_key(turn)
        if key in self.seen:
            hint = _NEXT.get(turn.action, "Take a different action.")
            detail = turn.path or turn.query or turn.pattern or turn.name
            return (
                f"already ran that exact {turn.action}"
                + (f" ({detail})" if detail else "")
                + f". The result has not changed. {hint}"
            )
        self.seen.add(key)
        return ""
