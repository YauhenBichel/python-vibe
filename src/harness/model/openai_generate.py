"""Call an OpenAI-compatible chat endpoint. Weights stay on that host.

The laptop harness does not change. This is how a 14B–70B that timed out
locally is reached: Hugging Face Inference, a rented vLLM box, or any
other /v1/chat/completions server. Tokens come from the environment.
They are never written into a trace, a test, or an error string.
"""

from __future__ import annotations

from harness.model.chat_backend import ChatBackend

import json
import os
import urllib.error
import urllib.request
from collections.abc import Sequence

HF_ROUTER = "https://router.huggingface.co/v1"


def chat_url(base: str) -> str:
    """POST target. Accepts a host, a /v1 root, or the full chat path."""
    base = base.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def resolve_openai_endpoint(
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> tuple[str, str]:
    """(base_url, api_key). Raises ValueError with no secret in the text."""
    base = (
        base_url
        or os.environ.get("PYTHON_VIBE_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or ""
    ).strip()
    key = (
        api_key
        or os.environ.get("PYTHON_VIBE_API_KEY")
        or os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        or os.environ.get("OPENAI_API_KEY")
        or ""
    ).strip()
    if not base and key:
        base = HF_ROUTER
    if not base:
        raise ValueError(
            "PYTHON_VIBE_BASE_URL is required for --engine openai "
            "(or set HF_TOKEN to use the Hugging Face router)"
        )
    return base.rstrip("/"), key


def looks_like_an_ollama_tag(model: str) -> bool:
    """`llama3.1:8b` names a local pull, not a model on someone's server.

    The engine falls back to the everyday Ollama name when --model is not
    given, so the first remote run sends a tag no remote host knows and
    comes back with a bare 400. Saying so is cheaper than guessing.
    """
    return ":" in model and "/" not in model


class OpenAIGenerate(ChatBackend):
    def __init__(
        self,
        model: str,
        system: str,
        *,
        max_tokens: int = 700,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.base_url, self.api_key = resolve_openai_endpoint(
            base_url=base_url, api_key=api_key
        )
        if timeout is None:
            raw = os.environ.get("PYTHON_VIBE_TIMEOUT", "180")
            try:
                timeout = float(raw)
            except ValueError:
                timeout = 180.0
        super().__init__(model, system, timeout=timeout)

    def _hint(self, code: int) -> str:
        """Say the likely cause. Never quote the key or the headers."""
        if code in {401, 403}:
            return (
                ". Check the token in PYTHON_VIBE_API_KEY or HF_TOKEN, "
                "and that it may use this host"
            )
        if code in {400, 404} and looks_like_an_ollama_tag(self.model):
            return (
                f". `{self.model}` is an Ollama tag; a remote host wants its "
                "own id, such as meta-llama/Llama-3.1-8B-Instruct. "
                "Pass --model"
            )
        return ""

    def url(self) -> str:
        return chat_url(self.base_url)

    def body(self, messages: list[dict[str, str]]) -> dict[str, object]:
        return {
            "model": self.model,
            "stream": False,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }

    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def reply_from(self, payload: dict[str, object]) -> str:
        choices = payload.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}  # type: ignore[index]
        return str(message.get("content") or "")

    def unreachable(self, exc: Exception) -> str:
        return "remote model unreachable"

    def refused(self, code: int) -> str:
        return f"remote model HTTP {code}{self._hint(code)}"
