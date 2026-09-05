"""Pull a Python block out of a vibe draft and write or run it locally."""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_SKIP_PARTS = {".git", ".venv", "node_modules", "adapters", "fused", "__pycache__"}
_TRACE_HEAD = re.compile(
    r"^(?:Traceback \(most recent call last\):"
    r"|File \""
    r"|[A-Za-z]+(?:Error|Exception|Warning)\b)"
)
_MISSING_STDLIB = re.compile(r"NameError: name '(sys|re|datetime)' is not defined")
_DATETIME_MODULE_USE = re.compile(
    r"\bdatetime\.(datetime|date|time|timedelta|timezone)\b"
)
MAX_FILE_CHARS = 3500


def extract_python(text: str) -> str | None:
    blocks = [m.group(1).strip() for m in _FENCE.finditer(text)]
    if blocks:
        source = max(blocks, key=len)
        return None if is_traceback_source(source) else source
    stripped = text.strip()
    if stripped.startswith(("import ", "from ", "def ", "class ", "#!/")):
        return None if is_traceback_source(stripped) else stripped
    return None


def is_traceback_source(source: str) -> bool:
    for line in source.splitlines():
        text = line.strip()
        if not text:
            continue
        return bool(_TRACE_HEAD.match(text))
    return False


def missing_stdlib_names(stderr: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_MISSING_STDLIB.findall(stderr)))


def _import_line(name: str, source: str) -> str | None:
    if name in {"sys", "re"}:
        return None if f"import {name}" in source else f"import {name}"
    if name == "datetime":
        if "import datetime" in source or "from datetime import" in source:
            return None
        if _DATETIME_MODULE_USE.search(source):
            return "import datetime"
        return "from datetime import datetime"
    return f"import {name}"


def with_missing_imports(source: str, names: tuple[str, ...]) -> str:
    extra = [line for name in names if (line := _import_line(name, source))]
    if not extra:
        return source
    return "\n".join(extra) + "\n" + source.lstrip("\n")


@dataclass(frozen=True)
class RunResult:
    code: int
    stdout: str
    stderr: str


def write_and_run(
    source: str,
    dest: Path,
    argv: list[str] | None = None,
    *,
    cwd: Path | None = None,
    timeout: float = 12,
    stdin: str | None = None,
) -> RunResult:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(source.rstrip() + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(dest), *(argv or [])],
        cwd=cwd or dest.parent,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        input=stdin,
    )
    return RunResult(proc.returncode, proc.stdout, proc.stderr)


def write_and_run_fixed(
    source: str,
    dest: Path,
    argv: list[str] | None = None,
    *,
    cwd: Path | None = None,
    timeout: float = 12,
    stdin: str | None = None,
) -> tuple[RunResult, bool]:
    result = write_and_run(
        source, dest, argv, cwd=cwd, timeout=timeout, stdin=stdin
    )
    names = missing_stdlib_names(result.stderr)
    if result.code == 0 or not names:
        return result, False
    fixed = with_missing_imports(source, names)
    if fixed == source:
        return result, False
    return write_and_run(fixed, dest, argv, cwd=cwd, timeout=timeout, stdin=stdin), True


def resolve_project_file(project: Path, rel: str) -> Path:
    root = project.resolve()
    path = (root / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{path} is outside {root}") from exc
    if any(part in _SKIP_PARTS for part in path.parts):
        raise ValueError(f"refusing {path}")
    if path.suffix not in {".py", ".pyi"}:
        raise ValueError("only .py files")
    return path


def read_project_file(path: Path, *, limit: int = MAX_FILE_CHARS) -> str:
    text = path.read_text(encoding="utf-8")
    if len(text) > limit:
        return text[:limit] + f"\n# … truncated {len(text) - limit} chars\n"
    return text


def apply_source(path: Path, source: str, *, original: str) -> None:
    if not source.strip():
        raise ValueError("empty draft")
    if original and len(source) < max(40, len(original) // 5):
        raise ValueError(
            f"draft is too short ({len(source)} chars vs {len(original)}) — not applying"
        )
    bak = path.with_suffix(path.suffix + ".bak")
    if path.is_file():
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(source.rstrip() + "\n", encoding="utf-8")
