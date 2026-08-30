"""Deterministic guard for python-vibe drafts. No model. No network.

The fine-tune owns style. This only stops a few classes of output that
must not ship: empty, leaked secrets, pipe-to-shell, or a lesion diagnosis
(wrong surface — this is a coding harness).
"""

from __future__ import annotations

import re

from harness.guard.types import Finding, Outcome
from harness.secrets import SECRET_SHAPES

RULESET_VERSION = "python-vibe-harness@0.1.0"
MAX_CHARS = 8000

_FLAGS = re.IGNORECASE

_RULES: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "PV001",
        "block",
        re.compile(r"^\s*$"),
    ),
    (
        "PV002",
        "block",
        re.compile(
            "|".join(f"(?:{p.pattern})" for _name, p in SECRET_SHAPES)
        ),
    ),
    (
        "PV003",
        "block",
        re.compile(r"(curl|wget)\s+[^\n|]{0,200}\|\s*(?:ba)?sh\b", _FLAGS),
    ),
    (
        "PV004",
        "block",
        re.compile(
            r"(\b(this|that|it)(?:'s|\s+is)\s+(a\s+|an\s+)?"
            r"(melanoma|basal cell carcinoma|skin cancer)\b"
            r"|\byou have\s+(a\s+|an\s+)?(melanoma|skin cancer)\b)",
            _FLAGS,
        ),
    ),
)


class PythonVibeGuard:
    def review(self, text: str) -> Outcome:
        findings: list[Finding] = []
        if len(text) > MAX_CHARS:
            findings.append(
                Finding("PV005", "block", f"output length {len(text)} > {MAX_CHARS}")
            )
        for rule_id, severity, pattern in _RULES:
            match = pattern.search(text)
            if match:
                findings.append(Finding(rule_id, severity, match.group(0)[:80]))
        if findings:
            return Outcome("block", None, tuple(findings), RULESET_VERSION)
        return Outcome("pass", text, (), RULESET_VERSION)

    def check(self, text: str, red_flags: list[str] | None = None) -> Outcome:
        del red_flags
        return self.review(text)
