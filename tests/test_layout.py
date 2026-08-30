import tempfile
import unittest
from pathlib import Path

from harness.scan.layout import (
    find_cycles,
    find_flat_packages,
    find_god_modules,
    has_tests,
    render_layout,
    review_layout,
)

HARNESS = Path(__file__).resolve().parents[1] / "src" / "harness"


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CycleTest(unittest.TestCase):
    def test_two_modules_importing_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "alpha.py", "from beta import go\n")
            _write(root, "beta.py", "from alpha import back\n")
            self.assertEqual(find_cycles(root), [("alpha.py", "beta.py")])

    def test_one_way_import_is_not_a_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "alpha.py", "from beta import go\n")
            _write(root, "beta.py", "x = 1\n")
            self.assertEqual(find_cycles(root), [])

    def test_third_party_import_is_not_a_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "alpha.py", "from unittest import TestCase\n")
            self.assertEqual(find_cycles(root), [])

    def test_unparsable_module_is_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "alpha.py", "def broken(\n")
            self.assertEqual(find_cycles(root), [])

    def test_the_harness_itself_has_no_cycles(self) -> None:
        self.assertEqual(find_cycles(HARNESS), [])


class FlatAndGodTest(unittest.TestCase):
    def test_flat_package_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(15):
                _write(root, f"pkg/m{i}.py", "x = 1\n")
            flat = find_flat_packages(root)
        self.assertEqual(flat, [("pkg", 15)])

    def test_grouped_package_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for group in ("a", "b", "c"):
                for i in range(5):
                    _write(root, f"pkg/{group}/m{i}.py", "x = 1\n")
            self.assertEqual(find_flat_packages(root), [])

    def test_god_module_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(6):
                _write(root, f"m{i}.py", "x = 1\n")
            _write(root, "huge.py", "# pad\n" * 3000)
            god = find_god_modules(root)
        self.assertEqual([rel for rel, _size in god], ["huge.py"])

    def test_even_sizes_have_no_god_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(6):
                _write(root, f"m{i}.py", "# pad\n" * 2000)
            self.assertEqual(find_god_modules(root), [])


class ReviewTest(unittest.TestCase):
    def test_missing_tests_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "app.py", "x = 1\n")
            self.assertFalse(has_tests(root))
            self.assertIn("no-tests", [f.kind for f in review_layout(root)])

    def test_tests_present_clears_that_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "app.py", "x = 1\n")
            _write(root, "tests/test_app.py", "x = 1\n")
            self.assertTrue(has_tests(root))
            self.assertNotIn("no-tests", [f.kind for f in review_layout(root)])

    def test_cycle_outranks_everything_else(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "alpha.py", "from beta import go\n")
            _write(root, "beta.py", "from alpha import back\n")
            self.assertEqual(review_layout(root)[0].kind, "cycle")

    def test_clean_project_says_do_the_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "app.py", "x = 1\n")
            _write(root, "tests/test_app.py", "x = 1\n")
            self.assertIn("do the task", render_layout(root))

    def test_render_names_exactly_one_move(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "alpha.py", "from beta import go\n")
            _write(root, "beta.py", "from alpha import back\n")
            text = render_layout(root)
        self.assertEqual(text.count("Next move"), 1)


class SameFileNameIsNotACycleTest(unittest.TestCase):
    """Two modules that share a file name are still two modules.

    Measured on a 4,580-file project: four cycles reported, none real.
    One paired `surfaces/.../choice_menu.py` with
    `surfaces/.../streaming/console.py` because choice_menu imports
    `rich.console` — a third-party package matched on its last word.
    The others each paired one file with a different file of the same
    name somewhere else in the tree. Advice to merge two modules that do
    not import each other costs more than saying nothing.
    """

    def _tree(self, root: Path) -> None:
        (root / "one").mkdir()
        (root / "two").mkdir()
        (root / "one" / "__init__.py").write_text("", encoding="utf-8")
        (root / "two" / "__init__.py").write_text("", encoding="utf-8")
        # menu imports two.theme; a different theme.py imports menu.
        (root / "one" / "menu.py").write_text(
            "import two.theme\n", encoding="utf-8"
        )
        (root / "two" / "theme.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "one" / "theme.py").write_text(
            "from one.menu import x\n", encoding="utf-8"
        )

    def test_two_files_called_theme_do_not_make_a_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._tree(root)
            self.assertEqual(find_cycles(root), [])

    def test_a_third_party_import_is_not_a_local_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "console.py").write_text("import menu\n", encoding="utf-8")
            (root / "menu.py").write_text(
                "from rich.console import Console\n", encoding="utf-8"
            )
            self.assertEqual(find_cycles(root), [])

    def test_a_real_cycle_is_still_reported_with_its_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "pkg" / "left.py").write_text(
                "from pkg.right import r\n", encoding="utf-8"
            )
            (root / "pkg" / "right.py").write_text(
                "from pkg.left import l\n", encoding="utf-8"
            )
            self.assertEqual(find_cycles(root), [("pkg/left.py", "pkg/right.py")])

    def test_a_stdlib_name_matching_a_local_package_is_not_an_import(self) -> None:
        """`import logging` beside `infrastructure/logging/` is stdlib.

        Allowing a sub-project's own root to resolve (`src.report` inside
        demo/orders) first matched any tail, so a bare `import logging`
        resolved to the local package and invented two cycles on a real
        repository. Only a dotted path may be matched that way.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "infra").mkdir()
            (root / "infra" / "logging").mkdir()
            (root / "infra" / "__init__.py").write_text("", encoding="utf-8")
            (root / "infra" / "logging" / "__init__.py").write_text(
                "from infra.logging.quiet import hush\n", encoding="utf-8"
            )
            (root / "infra" / "logging" / "quiet.py").write_text(
                "import logging\n\n\ndef hush() -> None:\n    pass\n",
                encoding="utf-8",
            )
            self.assertEqual(find_cycles(root), [])

    def test_a_sub_projects_own_root_still_resolves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sub = root / "demo" / "app" / "src"
            sub.mkdir(parents=True)
            (sub / "__init__.py").write_text("", encoding="utf-8")
            (sub / "render.py").write_text(
                "from src.report import build\n", encoding="utf-8"
            )
            (sub / "report.py").write_text(
                "from src.render import line\n", encoding="utf-8"
            )
            self.assertEqual(
                find_cycles(root),
                [("demo/app/src/render.py", "demo/app/src/report.py")],
            )

    def test_a_relative_import_still_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (root / "pkg" / "left.py").write_text(
                "from .right import r\n", encoding="utf-8"
            )
            (root / "pkg" / "right.py").write_text(
                "from .left import l\n", encoding="utf-8"
            )
            self.assertEqual(find_cycles(root), [("pkg/left.py", "pkg/right.py")])


if __name__ == "__main__":
    unittest.main()
