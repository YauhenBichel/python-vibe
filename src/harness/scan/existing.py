"""What the project already has that the task is about.

A run asked to check a prompt for a leaked credential and wrote a
function that looked for a variable name rather than the shape of one,
and called it from nowhere. The shape was already in the tree, in
`secrets.py`, under the same words the task had used. The preamble the
model was given ran to twelve thousand characters and named neither the
file nor the function.

This module deliberately avoids quoting the words that case turned on.
A search that matches its own source is a search that reports itself.

Nothing was wrong with the model that a search would not have fixed. So
the search happens here, before the model starts: take the phrases out
of the task, find the ones that are rare in this project, and say where
they already appear. Rare is the whole trick — "add a function" matches
everything and means nothing.
"""

from __future__ import annotations

import re
from pathlib import Path

from harness.scan.project_scan import SKIP_DIR

# Words that carry no subject. A phrase built only from these is not
# worth searching for.
FILLER = frozenset(
    {
        "add", "also", "and", "any", "are", "back", "call", "called", "can",
        "change", "check", "code", "create", "does", "file", "files", "fix",
        "for", "from", "function", "has", "have", "how", "into", "make",
        "move", "must", "need", "new", "not", "one", "only", "out", "put",
        "return", "returns", "run", "should", "test", "tests", "that",
        "the", "then", "this", "to", "use", "used", "using", "when",
        "where", "which", "with", "write", "you",
    }
)

# A phrase in more files than this is common vocabulary, not a pointer.
MOST_FILES = 3
# And one in no file is not a pointer either.
FEWEST_FILES = 1


def phrases(task: str) -> list[str]:
    """Two-word phrases from the task that might name something real."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9_]+", task.lower())]
    found = []
    for first, second in zip(words, words[1:], strict=False):
        if first in FILLER or second in FILLER:
            continue
        if len(first) < 3 or len(second) < 3:
            continue
        found.append(f"{first} {second}")
    return found


def _searchable(project: Path) -> list[Path]:
    """Source files only. A test names every subject in the project."""
    return [
        path
        for path in sorted(Path(project).rglob("*.py"))
        if not any(part in SKIP_DIR or part.startswith(".") for part in path.parts)
        and not path.name.endswith(".bak")
        and not path.name.startswith("test_")
        and "tests" not in path.parts
    ]


def _ranked_hits(
    project: Path, task: str, *, skip: str = ""
) -> list[tuple[str, list[tuple[str, int]]]]:
    """Rare phrases from the task, each with the files they already appear in."""
    wanted = phrases(task)
    if not wanted:
        return []
    root = Path(project)
    hits: dict[str, list[tuple[str, int]]] = {phrase: [] for phrase in wanted}
    for path in _searchable(root):
        rel = path.relative_to(root).as_posix()
        if skip and rel == skip:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        lowered = [line.lower() for line in lines]
        for phrase in wanted:
            for number, line in enumerate(lowered, 1):
                if phrase in line:
                    hits[phrase].append((rel, number))
                    break
    ranked = [
        (phrase, found)
        for phrase, found in hits.items()
        if FEWEST_FILES <= len({rel for rel, _ in found}) <= MOST_FILES
    ]
    ranked.sort(key=lambda item: (len({rel for rel, _ in item[1]}), item[0]))
    return ranked[:2]


def existing_files(project: Path, task: str, *, skip: str = "") -> tuple[str, ...]:
    """Paths already_covers would name, without the prose."""
    found: list[str] = []
    for _phrase, hits in _ranked_hits(project, task, skip=skip):
        for rel, _number in hits:
            if rel not in found:
                found.append(rel)
    return tuple(found)


def already_covers(project: Path, task: str, *, skip: str = "") -> str:
    """One line naming where the task's subject already appears. "" if nowhere.

    `skip` is the file the task already names, because finding the words
    in the file being changed is not news.
    """
    ranked = _ranked_hits(project, task, skip=skip)
    if not ranked:
        return ""
    lines = []
    for phrase, found in ranked:
        where = ", ".join(f"{rel}:{number}" for rel, number in found[:2])
        lines.append(f'  "{phrase}" is already in {where}')
    return (
        "This project already has something for what the task names:\n"
        + "\n".join(lines)
        + "\nRead those before writing anything new for it."
    )
