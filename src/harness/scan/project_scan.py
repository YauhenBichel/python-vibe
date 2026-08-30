"""First-party .py files small enough for the 0.5B context window."""

from __future__ import annotations

from pathlib import Path

SKIP_DIR = {
    ".git",
    # Editor settings, including the ones `python-vibe editors` writes.
    # A project summary that counts the tool's own configuration as part
    # of your project is describing itself, not the code.
    ".cursor",
    ".vscode",
    ".idea",
    ".zed",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "site-packages",
    ".mlx_cache",
    "adapters",
    "fused",
    "scratch",
}
MAX_REVIEW_BYTES = 2500


def list_small_py_files(
    project: Path,
    *,
    limit: int = 100,
    max_bytes: int = MAX_REVIEW_BYTES,
    min_bytes: int = 200,
) -> list[Path]:
    root = project.resolve()
    out: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIR for part in path.parts):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size < min_bytes or size > max_bytes:
            continue
        out.append(path)
    out.sort(key=lambda p: (p.stat().st_size, str(p)))
    return out[:limit]
