"""Judging a bot's pull request. No network, no live repository."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.ship.bot_pr import (  # noqa: E402
    bump_in,
    is_a_major_bump,
    refuse_bot_merge,
)

GREEN = {"name": "ci", "conclusion": "SUCCESS"}


def pull(title: str = "Bump left-pad from 1.2.3 to 1.2.4", **over) -> dict:
    base = {
        "title": title,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
        "statusCheckRollup": [GREEN],
        "author": {"is_bot": True, "login": "app/dependabot"},
    }
    base.update(over)
    return base


class ReadingTheTitleTest(unittest.TestCase):
    def test_the_usual_shape(self) -> None:
        self.assertEqual(
            bump_in("Bump actions/github-script from 7 to 9"),
            ("actions/github-script", "7", "9"),
        )

    def test_a_conventional_commit_prefix(self) -> None:
        self.assertEqual(
            bump_in("chore(deps): bump numpy from 1.26.4 to 2.0.0"),
            ("numpy", "1.26.4", "2.0.0"),
        )

    def test_a_title_that_is_not_a_bump(self) -> None:
        self.assertIsNone(bump_in("Fix the retry loop"))

    def test_a_leading_v_is_still_a_version(self) -> None:
        self.assertTrue(is_a_major_bump("v7", "v9"))

    def test_a_patch_is_not_major(self) -> None:
        self.assertFalse(is_a_major_bump("1.2.3", "1.2.4"))

    def test_a_minor_is_not_major(self) -> None:
        self.assertFalse(is_a_major_bump("1.2.3", "1.3.0"))

    def test_a_version_nobody_can_parse_is_not_called_major(self) -> None:
        """The check is about the risk, not about the parser."""
        self.assertFalse(is_a_major_bump("latest", "newest"))


class WhenAPersonIsNeededTest(unittest.TestCase):
    def test_a_dull_patch_bump_draws_no_objection(self) -> None:
        self.assertEqual(refuse_bot_merge(pull()), "")

    def test_the_real_one_that_looks_dull(self) -> None:
        """`Bump actions/github-script from 7 to 9` reads like the rest.

        Its release notes say `require('@actions/github')` stops working
        and `getOctokit` becomes an injected parameter. The title says
        none of that. The first number says all of it.
        """
        refused = refuse_bot_merge(
            pull("Bump actions/github-script from 7 to 9", mergeStateStatus="CLEAN")
        )
        self.assertIn("major version bump", refused)
        self.assertIn("7 to 9", refused)

    def test_a_failing_check_is_named(self) -> None:
        refused = refuse_bot_merge(
            pull(statusCheckRollup=[{"name": "windows", "conclusion": "FAILURE"}])
        )
        self.assertIn("failing", refused)
        self.assertIn("windows", refused)

    def test_a_check_still_running_is_not_a_green_check(self) -> None:
        refused = refuse_bot_merge(
            pull(statusCheckRollup=[GREEN, {"name": "macos", "status": "IN_PROGRESS"}])
        )
        self.assertIn("not finished", refused)
        self.assertIn("macos", refused)

    def test_a_conflict_is_refused(self) -> None:
        self.assertIn("conflicts", refuse_bot_merge(pull(mergeable="CONFLICTING")))

    def test_github_saying_blocked_is_believed(self) -> None:
        refused = refuse_bot_merge(pull(mergeStateStatus="BLOCKED"))
        self.assertIn("blocked", refused)

    def test_a_draft_is_not_finished_work(self) -> None:
        self.assertIn("draft", refuse_bot_merge(pull(mergeStateStatus="DRAFT")))

    def test_a_red_check_is_reported_before_the_version(self) -> None:
        """Whichever comes first, the person is told the worse thing."""
        refused = refuse_bot_merge(
            pull(
                "Bump x from 1 to 2",
                statusCheckRollup=[{"name": "ci", "conclusion": "FAILURE"}],
            )
        )
        self.assertIn("failing", refused)

    def test_github_not_having_decided_is_not_a_yes(self) -> None:
        """Mergeability is worked out when asked, not in advance.

        The first read of a fresh pull request often says UNKNOWN. The
        real #53 said exactly that, with every check green, which is one
        rule away from a bot merging a breaking change unread.
        """
        refused = refuse_bot_merge(
            pull("Bump left-pad from 1.2.3 to 1.2.4",
                 mergeable="UNKNOWN", mergeStateStatus="UNKNOWN")
        )
        self.assertIn("not worked out yet", refused)

    def test_a_major_bump_is_said_even_while_github_is_thinking(self) -> None:
        """The durable reason beats the transient one."""
        refused = refuse_bot_merge(
            pull("Bump actions/github-script from 7 to 9",
                 mergeable="UNKNOWN", mergeStateStatus="UNKNOWN")
        )
        self.assertIn("major version bump", refused)

    def test_a_pull_request_with_no_checks_at_all(self) -> None:
        """Nothing to object to is not the same as nothing being checked."""
        self.assertEqual(refuse_bot_merge(pull(statusCheckRollup=[])), "")



class ReadingRealBotTitlesTest(unittest.TestCase):
    """The bot writes two shapes and only one was being read.

    Pointing this at four live dependabot pull requests found both of
    the bugs below. Neither showed up against made-up input, because
    made-up input was written by the same person who wrote the parser.
    """

    def test_a_python_requirement_bump_is_a_bump(self) -> None:
        """Actions say "bump x from"; requirements say "update x requirement from"."""
        self.assertEqual(
            bump_in("Build(deps): update huggingface-hub requirement "
                    "from >=0.26.0 to >=1.29.0"),
            ("huggingface-hub", ">=0.26.0", ">=1.29.0"),
        )

    def test_a_comparator_is_not_part_of_the_version(self) -> None:
        """`>=0.26.0` is version 0, not a string starting with a bracket."""
        self.assertTrue(is_a_major_bump(">=0.26.0", ">=1.29.0"))
        self.assertTrue(is_a_major_bump(">=68", ">=84.0.0"))
        self.assertFalse(is_a_major_bump(">=8.1.0", ">=8.4.0"))

    def test_the_three_live_ones_are_all_refused(self) -> None:
        for title in (
            "Build(deps): bump actions/configure-pages from 5 to 6",
            "Build(deps): update huggingface-hub requirement from >=0.26.0 to >=1.29.0",
            "Build(deps-dev): update setuptools requirement from >=68 to >=84.0.0",
        ):
            with self.subTest(title=title):
                self.assertIn("major version bump", refuse_bot_merge(pull(title)))


class OnlyTheLatestRunOfACheckCountsTest(unittest.TestCase):
    """A pull request keeps every run of a check, not just the current one.

    Pushing again cancels the run in flight and starts another, so the
    rollup holds a cancelled entry and a successful entry under one name.
    Reading them as equal reported "checks are failing: readme" on two
    pull requests whose readme check passed forty seconds after being
    superseded.
    """

    def test_a_superseded_run_does_not_fail_the_pull_request(self) -> None:
        rollup = [
            {"name": "readme", "conclusion": "CANCELLED",
             "startedAt": "2026-09-01T01:48:40Z"},
            {"name": "readme", "conclusion": "SUCCESS",
             "startedAt": "2026-09-01T01:49:30Z"},
        ]
        self.assertEqual(refuse_bot_merge(pull(statusCheckRollup=rollup)), "")

    def test_the_order_they_arrive_in_does_not_matter(self) -> None:
        rollup = [
            {"name": "readme", "conclusion": "SUCCESS",
             "startedAt": "2026-09-01T01:49:30Z"},
            {"name": "readme", "conclusion": "CANCELLED",
             "startedAt": "2026-09-01T01:48:40Z"},
        ]
        self.assertEqual(refuse_bot_merge(pull(statusCheckRollup=rollup)), "")

    def test_a_genuine_failure_after_a_pass_still_counts(self) -> None:
        rollup = [
            {"name": "ci", "conclusion": "SUCCESS",
             "startedAt": "2026-09-01T01:00:00Z"},
            {"name": "ci", "conclusion": "FAILURE",
             "startedAt": "2026-09-01T02:00:00Z"},
        ]
        self.assertIn("failing", refuse_bot_merge(pull(statusCheckRollup=rollup)))

    def test_a_check_only_ever_cancelled_gave_no_answer(self) -> None:
        """No answer is not a pass, but it is not a failure either."""
        from harness.ship.bot_pr import latest_of_each

        rollup = [{"name": "ci", "conclusion": "CANCELLED",
                   "startedAt": "2026-09-01T01:00:00Z"}]
        self.assertEqual(len(latest_of_each({"statusCheckRollup": rollup})), 1)
        self.assertEqual(refuse_bot_merge(pull(statusCheckRollup=rollup)), "")

    def test_a_skipped_check_is_not_a_failure(self) -> None:
        rollup = [{"name": "celebrate", "conclusion": "SKIPPED"}]
        self.assertEqual(refuse_bot_merge(pull(statusCheckRollup=rollup)), "")


if __name__ == "__main__":
    unittest.main()
