"""What may leave this machine, and what was sent when it did.

The default engine talks to Ollama on this laptop, so nothing leaves and
none of this runs. `--engine openai` posts to a host somebody else runs,
and until now nothing looked at the bytes on the way out. The guard read
drafts coming back and never the prompt going out.

Two questions are answered here. May this go: not if it carries a secret
shape, and not if it is far larger than a task should need. And what
went: a sentence a person can check against what they expected, without
the prompt itself being printed back at them.
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

from harness.secrets import secret_in

# Hosts that are this machine. Sending to one of these is not sending.
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1", "0.0.0.0", ""})

# A single large file is ordinary. A whole repository is a mistake, and
# the point of a cap is to catch the mistake, not to ration the work.
DEFAULT_MAX_CHARS = 200_000


def leaves_this_machine(base_url: str) -> bool:
    """True when this host is somebody else's."""
    host = urlparse(base_url if "//" in base_url else f"//{base_url}").hostname
    return (host or "") not in LOCAL_HOSTS


def max_chars() -> int:
    """The cap, which a caller who means it can raise."""
    try:
        return int(os.environ.get("PYTHON_VIBE_MAX_SEND", DEFAULT_MAX_CHARS))
    except ValueError:
        return DEFAULT_MAX_CHARS


def _joined(messages: list[dict[str, str]]) -> str:
    return "\n".join(str(m.get("content") or "") for m in messages)


def refuse_to_send(messages: list[dict[str, str]], base_url: str) -> str:
    """Why these messages must not go to that host. "" when they may."""
    if not leaves_this_machine(base_url):
        return ""
    text = _joined(messages)
    found = secret_in(text)
    if found:
        return (
            f"Refusing to send: the prompt contains {found}. It would go "
            "to a host this machine does not control. Take it out of the "
            "file, or run without --engine openai."
        )
    size = len(text)
    cap = max_chars()
    if size > cap:
        return (
            f"Refusing to send {size} characters to a remote host; the "
            f"limit is {cap}. Narrow the task with --scope, or raise "
            "PYTHON_VIBE_MAX_SEND if that is really the intent."
        )
    return ""


def what_was_sent(messages: list[dict[str, str]], base_url: str) -> str:
    """One line naming where it went and how much of it. "" when local.

    Deliberately a size and a destination rather than the prompt. A
    person who wants to know whether their file went can read this; a
    person who wants the prompt back has it already.
    """
    if not leaves_this_machine(base_url):
        return ""
    host = urlparse(base_url if "//" in base_url else f"//{base_url}").hostname
    text = _joined(messages)
    return (
        f"sent {len(text)} characters in {len(messages)} message(s) to {host}"
    )
