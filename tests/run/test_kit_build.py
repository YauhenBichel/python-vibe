"""The PyPI wheel must ship the kit. A source checkout reads skills/."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "kit_build.py"


def _load():
    spec = importlib.util.spec_from_file_location("kit_build", BACKEND)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {BACKEND}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class KitBuildTest(unittest.TestCase):
    def test_pyproject_uses_the_copy_backend(self) -> None:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('build-backend = "kit_build"', text)
        self.assertIn("kit_skills/*/SKILL.md", text)

    def test_copy_puts_skill_markdown_in_the_package(self) -> None:
        mod = _load()
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "kit_skills"
            mod.copy_kit_skills(src=ROOT / "skills", dest=dest)
            skills = list(dest.glob("*/SKILL.md"))
            self.assertGreaterEqual(len(skills), 20, len(skills))


if __name__ == "__main__":
    unittest.main()
