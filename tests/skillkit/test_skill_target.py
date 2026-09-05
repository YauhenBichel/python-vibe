import tempfile
import unittest
from pathlib import Path

from harness.skillkit.target import (
    Target,
    pick_target,
    retarget,
)
from harness.skillkit.catalog import get_skill, render_skill

MODULE = "def compute_total(rows: list[int]) -> int:\n    return sum(rows)\n"
TEST = (
    "import unittest\n\n\nclass AppTest(unittest.TestCase):\n"
    "    def test_total(self) -> None:\n        self.assertEqual(1, 1)\n"
)


def _project(tmp: str) -> Path:
    project = Path(tmp)
    (project / "src").mkdir()
    (project / "tests").mkdir()
    (project / "src" / "app.py").write_text(MODULE, encoding="utf-8")
    (project / "tests" / "test_app.py").write_text(TEST, encoding="utf-8")
    return project


class PickTargetTest(unittest.TestCase):
    def test_picks_a_real_module_and_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = pick_target(_project(tmp), "add multiply")
        self.assertEqual(target.module, "src/app.py")
        self.assertEqual(target.test, "tests/test_app.py")
        self.assertEqual(target.scope, "src")
        self.assertEqual(target.symbol, "multiply")

    def test_located_path_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            (project / "src" / "other.py").write_text(MODULE * 4, encoding="utf-8")
            target = pick_target(project, "add multiply", located_path="src/app.py")
        self.assertEqual(target.module, "src/app.py")

    def test_test_file_is_never_the_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = pick_target(_project(tmp), "add x", located_path="tests/test_app.py")
        self.assertEqual(target.module, "src/app.py")

    def test_empty_project_gets_a_real_path_not_a_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = pick_target(Path(tmp), "add x")
        self.assertEqual(target.module, "src/main.py")
        self.assertNotIn("path/to/", target.module)

    def test_a_cli_app_task_names_pkg_not_weekday(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = pick_target(
                Path(tmp),
                "design and develop a small cli app for reviewing github PRs",
            )
        self.assertEqual(target.module, "pkg/pr_review.py")
        self.assertEqual(target.test, "tests/test_pr_review.py")
        self.assertEqual(target.symbol, "pr_review")


class RetargetTest(unittest.TestCase):
    def test_fixture_path_is_repointed(self) -> None:
        target = Target("src/app.py", "tests/test_app.py", "src", "multiply")
        with tempfile.TemporaryDirectory() as tmp:
            out = retarget("Action: patch\nPath: pkg/mathy.py\n", target, _project(tmp))
        self.assertIn("Path: src/app.py", out)
        self.assertNotIn("pkg/mathy.py", out)

    def test_a_path_that_exists_here_is_left_alone(self) -> None:
        target = Target("src/app.py", "tests/test_app.py", "src", "multiply")
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            (project / "pkg").mkdir()
            (project / "pkg" / "mathy.py").write_text(MODULE, encoding="utf-8")
            out = retarget("Path: pkg/mathy.py\n", target, project)
        self.assertIn("Path: pkg/mathy.py", out)

    def test_a_missing_test_path_goes_to_the_test_file(self) -> None:
        target = Target("src/app.py", "tests/test_app.py", "src", "multiply")
        with tempfile.TemporaryDirectory() as tmp:
            out = retarget("Path: tests/test_mathy.py\n", target, _project(tmp))
        self.assertIn("Path: tests/test_app.py", out)

    def test_new_package_init_is_left_alone(self) -> None:
        target = Target("src/app.py", "tests/test_app.py", "src", "multiply")
        with tempfile.TemporaryDirectory() as tmp:
            out = retarget("Path: pkg/__init__.py\n", target, _project(tmp))
        self.assertIn("Path: pkg/__init__.py", out)

    def test_placeholders_are_filled(self) -> None:
        target = Target("src/app.py", "tests/test_app.py", "src", "multiply")
        out = retarget("Path: {{module}}\nScope: {{scope}}\nQuery: {{symbol}}\n", target)
        self.assertIn("Path: src/app.py", out)
        self.assertIn("Scope: src", out)
        self.assertIn("Query: multiply", out)

    def test_symbol_token_is_filled(self) -> None:
        target = Target("src/app.py", "tests/test_app.py", "src", "multiply")
        out = retarget("Query: the_symbol_from_the_task\n", target)
        self.assertIn("Query: multiply", out)


class KitSkillTest(unittest.TestCase):
    def test_no_kit_skill_sends_a_fixture_path_into_a_real_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            target = pick_target(project, "add a function multiply(a, b) and a unit test")
            for name in ("add-feature", "write-tests", "fix-smell"):
                skill = get_skill(name)
                self.assertIsNotNone(skill, name)
                rendered = render_skill(skill, target, project)
                for line in rendered.splitlines():
                    if line.startswith(("Path:", "File:")):
                        rel = line.split(":", 1)[1].strip()
                        self.assertTrue(
                            (project / rel).is_file(),
                            f"{name} points at {rel}, which is not in this project",
                        )



class EmptyProjectTest(unittest.TestCase):
    """A project with nothing in it still needs a real path.

    The placeholder used to reach the model, which then created a file
    literally at `path/to/module.py`. That is the fixture-path fault
    arriving by another route, so the check is on the path itself.
    """

    def test_no_placeholder_reaches_the_model(self) -> None:
        from harness.skillkit.catalog import list_skills, render_skill

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            target = pick_target(project, "add a function multiply(a, b)")
            for skill in list_skills():
                rendered = render_skill(skill, target, project)
                for line in rendered.splitlines():
                    if line.startswith(("Path:", "File:")):
                        self.assertNotIn(
                            "path/to/", line, f"{skill.name} names a placeholder"
                        )

    def test_the_task_names_the_first_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = pick_target(Path(tmp), "add a function multiply(a, b)")
        self.assertEqual(target.module, "src/multiply.py")
        self.assertEqual(target.test, "tests/test_multiply.py")

    def test_a_task_naming_nothing_still_gets_a_real_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = pick_target(Path(tmp), "")
        self.assertEqual(target.module, "src/main.py")

    def test_an_existing_module_still_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "src").mkdir()
            (project / "src" / "app.py").write_text(
                "def go() -> int:\n    return 1\n", encoding="utf-8"
            )
            target = pick_target(project, "add a function multiply(a, b)")
        self.assertEqual(target.module, "src/app.py")

    def test_a_larger_controller_is_not_where_a_total_belongs(self) -> None:
        """Live 8B wrote total_lines into orders_controller.py (largest file)."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            src = project / "src"
            src.mkdir()
            (src / "orders.py").write_text(
                "def compute_total(prices):\n    return sum(prices)\n"
                "def total_with_tax(prices):\n    return sum(prices)\n",
                encoding="utf-8",
            )
            (src / "orders_controller.py").write_text(
                "class OrdersController:\n"
                "    def handle(self, body):\n        return body\n"
                "    def status(self):\n        return 'ok'\n"
                + ("    # padding\n" * 20),
                encoding="utf-8",
            )
            target = pick_target(
                project,
                "add a function total_lines(prices) that counts the prices",
            )
        self.assertEqual(target.module, "src/orders.py")


if __name__ == "__main__":
    unittest.main()
