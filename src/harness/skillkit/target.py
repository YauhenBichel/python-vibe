"""Replace the file paths inside a skill with paths from this project.

A skill is written as a block of text for the model to copy, so any file
path inside it will be copied as well. A path that refers to this
repository's test fixtures does not exist in the user's project, and
writing to it creates a file the user did not ask for.

Two replacements are made before the model sees a skill:

* The placeholders `{{module}}`, `{{test}}`, `{{scope}}` and `{{symbol}}`
  are filled in from the project.
* Any `Path:` or `Scope:` that does not exist in the project is replaced
  with one that does.

A path that does exist in the project is left unchanged, which is what
keeps the fixture-based tests working. A path ending in `__init__.py` is
also left unchanged, because creating a package legitimately names a file
that does not exist yet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness.task import looks_like_new_package, looks_like_ops, package_noun, question_symbol
from harness.paths import rel_posix
from harness.scan.project_brief import iter_text_files

_DEF_NAME = re.compile(r"^def\s+([A-Za-z_]\w*)", re.MULTILINE)
# HTTP/UI adapters are larger than the domain file beside them. Size-first
# pick put `total_lines` in `orders_controller.py` on the live 8B demo.
_ROLE_SUFFIX = ("_controller", "_service", "_view", "_router", "_handler")

_PLACEHOLDER = re.compile(r"\{\{(module|test|scope|symbol)\}\}")
_PATH_LINE = re.compile(r"^(Path|File):\s*(\S+)\s*$", re.MULTILINE)
_SCOPE_LINE = re.compile(r"^Scope:\s*(\S+)\s*$", re.MULTILINE)
_SYMBOL_TOKEN = "the_symbol_from_the_task"
# Scaffolding a package legitimately names a file that does not exist yet.
_KEEP_NAMES = frozenset({"__init__.py"})
# Used only in documentation and error text, never handed to the model.
FALLBACK_MODULE = "path/to/module.py"
DEFAULT_NEW_MODULE = "src/main.py"
FALLBACK_TEST = "tests/test_module.py"


@dataclass(frozen=True)
class Target:
    """The files in this project that a skill should refer to.

    Fields:
        module: file where new code belongs.
        test: file where new tests belong.
        scope: directory to stay within.
        symbol: name from the task, used to fill in a search query.
    """

    module: str
    test: str
    scope: str
    symbol: str


def _is_test(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    return "tests" in parts or parts[-1].startswith("test_")


def _rels(project: Path, suffix: str = ".py") -> list[tuple[str, int]]:
    root = project.resolve()
    return [
        (rel_posix(path, root), size)
        for path, size in iter_text_files(project)
        if path.suffix == suffix
    ]


def pick_module(project: Path, located_path: str = "", task: str = "") -> str:
    """The file a new function most likely belongs in.

    A project with no Python file in it still needs a real path. The
    placeholder used to be handed straight to the model, which then created
    a file literally at `path/to/module.py` — the same fault as shipping a
    fixture path, arriving by a different route.
    """
    if looks_like_ops(task):
        return pick_workflow(project)
    if looks_like_new_package(task):
        return f"pkg/{package_noun(task)}.py"
    if located_path:
        rel = located_path.replace("\\", "/").lstrip("./")
        if rel.endswith(".py") and not _is_test(rel):
            return rel
    usable = [
        (rel, size)
        for rel, size in _rels(project)
        if not _is_test(rel) and Path(rel).name != "__init__.py"
    ]
    if not usable:
        return _new_module_name(task)
    wanted = _name_tokens(question_symbol(task))
    usable.sort(key=lambda item: _module_score(project, item[0], item[1], wanted))
    return usable[0][0]


def _name_tokens(symbol: str) -> frozenset[str]:
    return frozenset(part for part in symbol.lower().split("_") if len(part) >= 3)


def _module_score(
    project: Path, rel: str, size: int, wanted: frozenset[str]
) -> tuple[int, int, int, str]:
    """Lower is better: more name overlap, not a role adapter, then smaller."""
    stem = Path(rel).stem.lower()
    role = int(any(stem.endswith(suffix) for suffix in _ROLE_SUFFIX))
    overlap = 0
    if wanted:
        try:
            body = (Path(project) / rel).read_text(encoding="utf-8")
        except OSError:
            body = ""
        overlap = sum(
            1 for name in _DEF_NAME.findall(body) if _name_tokens(name) & wanted
        )
    return (-overlap, role, size, rel)


def pick_workflow(project: Path) -> str:
    """Existing workflow YAML, else the path the skill creates."""
    root = Path(project)
    folder = root / ".github" / "workflows"
    if folder.is_dir():
        found = sorted(
            rel_posix(path, root)
            for path in folder.iterdir()
            if path.suffix in {".yml", ".yaml"} and path.is_file()
        )
        if found:
            return found[0]
    return ".github/workflows/tests.yml"


def _new_module_name(task: str) -> str:
    """Where the first module of an empty project should go."""
    symbol = question_symbol(task)
    if symbol and symbol != _SYMBOL_TOKEN:
        return f"src/{symbol}.py"
    return DEFAULT_NEW_MODULE


def pick_test(project: Path, module: str) -> str:
    """The matching test file, else any test file, else the name to create."""
    stem = Path(module).stem
    tests = sorted(rel for rel, _size in _rels(project) if _is_test(rel))
    if not tests:
        return f"tests/test_{stem}.py" if stem else FALLBACK_TEST
    for rel in tests:
        if Path(rel).stem == f"test_{stem}":
            return rel
    return tests[0]


def pick_scope(scope: str, module: str) -> str:
    if scope:
        return scope
    parts = module.split("/")
    return parts[0] if len(parts) > 1 else "."


def pick_target(
    project: Path, task: str = "", scope: str = "", located_path: str = ""
) -> Target:
    module = pick_module(project, located_path, task)
    symbol = (
        package_noun(task)
        if looks_like_new_package(task)
        else question_symbol(task) or _SYMBOL_TOKEN
    )
    return Target(
        module=module,
        test=pick_test(project, module),
        scope=pick_scope(scope, module),
        symbol=symbol,
    )


def _writes_a_whole_module(body: str) -> bool:
    """True when the skill hands over a file, not a change to one.

    `Action: edit` with a module body creates a file. `Action: patch` with
    Find or Append edits one that is already there, and only that case
    should be pointed at an existing file.
    """
    return bool(re.search(r"^Action:\s*edit\s*$", body, re.MULTILINE))


def retarget(body: str, target: Target, project: Path | None = None) -> str:
    """Fill placeholders, then repoint any path this project does not have."""
    values = {
        "module": target.module,
        "test": target.test,
        "scope": target.scope,
        "symbol": target.symbol,
    }
    text = _PLACEHOLDER.sub(lambda m: values[m.group(1)], body)
    if target.symbol != _SYMBOL_TOKEN:
        text = text.replace(_SYMBOL_TOKEN, target.symbol)
    if project is None:
        return text
    root = project.resolve()

    creates_module = _writes_a_whole_module(text)

    def _path(match: re.Match[str]) -> str:
        key, rel = match.group(1), match.group(2)
        if (root / rel).is_file() or Path(rel).name in _KEEP_NAMES:
            return match.group(0)
        if creates_module and not _is_test(rel):
            # The skill writes a new module, not a change to an existing one.
            # Repointing it onto a file that already exists made the model
            # write the function twice: once where it was sent, once where
            # the skill said. Keep the name, move it beside this project's
            # own modules.
            home = Path(target.module).parent
            name = Path(rel).name
            moved = (home / name).as_posix() if home != Path(".") else name
            return f"{key}: {moved}"
        return f"{key}: {target.test if _is_test(rel) else target.module}"

    def _scope(match: re.Match[str]) -> str:
        rel = match.group(1)
        if (root / rel).is_dir():
            return match.group(0)
        return f"Scope: {target.scope}"

    text = _PATH_LINE.sub(_path, text)
    return _SCOPE_LINE.sub(_scope, text)
