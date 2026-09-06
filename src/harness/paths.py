"""Locations inside this repository.

A module that finds the repository root by counting parent directories
stops working when the module is moved to a different directory depth. The
root is resolved once here and imported everywhere else.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Small platform trees are Python plus a few config files. Secrets stay out.
TEXT_SUFFIXES = frozenset(
    {".py", ".pyi", ".md", ".toml", ".yml", ".yaml", ".cfg", ".ini", ".json"}
)
SECRET_NAMES = frozenset(
    {".env", ".env.local", "credentials.json", ".pypirc", "secrets.json"}
)


def _find_kit_skills() -> Path:
    """Locate the skills shipped with py-harness.

    A source checkout keeps them at the repository root. An installed
    package carries a copy inside `harness/`, because the repository root
    is not present once the package is in site-packages.
    """
    packaged = Path(__file__).resolve().parent / "kit_skills"
    if packaged.is_dir():
        return packaged
    return REPO_ROOT / "skills"


KIT_SKILLS_DIR = _find_kit_skills()
EVAL_DIR = REPO_ROOT / "eval"


def suffix_globs() -> tuple[str, ...]:
    """rglob patterns for every writable text suffix, sorted for stable tests."""
    return tuple(f"*{suffix}" for suffix in sorted(TEXT_SUFFIXES))


def is_secret_name(name: str) -> bool:
    return name.lower() in {item.lower() for item in SECRET_NAMES}


def is_windows(*, windows: bool | None = None) -> bool:
    """True on this OS, or the layout a caller asked to simulate."""
    return os.name == "nt" if windows is None else windows


def venv_python(venv: Path, *, windows: bool | None = None) -> Path:
    """The interpreter inside a virtual environment, on any platform.

    POSIX puts it at `bin/python`; Windows puts it at `Scripts/python.exe`.
    Pass `windows` to ask for one layout regardless of the platform running.
    """
    on_windows = is_windows(windows=windows)
    if on_windows:
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def rel_posix(path: Path, root: Path) -> str:
    """Path relative to root, written with forward slashes on every platform.

    Windows renders a relative path as `src\\app.py`. The model is shown
    these paths and copies them back into `Path:`, and the skills, the
    prompts and the tests are all written with forward slashes, so the two
    styles must not mix. Forward slashes work as input on Windows too.
    """
    return path.relative_to(root).as_posix()


def as_project_rel(rel: str) -> str:
    """Accept a path written with either separator, return one with slashes.

    A model may answer with `src\\app.py` whatever platform it runs on. On
    Linux and macOS that is a single filename containing a backslash, not a
    path, so it is converted before use.
    """
    cleaned = rel.replace("\\", "/").strip()
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned
