import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.task import looks_like_question, question_symbol
from harness.scan.project_brief import classify_project, render_brief, render_map, resolve_scope, start_hint


class ProjectBriefTest(unittest.TestCase):
    def test_small_lists_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("print(1)\n", encoding="utf-8")
            (root / "README.md").write_text("# hi\n", encoding="utf-8")
            brief = classify_project(root)
            self.assertEqual(brief.kind, "small")
            self.assertEqual(brief.files, 2)
            text = render_brief(brief)
            self.assertIn("Small project", text)
            self.assertIn("ok.py", text)
            self.assertIn("README.md", text)

    def test_large_uses_harness_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "src"
            src.mkdir()
            for i in range(45):
                (src / f"mod_{i}.py").write_text("x = 1\n" * 20, encoding="utf-8")
            brief = classify_project(root)
            self.assertEqual(brief.kind, "large")
            text = render_brief(brief)
            self.assertIn("Large project", text)
            self.assertIn("Action: map", text)
            self.assertIn("src/", text)

    def test_scope_jails_and_maps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
            (root / "other.py").write_text("def other():\n    return 2\n", encoding="utf-8")
            scoped = resolve_scope(root, "src")
            self.assertEqual(scoped, (root / "src").resolve())
            with self.assertRaises(ValueError):
                resolve_scope(root, "../escape")
            with self.assertRaises(ValueError) as ctx:
                resolve_scope(root, "src/a.py")
            self.assertIn("Path:", str(ctx.exception))
            mapped = render_map(root, "src")
            self.assertIn("src/a.py", mapped)
            self.assertNotIn("other.py", mapped)

    def test_question_hint(self) -> None:
        self.assertTrue(looks_like_question("what does apply_source refuse?"))
        self.assertTrue(looks_like_question("explain the weekday helper"))
        self.assertFalse(looks_like_question("find a NameError and fix it"))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("print(1)\n", encoding="utf-8")
            brief = classify_project(root)
            self.assertIn("question", start_hint(brief, "what is ok.py?"))
            self.assertEqual(question_symbol("what does apply_source refuse?"), "apply_source")
            self.assertEqual(question_symbol("what does add return?"), "add")
            self.assertEqual(
                question_symbol("add a function multiply(a, b) and a unit test"),
                "multiply",
            )
            hint = start_hint(brief, "what does apply_source refuse?")
            self.assertIn("grep", hint)
            self.assertIn("apply_source", hint)
            self.assertTrue(hint.index("grep") < hint.index("read"))
            located = start_hint(
                brief, "what does apply_source refuse?", located=True
            )
            self.assertIn("done", located)
            self.assertNotIn("First Action: grep", located)

    def test_cli_app_hint_names_the_module_not_a_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("print(1)\n", encoding="utf-8")
            hint = start_hint(
                classify_project(root),
                "design and develop a small cli app for reviewing github PRs",
            )
        self.assertIn("pkg/__init__.py", hint)
        self.assertIn("pkg/pr_review.py", hint)
        self.assertIn("argparse", hint)
        self.assertIn("urllib", hint)
        self.assertNotIn("weekday_name", hint)
        self.assertNotIn("pkg/<noun>.py", hint)


if __name__ == "__main__":
    unittest.main()
