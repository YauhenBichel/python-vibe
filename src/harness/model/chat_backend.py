"""What every model this project talks to has in common.

Both hosts speak the same shape: post a list of messages, read one reply
out of what comes back. Sixty-four per cent of the two files was the
same lines — building the request, opening it, turning a failure into a
message, pulling the text out.

What actually differs is small and named here: where to post, what the
body looks like, what headers it needs, where the reply sits in the
answer, and what a status code means. A new host is those five things,
not another copy of the transport.

This is a base class rather than a function because the pieces vary
together and are named by what they are. Most of this project is plain
functions, which is right when a thing takes values and returns one; a
model backend holds a host, a model name and a timeout, and answers
several questions about them.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any


class ChatBackend:
    """One model, reachable over HTTP, that answers a list of messages."""

    def __init__(self, model: str, system: str, *, timeout: float) -> None:
        self.model = model
        self.system = system
        self.timeout = timeout

    # -- what a host has to say for itself -----------------------------

    def url(self) -> str:
        raise NotImplementedError

    def body(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        raise NotImplementedError

    def headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def reply_from(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError

    def unreachable(self, exc: Exception) -> str:
        return f"{self.model} unreachable"

    def refused(self, code: int) -> str:
        return f"remote model HTTP {code}"

    def before_send(self, messages: list[dict[str, str]]) -> None:
        """Last look at what is about to leave. Raise to stop it.

        Local hosts have nothing to check, so this does nothing by
        default. A backend that posts somewhere else overrides it.
        """

    # -- what they all do the same way ---------------------------------

    def __call__(
        self, prompt: str, history: Sequence[dict[str, str]] | None = None
    ) -> str:
        """Answer one prompt, with earlier turns in front of it."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.system}
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return self.send(messages)

    def send(self, messages: list[dict[str, str]]) -> str:
        """Post exactly these messages. The caller decides what they are.

        The conversation is assembled by `harness.memory`, which knows
        what to keep and what to let go. This only sends it.
        """
        self.before_send(messages)
        request = urllib.request.Request(
            self.url(),
            data=json.dumps(self.body(messages)).encode("utf-8"),
            headers=self.headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as answer:
                payload = json.loads(answer.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # `from None` on purpose: the original carries the full URL,
            # and a token can be in it.
            raise RuntimeError(self.refused(exc.code)) from None
        except urllib.error.URLError as exc:
            raise RuntimeError(self.unreachable(exc)) from exc
        return self.reply_from(payload)
