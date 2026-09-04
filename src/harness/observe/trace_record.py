"""Append redacted agent turns. Never store raw keys or home paths."""

from __future__ import annotations

import json
import re
from pathlib import Path

from harness.secrets import secret_in

# The four shapes are shared with the guard and the outbound check, so
# a shape learned once is known everywhere. These two are extra to this
# file: a trace is written to disk and kept, so it redacts wider than a
# refusal needs to.
_ALSO_REDACT = re.compile(r"(HF_TOKEN=|-----BEGIN )")
_HOME = re.compile(r"/(Users|home)/[^/\s]+")
_URL_HOST = re.compile(r"\b([a-z][a-z0-9+.-]*://)(?:[^/@\s]+@)?([^/\s]+)", re.IGNORECASE)
# A hostname with no scheme in front of it. `.home` and `.local` are
# deliberately absent from the list without a port: `Path.home()` is
# standard Python and `settings.local.json` is a real file name, and a
# trace is training data, so mangling either teaches the model a
# mistake. With a port there is no ambiguity — `box.local:8443` is a
# host and `Path.home()` never carries one.
_BARE_HOST = re.compile(
    r"\b[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*"
    r"(?:\.(?:lan|internal|corp)(?::\d+)?|\.(?:local|home):\d+)\b"
)


def redact(text: str) -> str:
    if secret_in(text) or _ALSO_REDACT.search(text):
        return "[redacted]"
    text = _HOME.sub(lambda match: f"/{match.group(1)}/you", text)
    text = _URL_HOST.sub(lambda match: f"{match.group(1)}[host]", text)
    return _BARE_HOST.sub("[host]", text)


# Where a run writes its turns when nobody says otherwise. Inside the
# project, because the traces are about that project's code, and hidden
# because nobody wants it in a listing.
TRACE_DIR = ".python-vibe"
TRACE_FILE = "traces.jsonl"


def default_trace_path(project: Path) -> Path:
    """Where turns go when no --record is given."""
    return Path(project) / TRACE_DIR / TRACE_FILE


def append_turn(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {key: redact(str(value)) for key, value in row.items()}
    if any(v == "[redacted]" for v in clean.values()):
        return
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(clean, ensure_ascii=False) + "\n")
