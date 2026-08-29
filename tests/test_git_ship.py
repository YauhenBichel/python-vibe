import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.ship.git_ship import (
    commit_changes,
    current_branch,
    make_branch,
    merge_pr,
    push_branch,
)
from harness.task import (
    issue_number,
    looks_like_add_feature,
    looks_like_ship,
    looks_like_ticket_work,
)


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "init.templateDir=", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


class GitShipTest(unittest.TestCase):
    def test_ship_task_kinds(self) -> None:
        self.assertTrue(looks_like_ship("fix #50 and open a PR"))
        self.assertTrue(looks_like_ticket_work("fix #50 and open a PR"))
        self.assertTrue(looks_like_ship("create a pr for the rename"))
        self.assertEqual(issue_number("fix issue #50"), "50")
        self.assertFalse(looks_like_ship("fix issue #50"))
        self.assertFalse(looks_like_ship("create a package for total_price"))
        self.assertFalse(looks_like_add_feature("create a pr for #50"))
        self.assertFalse(looks_like_ship("what does apply_source refuse?"))

    def test_branch_and_commit_in_temp_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-b", "proceed/test")
            _git(root, "config", "user.email", "t@localhost")
            _git(root, "config", "user.name", "t")
            (root / "ok.py").write_text("print(1)\n", encoding="utf-8")
            _git(root, "add", "ok.py")
            _git(root, "commit", "-m", "start")
            out = make_branch(root, "proceed/quote-type")
            self.assertNotIn("bad branch", out)
            self.assertEqual(current_branch(root), "proceed/quote-type")
            self.assertIn("main", make_branch(root, "main"))
            (root / "ok.py").write_text("print(2)\n", encoding="utf-8")
            committed = commit_changes(root, "Explain why the print changed.")
            self.assertIn("quote-type", current_branch(root))
            self.assertTrue(
                "changed" in committed.lower() or "commit" in committed.lower()
            )
            self.assertIn("origin", push_branch(root))

    def test_merge_refused_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("merge only", merge_pr(Path(tmp), "16", allowed=False))


if __name__ == "__main__":
    unittest.main()


class AttributionTest(unittest.TestCase):
    """python-vibe's work should be visible where it happened.

    The commit used to be authored by `python-vibe@localhost`, which links
    to nothing on GitHub and takes the commit out of the person's own
    history. The person is the author now, and python-vibe is a co-author,
    which GitHub renders and links.
    """

    def test_the_person_stays_the_author(self) -> None:
        from harness.ship import git_ship

        source = Path(git_ship.__file__).read_text(encoding="utf-8")
        self.assertNotIn('GIT_AUTHOR_NAME", "python-vibe"', source)

    def test_a_commit_names_python_vibe_as_co_author(self) -> None:
        from harness.ship.git_ship import CO_AUTHOR
        from harness.ship.identity import with_co_author

        self.assertTrue(CO_AUTHOR.startswith("Co-authored-by:"))
        self.assertIn("python-vibe <python-vibe@users.noreply.github.com>", CO_AUTHOR)
        once = with_co_author("Explain why the print changed.")
        twice = with_co_author(once)
        self.assertEqual(once.count("Co-authored-by:"), 1)
        self.assertEqual(twice.count("Co-authored-by:"), 1)

    def test_a_pull_request_says_what_opened_it(self) -> None:
        from harness.ship.git_ship import PR_FOOTER

        self.assertIn("python-vibe", PR_FOOTER)

    def test_a_real_commit_carries_both(self) -> None:
        from harness.ship.git_ship import commit_changes

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _git(root, "init", "-b", "work")
            _git(root, "config", "user.name", "A Person")
            _git(root, "config", "user.email", "person@example.com")
            (root / "a.py").write_text("x = 1\n", encoding="utf-8")
            commit_changes(root, "add a helper module")
            author = subprocess.run(
                ["git", "log", "-1", "--format=%an"],
                cwd=root, capture_output=True, text=True, check=False,
            ).stdout.strip()
            body = subprocess.run(
                ["git", "log", "-1", "--format=%B"],
                cwd=root, capture_output=True, text=True, check=False,
            ).stdout
        self.assertEqual(author, "A Person")
        self.assertIn("Co-authored-by: python-vibe <python-vibe@users.noreply.github.com>", body)
