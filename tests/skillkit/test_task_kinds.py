"""Which kind of work a task asks for.

Every layer reads the task through these functions, so a wrong answer here
sends the wrong skill and the wrong first action.
"""

import unittest

from harness.skillkit.catalog import list_skills, pick_skills
from harness.task import (
    looks_like_add_feature,
    looks_like_bugfix,
    looks_like_design_loop,
    looks_like_app_loop,
    looks_like_app_overflow,
    looks_like_new_package,
    looks_like_question,
    looks_like_review_code,
    looks_like_script,
    looks_like_ship,
    looks_unclear,
    mentions_cli,
    mentions_http,
    names_something_concrete,
    package_noun,
)


class ConcreteTest(unittest.TestCase):
    def test_a_call_is_concrete(self) -> None:
        self.assertTrue(names_something_concrete("add multiply(a, b)"))

    def test_a_file_path_is_concrete(self) -> None:
        self.assertTrue(names_something_concrete("review src/app.py"))

    def test_a_snake_case_name_is_concrete(self) -> None:
        self.assertTrue(names_something_concrete("rename calc to total_price"))

    def test_plain_english_is_not_concrete(self) -> None:
        self.assertFalse(names_something_concrete("clean this up"))


class UnclearTest(unittest.TestCase):
    def test_a_vague_short_task_is_unclear(self) -> None:
        for task in ("clean this up", "make it better", "tidy"):
            self.assertTrue(looks_unclear(task), task)

    def test_a_recognised_kind_is_workable_even_when_short(self) -> None:
        """A kind the harness has a first action for does not need a question."""
        for task in ("fix the thing", "add a helper", "create a package"):
            self.assertFalse(looks_unclear(task), task)

    def test_a_task_naming_a_symbol_is_clear(self) -> None:
        self.assertFalse(looks_unclear("add multiply(a, b) and a test"))

    def test_a_question_is_never_unclear(self) -> None:
        self.assertFalse(looks_unclear("what does it do?"))

    def test_a_long_task_is_not_treated_as_unclear(self) -> None:
        self.assertFalse(
            looks_unclear("go through the tree and tidy the naming everywhere please")
        )


class ReviewTest(unittest.TestCase):
    def test_review_is_review(self) -> None:
        self.assertTrue(looks_like_review_code("review src/app.py for bugs"))

    def test_adding_is_not_review(self) -> None:
        self.assertFalse(looks_like_review_code("add multiply(a, b)"))

    def test_a_question_is_still_a_question(self) -> None:
        self.assertTrue(looks_like_question("what does compute_total return?"))
        self.assertFalse(looks_like_add_feature("what does compute_total return?"))


class SkillChoiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = list_skills()

    def _names(self, task: str) -> list[str]:
        return [item.name for item in pick_skills(task, self.catalog)]

    def test_vague_task_offers_the_asking_skill(self) -> None:
        self.assertIn("ask-when-unclear", self._names("clean this up"))

    def test_review_task_offers_the_review_skill(self) -> None:
        self.assertIn("review-code", self._names("find bugs in src/app.py"))

    def test_design_loop_offers_review_and_split(self) -> None:
        names = self._names("review the project structure")
        self.assertIn("review-design", names)
        self.assertIn("refactor-split", names)
        self.assertIn("readable-layout", names)

    def test_nameerror_is_a_bugfix(self) -> None:
        self.assertTrue(looks_like_bugfix("find a real NameError and fix it"))
        self.assertFalse(looks_like_bugfix("fix the code smell in calc"))
        self.assertTrue(looks_like_design_loop("review the design then one-split"))
        self.assertFalse(looks_like_design_loop("review src/orders.py for bugs"))
        self.assertTrue(looks_like_design_loop("review the project structure"))

    def test_add_task_still_offers_add_and_tests(self) -> None:
        names = self._names("add multiply(a, b) and a unit test")
        self.assertIn("add-feature", names)
        self.assertIn("write-tests", names)

    def test_a_clear_task_is_not_offered_the_asking_skill(self) -> None:
        self.assertNotIn(
            "ask-when-unclear", self._names("add multiply(a, b) and a test")
        )


CLI_APP = "design and develop a small cli app for reviewing github PRs"


class GreenfieldCliTest(unittest.TestCase):
    """A typed 'build a CLI' prompt is a new package, not a weekday copy."""

    def test_design_a_cli_app_is_a_new_package(self) -> None:
        self.assertTrue(looks_like_new_package(CLI_APP))
        self.assertTrue(looks_like_new_package("develop a small cli app for tallying csv"))
        self.assertTrue(looks_like_new_package("build a small CLI for reviewing GitHub pull requests"))
        self.assertTrue(looks_like_new_package("design a develop a small cli app for reviewing github PRs"))
        self.assertFalse(looks_like_new_package("write a weekday script from argv"))
        self.assertFalse(looks_like_new_package("review the project structure"))
        self.assertFalse(looks_like_new_package("create a pr for #50"))
        self.assertFalse(looks_like_new_package("add a function multiply"))

    def test_it_is_not_a_design_loop_or_a_ship(self) -> None:
        self.assertFalse(looks_like_design_loop(CLI_APP))
        self.assertFalse(looks_like_ship(CLI_APP))
        self.assertFalse(looks_like_script(CLI_APP))
        self.assertTrue(looks_like_app_loop(CLI_APP))
        self.assertFalse(looks_like_app_loop("create a package for total_price"))

    def test_github_pr_cli_names_pr_review_and_http(self) -> None:
        self.assertEqual(package_noun(CLI_APP), "pr_review")
        self.assertEqual(package_noun("create a package for total_price"), "total_price")
        self.assertEqual(package_noun("create a package"), "service")
        self.assertTrue(mentions_cli(CLI_APP))
        self.assertTrue(mentions_http(CLI_APP))

    def test_pick_scaffolds_then_http_then_tests(self) -> None:
        catalog = list_skills()
        names = [item.name for item in pick_skills(CLI_APP, catalog)]
        self.assertEqual(
            names, ["new-package", "write-cli-app", "call-http", "write-tests"]
        )
        self.assertNotIn("write-script", names)
        self.assertNotIn("review-design", names)
        self.assertNotIn("open-pr", names)


OVERFLOW = "add the comment subcommand and a mocked test"


class AppOverflowTest(unittest.TestCase):
    def test_comment_run_is_overflow_not_a_new_package(self) -> None:
        self.assertTrue(looks_like_app_overflow(OVERFLOW))
        self.assertFalse(looks_like_app_loop(OVERFLOW))
        self.assertFalse(looks_like_new_package(OVERFLOW))
        self.assertEqual(package_noun(OVERFLOW), "pr_review")

    def test_pick_does_not_offer_add_feature(self) -> None:
        names = [item.name for item in pick_skills(OVERFLOW, list_skills())]
        self.assertEqual(names, ["write-cli-app", "call-http", "write-tests"])
        self.assertNotIn("add-feature", names)

    def test_a_plain_add_is_not_overflow(self) -> None:
        self.assertFalse(looks_like_app_overflow("add a function multiply"))


if __name__ == "__main__":
    unittest.main()
