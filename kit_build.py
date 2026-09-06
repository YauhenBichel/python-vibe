"""Copy top-level skills/ into the wheel as harness/kit_skills.

A source checkout reads ``skills/``. An installed package has no repository
root, so the same files have to live next to ``harness/paths.py``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills"
DEST = ROOT / "src" / "harness" / "kit_skills"


def copy_kit_skills(src: Path = SKILLS, dest: Path = DEST) -> Path:
    if not src.is_dir():
        raise SystemExit(f"missing skills directory: {src}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def __getattr__(name: str):
    from setuptools import build_meta as origin

    if name == "build_wheel":

        def build_wheel(*args, **kwargs):
            copy_kit_skills()
            return origin.build_wheel(*args, **kwargs)

        return build_wheel
    if name == "build_sdist":

        def build_sdist(*args, **kwargs):
            copy_kit_skills()
            return origin.build_sdist(*args, **kwargs)

        return build_sdist
    return getattr(origin, name)
