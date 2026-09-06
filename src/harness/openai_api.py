"""The shapes an OpenAI-compatible client sends and expects.

Request parsing and reply payloads for `server.py`, so an editor can
talk to this project using the API it already speaks.

This is the request and reply shape, not the model. It knows what a chat request
looks like and nothing about weights, which is why it sits beside the
server rather than inside `model/`: that package is only the code that
talks to a model, and the CLI and the server do not reach into it.
"""

from __future__ import annotations

import json
from typing import Any

from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA, is_tiny_model


def parse_chat_body(raw: bytes) -> dict[str, Any]:
    body = json.loads(raw or b"{}")
    if not isinstance(body, dict):
        raise ValueError("json object required")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages required")
    model = str(body.get("model") or DEFAULT_EVERYDAY_OLLAMA)
    return {"model": model, "messages": messages, "stream": bool(body.get("stream"))}


def warn_tiny(model: str) -> str | None:
    if is_tiny_model(model):
        return (
            f"{model} is the 0.5B sidecar. Everyday laptop use should be "
            f"{DEFAULT_EVERYDAY_OLLAMA} (or qwen2.5-coder:7b / 14b)."
        )
    return None


def ollama_openai_url(host: str) -> str:
    return host.rstrip("/") + "/v1/chat/completions"


def models_payload(model: str) -> dict[str, Any]:
    return {
        "object": "list",
        "data": [{"id": model, "object": "model", "owned_by": "ollama"}],
    }


def last_user_text(messages: list[Any]) -> str:
    """The last user turn, as plain text. Editors send a string or parts."""
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                str(item.get("text") or "")
                for item in content
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            return "\n".join(part for part in parts if part).strip()
    return ""


def chat_completion_payload(content: str, model: str) -> dict[str, Any]:
    return {
        "id": "py-harness",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "model": model,
    }
