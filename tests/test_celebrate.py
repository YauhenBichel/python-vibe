"""The merge comment must not post a broken image.

The workflow picks a tag from the pull request title and falls back to a
file in `.github/celebrate/` when no Giphy key is set. A tag with no file
behind it produces a broken image in a public comment, so the two lists
are checked against each other here rather than in production.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "celebrate-merge.yml"
ASSETS = ROOT / ".github" / "celebrate"


def _tags() -> list[str]:
    return sorted(set(re.findall(r'tag = "([a-z ]+)"', WORKFLOW.read_text(encoding="utf-8"))))


def _files() -> set[str]:
    return {path.stem for path in ASSETS.glob("*.gif")}


class CelebrateAssetsTest(unittest.TestCase):
    def test_every_tag_has_a_file(self) -> None:
        missing = [tag for tag in _tags() if tag.replace(" ", "-") not in _files()]
        self.assertEqual(missing, [], "a tag with no image posts a broken comment")

    def test_no_file_is_unused(self) -> None:
        used = {tag.replace(" ", "-") for tag in _tags()}
        self.assertEqual(sorted(_files() - used), [])

    def test_the_images_are_small_enough_to_carry_in_the_repository(self) -> None:
        oversized = [
            f"{path.name} {path.stat().st_size // 1024} KB"
            for path in ASSETS.glob("*.gif")
            if path.stat().st_size > 200 * 1024
        ]
        self.assertEqual(oversized, [])

    def test_their_origin_is_recorded(self) -> None:
        notice = ASSETS / "NOTICE"
        self.assertTrue(notice.is_file(), "images redistributed without a NOTICE")
        text = notice.read_text(encoding="utf-8")
        self.assertIn("permission", text)

    def test_the_workflow_does_not_name_a_branch(self) -> None:
        """The fallback URL follows the default branch, whatever it is called."""
        body = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event.repository.default_branch", body)

    def test_the_pull_request_title_is_never_put_into_a_shell(self) -> None:
        """A title is attacker-controlled on a fork pull request."""
        body = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("${{ github.event.pull_request.title }}\n          run:", body)
        self.assertIn("PR_TITLE: ${{ github.event.pull_request.title }}", body)

    def test_the_pull_request_code_is_never_checked_out(self) -> None:
        """pull_request_target carries this repository's secrets."""
        body = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("actions/checkout", body)

    def test_github_script_is_pinned_to_a_commit(self) -> None:
        """pull-requests: write plus a mutable tag is a silent privilege change."""
        body = WORKFLOW.read_text(encoding="utf-8")
        self.assertRegex(body, r"uses: actions/github-script@[0-9a-f]{40}")


if __name__ == "__main__":
    unittest.main()
