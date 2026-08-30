"""Deterministic structure / SoC review. No model."""

from __future__ import annotations

import ast
from pathlib import Path

from harness.scan.project_brief import iter_text_files

MAX_FINDINGS = 16
GOD_DEFS = 4
CLEAN_PHRASE = "no structure findings"


def _defs(source: str) -> list[str]:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.append(node.name)
    return names


def render_design_review(project: Path, scope: str = "") -> str:
    root = project.resolve()
    python_files = [
        path
        for path, _size in iter_text_files(project, scope)
        if path.suffix == ".py"
    ]
    findings: list[str] = []
    rels = [path.relative_to(root).as_posix() for path in python_files]
    stems = {Path(rel).stem for rel in rels if "test" in rel}
    has_tests = any(rel.startswith("tests/") or "/tests/" in rel for rel in rels)
    has_lib = any(rel.startswith(("pkg/", "src/")) for rel in rels)
    if not has_tests:
        findings.append("missing tests/ — add tests/test_<module>.py beside each concern")
    if not has_lib and any(rel.startswith("scripts/") for rel in rels):
        findings.append("no pkg/ or src/ — library code should not live only in scripts/")
    for path, rel in zip(python_files, rels, strict=True):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        names = _defs(source)
        if rel.endswith("__init__.py") and names:
            findings.append(
                f"SoC: {rel} defines {', '.join(names)} — __init__.py is exports only"
            )
        if rel.startswith("scripts/") and any(name != "main" for name in names):
            extra = [name for name in names if name != "main"]
            findings.append(
                f"SoC: {rel} has {', '.join(extra)} — move library code to pkg/<noun>.py"
            )
        if "test" not in rel and not rel.endswith("__init__.py") and len(names) >= GOD_DEFS:
            findings.append(
                f"god module: {rel} has {len(names)} top-level functions — "
                "Action: edit Path: pkg/<new_concern>.py with one function"
            )
        if (
            rel.startswith(("pkg/", "src/"))
            and not rel.endswith("__init__.py")
            and f"test_{Path(rel).stem}" not in stems
        ):
            findings.append(f"missing tests: no tests/test_{Path(rel).stem}.py for {rel}")
        if len(findings) >= MAX_FINDINGS:
            break
    if not findings:
        findings.append(f"{CLEAN_PHRASE} in scope — pkg/ and tests/ look split")
    lines = ["design review (deterministic, not a model opinion):"]
    lines.extend(f"- {item}" for item in findings[:MAX_FINDINGS])
    return "\n".join(lines)


def design_is_clean(report: str) -> bool:
    """True when the last scan reported no structure findings."""
    return CLEAN_PHRASE in (report or "")
