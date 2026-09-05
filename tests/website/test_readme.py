"""README contributor list is a workflow marker, not a hardcoded table."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "contributors.yml"
CELEBRATE = ROOT / ".github" / "workflows" / "celebrate-merge.yml"

_START = "<!-- readme: contributors,bots/- -start -->"
_END = "<!-- readme: contributors,bots/- -end -->"


class ReadmeContributorsTest(unittest.TestCase):
    def test_readme_shows_the_vscode_recording(self) -> None:
        text = README.read_text(encoding="utf-8")
        self.assertIn("docs/media/vscode-demo.gif", text)
        self.assertIn("asciinema play docs/media/vscode-demo.cast", text)
        self.assertIn("python-vibe editors vscode", text)

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

    def test_a_fork_pull_request_does_not_run_the_job(self) -> None:
        """It cannot work on one, and it used to fail rather than skip.

        The branch of a fork pull request lives on the fork, so the
        checkout cannot fetch it from here. The job ran anyway and died
        on `git fetch origin +refs/heads/patch-2*`, which showed on the
        pull request as a failing check that had nothing to do with the
        change.
        """
        text = WORKFLOW.read_text(encoding="utf-8")
        head, _sep, steps = text.partition("steps:")
        self.assertIn("head.repo.full_name == github.repository", head)
        self.assertIn("github.event_name != 'pull_request'", head)
        # The step-level guard is subsumed by the job-level one.
        self.assertNotIn("head.repo.full_name", steps)

    def test_a_stale_list_on_main_becomes_a_pull_request(self) -> None:
        """Pushing to a branch nobody merges is not updating anything.

        main takes changes only through a reviewed pull request, so the
        workflow cannot commit there. It used to force-push the refresh
        to `docs/contributors` and stop. Nothing merged that branch, so
        a new contributor never reached the README.
        """
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("gh pr create", text)
        self.assertIn("pull-requests: write", text)
        self.assertIn("GH_TOKEN", text)
        # and it must not open a second one on every push
        self.assertIn("gh pr list --head docs/contributors", text)

    def test_a_branch_of_this_repo_still_takes_it_in_place(self) -> None:
        """No pull request is needed where a plain push works."""
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('if [ "$BRANCH" != "$DEFAULT_BRANCH" ]', text)

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
