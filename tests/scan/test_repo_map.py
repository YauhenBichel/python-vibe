import tempfile
import unittest
from pathlib import Path

from harness.scan.repo_map import file_signatures, render_outline

MODULE = '''
"""Docstring."""
import os

CONST = 1


def apply_source(path, source, *, original: str) -> None:
    return None


class Guard:
    def check(self, text: str) -> bool:
        return True

    def _private(self) -> None:
        return None
'''


class FileSignaturesTest(unittest.TestCase):
    def test_top_level_defs_and_public_methods(self) -> None:
        sigs = file_signatures(MODULE)
        self.assertIn("def apply_source(path, source, *, original: str) -> None", sigs)
        self.assertIn("class Guard", sigs)
        self.assertIn("    def check(self, text: str) -> bool", sigs)

    def test_private_methods_are_skipped(self) -> None:
        self.assertNotIn("    def _private(self) -> None", file_signatures(MODULE))

    def test_unparsable_file_is_not_a_crash(self) -> None:
        self.assertEqual(file_signatures("def broken("), [])

    def test_per_file_limit(self) -> None:
        source = "\n".join(f"def f{i}(): ...\n" for i in range(40))
        self.assertLessEqual(len(file_signatures(source, limit=5)), 5)


class RenderOutlineTest(unittest.TestCase):
    def test_outline_names_the_signature_not_the_size(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "app.py").write_text(MODULE, encoding="utf-8")
            text = render_outline(project)
        self.assertIn("app.py", text)
        self.assertIn("original: str", text)
        self.assertNotIn("KB", text)

    def test_empty_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("no .py files", render_outline(Path(tmp)))

    def test_line_budget_truncates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            for i in range(6):
                body = "\n".join(f"def f{i}_{j}(): ...\n" for j in range(10))
                (project / f"m{i}.py").write_text(body, encoding="utf-8")
            text = render_outline(project, max_lines=12)
        self.assertIn("truncated", text)


if __name__ == "__main__":
    unittest.main()
