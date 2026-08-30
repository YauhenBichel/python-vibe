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
_HOME = re.compile(r"/Users/[^/\s]+")


def redact(text: str) -> str:
    if secret_in(text) or _ALSO_REDACT.search(text):
        return "[redacted]"
    return _HOME.sub("/Users/you", text)


def append_turn(path: Path, row: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {key: redact(str(value)) for key, value in row.items()}
    if any(v == "[redacted]" for v in clean.values()):
        return
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(clean, ensure_ascii=False) + "\n")
