"""Report why a project is difficult to read, and what to change first.

Four problems are detected, listed here in the order they are worth
fixing:

* `cycle`    - two modules import each other, so neither can be read alone.
* `flat`     - one directory holds many modules with no grouping.
* `god`      - one module is much larger than the others around it.
* `no-tests` - the project contains no test files.

Only the first problem is turned into an instruction. A model given four
instructions at once tends to change four things at once; a model given one
instruction changes one thing, which can then be checked.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from harness.paths import rel_posix
from harness.scan.project_scan import SKIP_DIR

FLAT_MAX_MODULES = 12
# A module far bigger than the ones beside it. This is not the same
# thing as a god module and no longer says it is: `scan.design` calls a
# file with too many top-level functions a god module, and the two
# disagreed in both directions. A 300-byte file with four functions is
# one by that rule and not by this; a 7 KB file holding two long
# functions is one by this and not by that, and since the design review
# started reporting long functions, that case has a better answer.
OUTSIZED_RATIO = 3
OUTSIZED_MIN_BYTES = 6000
MAX_FINDINGS = 4


@dataclass(frozen=True)
class Finding:
    """One structural problem found in a project.

    Fields:
        kind: "cycle", "flat", "outsized" or "no-tests".
        detail: what was found, naming the files involved.
        move: the change to make, written as an instruction.
    """

    kind: str
    detail: str
    move: str


def _modules(project: Path) -> list[Path]:
    root = project.resolve()
    return [
        path
        for path in sorted(root.rglob("*.py"))
        if not any(part in SKIP_DIR for part in path.parts)
    ]


def _module_name(path: Path, root: Path) -> str:
    """Dotted name for a file, as an import inside this project spells it."""
    rel = path.resolve().relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _local_imports(path: Path, root: Path) -> set[str]:
    """Dotted modules this file imports, relative imports resolved.

    The first version kept only the last component of each import, and
    the graph was keyed on the file name. Two things followed on a real
    repository, where the same file name appears many times: distinct
    modules merged into one node, and `rich.console` counted as an
    import of a local `console.py`. Every cycle reported on a 4,580-file
    project was one of those, four out of four.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return set()
    package = _module_name(path, root).rsplit(".", 1)
    package = package[0] if len(package) == 2 else ""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                # `from . import x` and `from .mod import y` are relative
                # to the package this file sits in.
                base = package.split(".") if package else []
                climb = node.level - 1
                base = base[: len(base) - climb] if climb else base
                stem = ".".join(part for part in (*base, node.module or "") if part)
            else:
                stem = node.module or ""
            if not stem:
                continue
            names.add(stem)
            for alias in node.names:
                names.add(f"{stem}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
    return names


def find_cycles(project: Path) -> list[tuple[str, str]]:
    root = project.resolve()
    modules = _modules(project)
    by_name = {_module_name(path, root): path for path in modules}

    # A sub-project keeps its own root: demo/orders/src/report.py is
    # imported as `src.report` from inside demo/orders. Accept a dotted
    # path that is the tail of exactly one module, so that still counts,
    # while an ambiguous tail counts for nothing.
    tails: dict[str, list[str]] = {}
    for name in by_name:
        parts = name.split(".")
        for start in range(1, len(parts)):
            tails.setdefault(".".join(parts[start:]), []).append(name)

    def resolve(imported: set[str], self_name: str) -> set[str]:
        found = set()
        for item in imported:
            if item in by_name:
                found.add(item)
                continue
            # Only a dotted path. A bare top-level name competes with
            # every package on the machine: `import logging` beside a
            # local `infrastructure/logging/` package resolved to it and
            # invented two cycles on a real repository.
            if "." not in item:
                continue
            unique = tails.get(item, ())
            if len(unique) == 1:
                found.add(unique[0])
        return found - {self_name}

    graph = {
        name: resolve(_local_imports(path, root), name)
        for name, path in by_name.items()
    }
    pairs = {
        tuple(sorted((name, other)))
        for name, deps in graph.items()
        for other in deps
        if name in graph.get(other, set())
    }
    return sorted(
        (rel_posix(by_name[left], root), rel_posix(by_name[right], root))
        for left, right in pairs
    )


def find_flat_packages(project: Path) -> list[tuple[str, int]]:
    root = project.resolve()
    counts: dict[str, int] = {}
    for path in _modules(project):
        parent = path.parent
        key = rel_posix(parent, root) if parent != root else "."
        counts[key] = counts.get(key, 0) + 1
    return sorted(
        ((name, n) for name, n in counts.items() if n > FLAT_MAX_MODULES),
        key=lambda item: (-item[1], item[0]),
    )


def find_outsized_modules(project: Path) -> list[tuple[str, int]]:
    root = project.resolve()
    sizes = []
    for path in _modules(project):
        try:
            sizes.append((rel_posix(path, root), path.stat().st_size))
        except OSError:
            continue
    if len(sizes) < 3:
        return []
    median = sorted(size for _rel, size in sizes)[len(sizes) // 2]
    return sorted(
        (
            (rel, size)
            for rel, size in sizes
            if size >= OUTSIZED_MIN_BYTES and size > median * OUTSIZED_RATIO
        ),
        key=lambda item: -item[1],
    )


def has_tests(project: Path) -> bool:
    root = project.resolve()
    return any(
        path.name.startswith("test_")
        for path in root.rglob("test_*.py")
        if not any(part in SKIP_DIR for part in path.parts)
    )


def review_layout(project: Path) -> list[Finding]:
    out: list[Finding] = []
    for left, right in find_cycles(project):
        out.append(
            Finding(
                "cycle",
                f"{left} and {right} import each other",
                f"Move what they share into a new module both import. "
                f"Action: grep Query: def .*  Path: {left}",
            )
        )
    for name, count in find_flat_packages(project):
        out.append(
            Finding(
                "flat",
                f"{name}/ holds {count} modules with no grouping",
                f"Group {name}/ by what each module is for, one folder per "
                "job, and give each folder an __init__.py that says so.",
            )
        )
    for rel, size in find_outsized_modules(project):
        out.append(
            Finding(
                "outsized",
                f"{rel} is {size // 1024} KB — far larger than its neighbours",
                f"Action: read Path: {rel} and split the one group of "
                "functions that does not belong with the rest.",
            )
        )
    if not has_tests(project):
        out.append(
            Finding(
                "no-tests",
                "no test_*.py anywhere in this project",
                "Action: patch Path: tests/test_smoke.py with one unittest "
                "for the function you touch next.",
            )
        )
    return out[:MAX_FINDINGS]


def render_layout(project: Path) -> str:
    findings = review_layout(project)
    if not findings:
        return (
            "layout: no cycles, no oversized package, no outsized module, tests "
            "present. Nothing to restructure — do the task."
        )
    lines = [f"layout: {len(findings)} finding(s), worst first."]
    for finding in findings:
        lines.append(f"  [{finding.kind}] {finding.detail}")
    lines.append("")
    lines.append(f"Next move (do only this one): {findings[0].move}")
    return "\n".join(lines)
