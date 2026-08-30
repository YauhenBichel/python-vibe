"""Adding the import line for a name used without one."""

from __future__ import annotations

"""Mechanical fixes the 8B fails to express. Deterministic. No model.

Live 8B (29 Aug 2026): left `subtotal` unbound after a NameError task, and
spent twelve `Find:` turns that never matched `def calc(x: int, ...)`.
Those are compiler jobs. The harness does them, then runs the suite,
before the first generate. A green suite ends the run without a model.
"""
from harness.scan.names import undefined_names




def apply_missing_imports(source: str) -> str:
    """Add the import line for a well-known name used without one.

    A model writes `Path` and forgets `from pathlib import Path`. Refusing
    that and asking for a rename is wrong twice over: the name is right,
    and the repair is mechanical. Only names on a fixed list are handled,
    so nothing is guessed.
    """
    from harness.scan.names import import_for, undefined_names

    wanted = [
        line for line in (import_for(name) for name in undefined_names(source)) if line
    ]
    if not wanted:
        return source
    lines = source.splitlines()
    present = {line.strip() for line in lines}
    missing = [line for line in dict.fromkeys(wanted) if line not in present]
    if not missing:
        return source
    insert_at = 0
    if lines and lines[0].lstrip()[:3] in {'"""', "'''"}:
        quote = lines[0].lstrip()[:3]
        rest = lines[0].lstrip()[3:]
        if quote in rest:
            insert_at = 1
        else:
            for index, line in enumerate(lines[1:], 1):
                if quote in line:
                    insert_at = index + 1
                    break
    while insert_at < len(lines) and not lines[insert_at].strip():
        insert_at += 1
    return "\n".join(lines[:insert_at] + missing + [""] + lines[insert_at:]).rstrip() + "\n"
