"""README contributor list is a workflow marker, not a hardcoded table."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "contributors.yml"
CELEBRATE = ROOT / ".github" / "workflows" / "celebrate-merge.yml"

_START = "<!-- readme: contributors,bots/- -start -->"
_END = "<!-- readme: contributors,bots/- -end -->"


class ReadmeContributorsTest(unittest.TestCase):
    def test_markers_not_hardcoded_table(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn(_START, text)
        self.assertIn(_END, text)
        self.assertEqual(text.count(_START), 1)
        self.assertLess(text.index(_START), text.index(_END))
        self.assertNotIn("contrib.rocks", text)
        self.assertNotIn("| Contributor | Commits |", text)

    def test_workflow_reads_github_api(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("fill_contributors.py", text)
        self.assertIn("github-actions[bot]", text)
        self.assertNotIn("akhilmhdh/contributors-readme-action", text)
        self.assertNotIn("YauhenBichel", text)
        self.assertNotIn("ItzSaurav", text)
        script = ROOT / ".github" / "scripts" / "fill_contributors.py"
        self.assertTrue(script.is_file())

    def test_checkout_is_pinned_to_a_commit(self) -> None:
        """contents: write plus persist-credentials must not follow a moving tag."""
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(text, r"uses: actions/checkout@[0-9a-f]{40}")

    def test_workflow_keeps_a_fork_merge_on_a_writable_branch(self) -> None:
        """A fork PR cannot be pushed, and protected main cannot either.

        After that merge the generated list was discarded because both
        the PR-head push and the default-branch push were skipped.
        """
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("docs/contributors", text)
        self.assertIn("head.repo.full_name == github.repository", text)
        self.assertIn("DEFAULT_BRANCH", text)
        self.assertNotIn(
            "github.event.repository.default_branch != (github.head_ref || github.ref_name)",
            text,
        )

    def test_celebrate_merge_uses_giphy_not_hardcoded_gifs(self) -> None:
        text = CELEBRATE.read_text(encoding="utf-8")
        self.assertIn("pull_request_target", text)
        self.assertIn("api.giphy.com", text)
        self.assertIn("rating", text)
        self.assertIn("GIPHY_API_KEY", text)
        self.assertIn(".github/celebrate/", text)
        self.assertNotIn("media.giphy.com/media/", text)
        self.assertNotIn("YauhenBichel", text)
        gifs = sorted((ROOT / ".github" / "celebrate").glob("*.gif"))
        names = {path.name for path in gifs}
        self.assertTrue(gifs, "owned fallback GIFs belong in .github/celebrate/")
        self.assertIn("celebration.gif", names)
        self.assertIn("ship-it.gif", names)
        notice = (ROOT / ".github" / "celebrate" / "NOTICE").read_text(encoding="utf-8")
        self.assertIn("cultofthepartyparrot.com", notice)

    def test_contributor_markers_are_not_an_empty_pair(self) -> None:
        text = README.read_text(encoding="utf-8")
        start = text.index(_START) + len(_START)
        end = text.index(_END)
        body = text[start:end]
        self.assertIn("<table>", body)
        self.assertIn("avatars.githubusercontent.com", body)

    def test_fill_script_renders_a_table_without_bots(self) -> None:
        import importlib.util

        path = ROOT / ".github" / "scripts" / "fill_contributors.py"
        spec = importlib.util.spec_from_file_location("fill_contributors", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        html = module.render_table(
            [{"login": "alice", "name": "Alice Example"}]
        )
        self.assertIn("github.com/alice", html)
        self.assertIn("Alice Example", html)
        self.assertIn("<table>", html)
