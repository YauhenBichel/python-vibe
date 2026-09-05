#!/usr/bin/env python3
"""Put the `python-vibe` command on PATH.

  python3 scripts/run/install.py
  python3 scripts/run/install.py --train
  python3 scripts/run/install.py --dry-run

Creates `.venv` when you are not already in a virtual environment, then
runs `python -m pip install -e .`. Do not pipe a download into a shell.
No extras unless you ask.
Works on macOS, Linux, and Windows (no PYTHONPATH).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import venv
from pathlib import Path

MIN_VERSION = (3, 11)


def repo_root(start: Path | None = None) -> Path:
    """The checkout that contains this script, or *start* when testing."""
    if start is not None:
        root = Path(start)
        pyproject = root / "pyproject.toml"
        if not pyproject.is_file() or 'name = "python-vibe"' not in pyproject.read_text(
            encoding="utf-8"
        ):
            raise SystemExit(f"not a python-vibe checkout: {root}")
        return root
    here = Path(__file__).resolve().parent
    for root in (here, *here.parents):
        pyproject = root / "pyproject.toml"
        if pyproject.is_file() and 'name = "python-vibe"' in pyproject.read_text(
            encoding="utf-8"
        ):
            return root
    raise SystemExit("not a python-vibe checkout: no pyproject.toml")


def require_python(info: tuple[int, int] | None = None) -> str:
    """Empty when this interpreter is new enough, else a refusal."""
    major, minor = info if info is not None else sys.version_info[:2]
    if (major, minor) >= MIN_VERSION:
        return ""
    return (
        f"python-vibe needs Python {MIN_VERSION[0]}.{MIN_VERSION[1]} or newer "
        f"(this is {major}.{minor})"
    )


def in_venv() -> bool:
    if os.environ.get("VIRTUAL_ENV"):
        return True
    return getattr(sys, "prefix", "") != getattr(sys, "base_prefix", "")


def pip_spec(*, train: bool = False, hub: bool = False) -> list[str]:
    extras = [name for name, on in (("train", train), ("hub", hub)) if on]
    if not extras:
        return ["-e", "."]
    return ["-e", f".[{','.join(extras)}]"]


def venv_python(venv_dir: Path, *, windows: bool | None = None) -> Path:
    on_windows = os.name == "nt" if windows is None else windows
    if on_windows:
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def console_script(python: Path, *, windows: bool | None = None) -> Path:
    on_windows = os.name == "nt" if windows is None else windows
    if on_windows:
        return python.parent / "python-vibe.exe"
    return python.parent / "python-vibe"


def activate_hint(venv_dir: Path, *, windows: bool | None = None) -> str:
    on_windows = os.name == "nt" if windows is None else windows
    if on_windows:
        return str(venv_dir / "Scripts" / "Activate.ps1")
    return f"source {venv_dir.as_posix()}/bin/activate"


def pip_argv(python: Path, spec: list[str]) -> list[str]:
    return [str(python), "-m", "pip", "install", *spec]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the python-vibe command into a venv (or this interpreter)."
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="also install the Apple Silicon training extras",
    )
    parser.add_argument(
        "--hub",
        action="store_true",
        help="also install the Hugging Face publish extras",
    )
    parser.add_argument(
        "--system",
        action="store_true",
        help="install into this interpreter; do not create .venv",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the pip command and stop",
    )
    return parser.parse_args(argv)


def choose_python(root: Path, *, system: bool) -> Path:
    if system or in_venv():
        return Path(sys.executable)
    return venv_python(root / ".venv")


def ensure_venv(python: Path, root: Path) -> None:
    if python.resolve() == Path(sys.executable).resolve():
        return
    venv_dir = root / ".venv"
    if python.is_file():
        return
    venv.EnvBuilder(with_pip=True).create(venv_dir)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    blocked = require_python()
    if blocked:
        print(blocked, file=sys.stderr)
        return 2
    root = repo_root()
    spec = pip_spec(train=args.train, hub=args.hub)
    python = choose_python(root, system=args.system)
    argv_pip = pip_argv(python, spec)
    script = console_script(python)
    if args.dry_run:
        print(" ".join(argv_pip))
        print(f"would install {script}")
        return 0
    ensure_venv(python, root)
    ran = subprocess.run(argv_pip, cwd=root, check=False)
    if ran.returncode != 0:
        return ran.returncode
    print(f"installed python-vibe -> {script}")
    if not args.system and not in_venv():
        print(f"Activate once: {activate_hint(root / '.venv')}")
    print("Then from your project folder: python-vibe brief")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
