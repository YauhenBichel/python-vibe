"""Shapes that are a secret whoever is looking at them.

These patterns had one home, in the guard that reads drafts coming back
from the model. Nothing read what was going the other way, so a run
pointed at a remote host posted whatever the harness had gathered — for
a named-file task, the whole file — with no check at all.

The same four shapes answer both questions, so they live below both:
the guard reviews what arrives, `model.outbound` reviews what leaves.
"""

from __future__ import annotations

import re

# Named rather than lumped together, so a refusal can say which one it
# saw without quoting the thing it saw.
SECRET_SHAPES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("an AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("an Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}")),
    ("a GitHub token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    (
        "a private key",
        re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    ),
)


def secret_in(text: str) -> str:
    """What secret the text contains, in words. "" when none.

    The answer never includes the match. Saying "an AWS access key" is
    enough to act on, and printing the key to explain that it leaked
    would be the leak.
    """
    for name, pattern in SECRET_SHAPES:
        if pattern.search(text):
            return name
    return ""
