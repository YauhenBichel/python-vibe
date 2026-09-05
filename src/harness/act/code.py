"""Pull a Python block out of a vibe draft and write or run it locally."""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from harness.paths import SECRET_NAMES, TEXT_SUFFIXES, as_project_rel

_FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_SKIP_PARTS = {".git", ".venv", "node_modules", "adapters", "fused", "__pycache__"}
MAX_FILE_CHARS = 3500
# Small files are read whole so nearby constants (env, argv) stay in the quote.
WHOLE_FILE_CHARS = 12_000
# How much of the middle to keep when the task points at it.
MIDDLE_WINDOW_CHARS = 1200


def extract_python(text: str) -> str | None:
    blocks = [m.group(1).strip() for m in _FENCE.finditer(text)]
    if blocks:
        return max(blocks, key=len)
    stripped = text.strip()
    if stripped.startswith(("import ", "from ", "def ", "class ", "#!/")):
        return stripped
    return None


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
    )
    return RunResult(proc.returncode, proc.stdout, proc.stderr)


def resolve_project_file(project: Path, rel: str) -> Path:
    root = project.resolve()
    rel = as_project_rel(rel)
    path = (root / rel).resolve() if not Path(rel).is_absolute() else Path(rel).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{path} is outside {root}") from exc
    if any(part in _SKIP_PARTS for part in path.parts):
        raise ValueError(f"refusing {path}")
    if path.name.lower() in {item.lower() for item in SECRET_NAMES}:
        raise ValueError(f"refusing secret filename {path.name}")
    if path.suffix.lower() not in TEXT_SUFFIXES:
        raise ValueError(
            "only project text files: " + ", ".join(sorted(TEXT_SUFFIXES))
        )
    return path


def _window_around(text: str, about: str, width: int) -> tuple[int, int] | None:
    """Character range covering the first mention of `about`, or None."""
    if not about:
        return None
    at = text.find(about)
    if at < 0:
        return None
    half = width // 2
    start = max(0, at - half)
    return start, min(len(text), start + width)


def read_project_file(
    path: Path, *, limit: int = MAX_FILE_CHARS, about: str = ""
) -> str:
    """The file, or as much of it as fits, keeping the part that matters.

    A file too long to send whole used to be sent as its head and its
    tail, with the middle dropped. Asked to add a field to a dict two
    thirds of the way down a 13,476-character file, the model was handed
    3,500 characters from the top and 800 from the bottom — and the dict
    was in neither. It then invented a `Find:` line that was not in the
    file, was refused, and sent it again.

    `about` names what the task is for. When the text contains it, a
    window around it is kept as well, so the part being changed is one
    of the parts that arrives.
    """
    text = path.read_text(encoding="utf-8")
    cap = WHOLE_FILE_CHARS if limit == MAX_FILE_CHARS else limit
    if len(text) <= cap:
        return text
    tail = min(800, max(0, len(text) - limit))
    omitted = len(text) - limit - tail
    if omitted <= 0:
        return text
    window = _window_around(text, about, MIDDLE_WINDOW_CHARS)
    if window is None or window[0] < limit:
        # Either nothing to centre on, or it is inside the head already.
        return (
            text[:limit]
            + f"\n# … truncated {omitted} chars …\n"
            + text[-tail:]
        )
    start, end = window
    before = start - limit
    after = max(0, len(text) - tail - end)
    return (
        text[:limit]
        + f"\n# … truncated {before} chars …\n"
        + text[start:end]
        + f"\n# … truncated {after} chars …\n"
        + text[-tail:]
    )

def apply_source(path: Path, source: str, *, original: str) -> None:
    if not source.strip():
        raise ValueError("empty draft")
    if original and len(source) < max(40, (len(original) * 2) // 3):
        raise ValueError(
            f"draft is too short ({len(source)} chars vs {len(original)}) — "
            "use Action: patch for a small change"
        )
    if path.suffix in {".py", ".pyi"}:
        try:
            ast.parse(source)
        except SyntaxError as exc:
            raise ValueError(
                f"syntax error: {exc} — file not written. "
                "Use a full unique line for Find: (not a prefix of def …)"
            ) from exc
    bak = path.with_suffix(path.suffix + ".bak")
    if path.is_file():
        bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.rstrip() + "\n", encoding="utf-8")
