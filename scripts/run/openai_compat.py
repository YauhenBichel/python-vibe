#!/usr/bin/env python3
"""OpenAI-compatible proxy in front of Ollama for a local editor.

Ollama already serves http://127.0.0.1:11434/v1/chat/completions.
This process binds 127.0.0.1:8081, forwards that API, and refuses to
advertise the 0.5B sidecar as the everyday model.

  ollama pull llama3.1:8b
  PYTHONPATH=src python scripts/run/openai_compat.py

Editor: OpenAI Base URL http://127.0.0.1:8081/v1  — API key `ollama`
Model: llama3.1:8b  (see docs/local-editor.md)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from finetune.everyday import DEFAULT_EVERYDAY_OLLAMA  # noqa: E402
from harness.model.ollama_generate import OllamaGenerate  # noqa: E402
from harness.model.openai_compat import (  # noqa: E402
    models_payload,
    ollama_openai_url,
    parse_chat_body,
    warn_tiny,
)

HOST = os.environ.get("OPENAI_COMPAT_HOST", "127.0.0.1")
PORT = int(os.environ.get("OPENAI_COMPAT_PORT", "8081"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _json(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/health", "/v1/models", "/models"}:
            self._json(200, models_payload(DEFAULT_EVERYDAY_OLLAMA))
            return
        self._json(404, {"error": {"message": "not found"}})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/v1/chat/completions", "/chat/completions"}:
            self._json(404, {"error": {"message": "not found"}})
            return
        length = int(self.headers.get("Content-Length") or "0")
        if length > 32 * 1024:
            self._json(413, {"error": {"message": "body too large"}})
            return
        try:
            parsed = parse_chat_body(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": {"message": str(exc)}})
            return
        note = warn_tiny(parsed["model"])
        if note:
            print(note, file=sys.stderr)
        backend = OllamaGenerate(parsed["model"], "")
        url = ollama_openai_url(backend.host)
        req = urllib.request.Request(
            url,
            data=json.dumps(
                {
                    "model": parsed["model"],
                    "messages": parsed["messages"],
                    "stream": False,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            self._json(exc.code, {"error": {"message": exc.reason}})
            return
        except urllib.error.URLError as exc:
            self._json(502, {"error": {"message": f"ollama unreachable: {exc}"}})
            return
        self._json(200, payload)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(
        f"openai-compat {HOST}:{PORT} → ollama  model default {DEFAULT_EVERYDAY_OLLAMA}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
