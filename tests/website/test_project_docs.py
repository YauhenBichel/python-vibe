import tempfile
import unittest
from pathlib import Path

from harness.scan.project_docs import find_doc, render_house_rules


class ProjectDocsTest(unittest.TestCase):
    def test_no_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(find_doc(Path(tmp)))
            self.assertEqual(render_house_rules(Path(tmp)), "")

    def test_agents_md_wins_over_contributing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "CONTRIBUTING.md").write_text("contrib", encoding="utf-8")
            (project / "AGENTS.md").write_text("Do not touch vendor/", encoding="utf-8")
            text = render_house_rules(project)
        self.assertIn("AGENTS.md", text)
        self.assertIn("Do not touch vendor/", text)
        self.assertNotIn("contrib", text)

    def test_long_doc_is_budgeted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "AGENTS.md").write_text("x" * 5000, encoding="utf-8")
            text = render_house_rules(project, limit=100)
        self.assertIn("truncated", text)
        self.assertLess(len(text), 300)

    def test_empty_doc_is_not_a_preamble(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "AGENTS.md").write_text("   \n", encoding="utf-8")
            self.assertEqual(render_house_rules(project), "")


if __name__ == "__main__":
    unittest.main()
