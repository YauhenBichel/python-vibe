"""Call a local/cloud Ollama model. Weights stay in Ollama; this process is tiny."""

from __future__ import annotations

from harness.model.chat_backend import ChatBackend

# How much the model is told it may read. Ollama's own default is 4096,
# small enough that a twenty-step run silently lost its opening.
CONTEXT_TOKENS = 8192

import json
import os
import urllib.error
import urllib.request
from collections.abc import Sequence


class OllamaGenerate(ChatBackend):
    def __init__(
        self,
        model: str,
        system: str,
        host: str | None = None,
        timeout: float = 180,
    ) -> None:
        super().__init__(model, system, timeout=timeout)
        self.host = (host or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip(
            "/"
        )

    num_ctx = CONTEXT_TOKENS

    def url(self) -> str:
        return f"{self.host}/api/chat"

    def body(self, messages: list[dict[str, str]]) -> dict[str, object]:
        return {
            "model": self.model,
            "stream": False,
            "messages": messages,
            # Say the size rather than take the server's default. That
            # default is 4096 for weights that accept 131072, and a run
            # crossing it had its oldest messages dropped by the server
            # without saying so. The harness decides what to forget.
            "options": {"num_ctx": self.num_ctx},
        }

    def reply_from(self, payload: dict[str, object]) -> str:
        message = payload.get("message") or {}
        return str(message.get("content") or "")  # type: ignore[union-attr]

    def unreachable(self, exc: Exception) -> str:
        return f"ollama {self.host} unreachable: {exc}"

    def healthy(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=2) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
