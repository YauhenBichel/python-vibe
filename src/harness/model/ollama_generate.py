"""Call a local/cloud Ollama model. Weights stay in Ollama; this process is tiny."""

from __future__ import annotations

# How much the model is told it may read. Ollama's own default is 4096,
# small enough that a twenty-step run silently lost its opening.
CONTEXT_TOKENS = 8192

import json
import os
import urllib.error
import urllib.request
from collections.abc import Sequence


class OllamaGenerate:
    def __init__(
        self,
        model: str,
        system: str,
        host: str | None = None,
        timeout: float = 180,
    ) -> None:
        self.model = model
        self.system = system
        self.timeout = timeout
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip(
            "/"
        )

    num_ctx = CONTEXT_TOKENS

    def __call__(
        self, prompt: str, history: Sequence[dict[str, str]] | None = None
    ) -> str:
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return self.send(messages)

    def send(self, messages: list[dict[str, str]]) -> str:
        """Post exactly these messages. The caller decides what they are.

        The conversation is assembled by `harness.memory`, which knows
        what to keep and what to let go. This only sends it.
        """
        body = json.dumps(
            {
                "model": self.model,
                "stream": False,
                "messages": messages,
                # Say the size rather than take the server's default. That
                # default is 4096 for weights that accept 131072, and a run
                # crossing it had its oldest messages dropped by the server
                # without saying so. The harness decides what to forget.
                "options": {"num_ctx": self.num_ctx},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"ollama {self.host} unreachable: {exc}") from exc
        message = payload.get("message") or {}
        return str(message.get("content") or "")

    def healthy(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=2) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
