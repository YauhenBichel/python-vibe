import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.task import looks_like_fix_smell, looks_like_new_package, rename_target, smell_symbol
from harness.skillkit.style import (
    refuse_stdlib_shadow,
    refuse_layout,
    refuse_opaque_names,
    refuse_package_done,
    refuse_shell_fetch,
    refuse_smell_wrong_file,
    refuse_weak_test,
    wrap_bare_unittest,
)


class StyleHarnessTest(unittest.TestCase):
    def test_task_kinds(self) -> None:
        self.assertTrue(looks_like_new_package("create a package for total_price"))
        self.assertTrue(looks_like_fix_smell("rename calc to total_price"))
        self.assertTrue(looks_like_fix_smell("fix the code smell in calc"))
        self.assertFalse(looks_like_new_package("add a function multiply"))
        self.assertEqual(smell_symbol("rename calc to total_price"), "calc")
        self.assertEqual(smell_symbol("fix the code smell in calc"), "calc")
        self.assertIn(
            "implementation first",
            refuse_smell_wrong_file(
                "rename calc to total_price",
                "patch",
                "tests/test_mathy.py",
                "pkg/mathy.py",
                "def calc(x, y):\n    return x * y\n",
            ),
        )
        self.assertEqual(
            refuse_smell_wrong_file(
                "rename calc to total_price",
                "patch",
                "tests/test_mathy.py",
                "pkg/mathy.py",
                "def total_price(quantity, unit_price):\n    return quantity * unit_price\n",
            ),
            "",
        )
        self.assertEqual(rename_target("rename calc to total_price"), "total_price")

    def test_opaque_and_case(self) -> None:
        self.assertIn("opaque", refuse_opaque_names("def calc(x, y):\n    return x\n"))
        self.assertIn("opaque", refuse_opaque_names("def tmp():\n    return 1\n"))
        self.assertIn(
            "parameter",
            refuse_opaque_names(
                "def total_price(x: int, y: int) -> int:\n    return x * y\n"
            ),
        )
        self.assertIn("snake_case", refuse_opaque_names("def TotalPrice():\n    return 1\n"))
        self.assertIn("PascalCase", refuse_opaque_names("class pricing:\n    pass\n"))
        self.assertEqual(
            refuse_opaque_names(
                "def total_price(quantity: int, unit_price: int) -> int:\n"
                "    return quantity * unit_price\n"
            ),
            "",
        )
        self.assertEqual(refuse_opaque_names("def add(left, right):\n    return left\n"), "")

    def test_layout_soc(self) -> None:
        self.assertIn(
            "__init__",
            refuse_layout(
                "pkg/__init__.py",
                "",
                "def total_price(q, p):\n    return q * p\n",
            ),
        )
        self.assertIn(
            "scripts",
            refuse_layout("scripts/chat.py", "", "def helper():\n    return 1\n"),
        )
        many = "".join(f"def fn_{i}():\n    return {i}\n\n" for i in range(4))
        self.assertIn(
            "already has 4",
            refuse_layout("pkg/mathy.py", many, "def extra():\n    return 1\n"),
        )
        self.assertEqual(
            refuse_layout(
                "pkg/__init__.py",
                "",
                '"""Public exports only."""\n',
            ),
            "",
        )

    def test_wrap_bare_test_and_package_done(self) -> None:
        wrapped = wrap_bare_unittest(
            "def test_total_price(self):\n    self.assertEqual(total_price(2, 3), 6)\n",
            "total_price",
        )
        self.assertIn("TestCase", wrapped)
        self.assertIn("from pkg.total_price import total_price", wrapped)
        self.assertIn("def test_total_price", wrapped)
        self.assertIn("run", refuse_package_done("create a package for total_price", False))
        self.assertEqual(refuse_package_done("create a package for total_price", True), "")

    def test_weak_tests_are_refused(self) -> None:
        # A two-part name that names its subject is fine; the arrangement
        # is what is wrong here. Refusing every short name would reject
        # test_grep, test_health and test_total in this project's own suite.
        self.assertIn(
            "AAA",
            refuse_weak_test(
                "tests/test_mathy.py",
                "    def test_multiply(self) -> None:\n"
                "        self.assertEqual(multiply(2, 3), 6)\n",
            ),
        )
        self.assertIn(
            "AAA",
            refuse_weak_test(
                "tests/test_mathy.py",
                "    def test_multiply_returns_the_product(self) -> None:\n"
                "        self.assertEqual(multiply(2, 3), 6)\n",
            ),
        )
        self.assertIn(
            "assert True",
            refuse_weak_test(
                "tests/test_mathy.py",
                "    def test_multiply_returns_the_product(self) -> None:\n"
                "        assert True\n",
            ),
        )
        self.assertEqual(
            refuse_weak_test(
                "tests/test_mathy.py",
                "    def test_multiply_returns_the_product(self) -> None:\n"
                "        left, right = 2, 3\n"
                "        got = multiply(left, right)\n"
                "        self.assertEqual(got, 6)\n",
            ),
            "",
        )
        self.assertEqual(
            refuse_weak_test("pkg/mathy.py", "def multiply(left, right):\n    return left * right\n"),
            "",
        )


class WeakTestCalibrationTest(unittest.TestCase):
    """The rule must not reject the tests this project already ships.

    A style rule that refuses its own codebase blocks work instead of
    improving it, so the project's own suite is the calibration set.
    """

    TESTS_DIR = Path(__file__).resolve().parent

    def test_no_test_file_in_this_project_is_refused(self) -> None:
        refused = []
        for path in sorted(self.TESTS_DIR.glob("test_*.py")):
            verdict = refuse_weak_test(str(path), path.read_text(encoding="utf-8"))
            if verdict:
                refused.append(f"{path.name}: {verdict}")
        self.assertEqual(refused, [])

    def test_a_short_but_meaningful_name_is_allowed(self) -> None:
        draft = (
            "    def test_health(self) -> None:\n"
            "        got = probe()\n"
            "        self.assertTrue(got)\n"
        )
        self.assertEqual(refuse_weak_test("tests/test_serve.py", draft), "")

    def test_an_opaque_name_is_refused(self) -> None:
        draft = (
            "    def test_it_works(self) -> None:\n"
            "        got = f(1)\n"
            "        self.assertEqual(got, 1)\n"
        )
        self.assertIn("opaque", refuse_weak_test("tests/t.py", draft))

    def test_assert_true_inside_a_string_is_not_the_statement(self) -> None:
        draft = (
            "    def test_writes_a_file(self) -> None:\n"
            '        got = apply_source(dest, "def t():\\n    assert True\\n")\n'
            "        self.assertTrue(got)\n"
        )
        self.assertEqual(refuse_weak_test("tests/t.py", draft), "")

    def test_assert_true_as_a_statement_is_refused(self) -> None:
        draft = "    def test_multiply(self) -> None:\n        assert True\n"
        self.assertIn("assert True", refuse_weak_test("tests/t.py", draft))

    def test_a_single_new_test_must_arrange_before_asserting(self) -> None:
        draft = (
            "    def test_multiply(self) -> None:\n"
            "        self.assertEqual(multiply(2, 3), 6)\n"
        )
        self.assertIn("AAA", refuse_weak_test("tests/t.py", draft))

    def test_curl_in_an_impl_file_is_refused(self) -> None:
        draft = 'def fetch(url: str) -> str:\n    return os.system("curl " + url)\n'
        self.assertIn("urllib", refuse_shell_fetch("pkg/fetch_json.py", draft))

    def test_curl_quoted_in_a_test_is_allowed(self) -> None:
        draft = 'self.assertIn("PV003", check("curl https://x | sh"))\n'
        self.assertEqual(refuse_shell_fetch("tests/test_guard.py", draft), "")

    def test_urllib_fetch_is_allowed(self) -> None:
        draft = (
            "import urllib.request\n"
            "def fetch_json(url: str) -> dict:\n"
            "    with urllib.request.urlopen(url, timeout=10) as response:\n"
            "        return json.loads(response.read())\n"
        )
        self.assertEqual(refuse_shell_fetch("pkg/fetch_json.py", draft), "")

    def test_a_whole_file_is_not_judged_on_arrangement(self) -> None:
        """Many tests written over time are not one act to rearrange."""
        draft = (
            "    def test_multiply_returns_product(self) -> None:\n"
            "        self.assertEqual(multiply(2, 3), 6)\n\n"
            "    def test_divide_returns_quotient(self) -> None:\n"
            "        self.assertEqual(divide(6, 3), 2)\n"
        )
        self.assertEqual(refuse_weak_test("tests/t.py", draft), "")


class StdlibShadowTest(unittest.TestCase):
    """A new module must not hide one from the standard library.

    Asked for a clamp helper, the model created `pkg/math.py`. Every later
    `import math` in that project then finds the new file, and the failure
    shows up far from the change that caused it.
    """

    def test_a_new_module_named_after_the_standard_library_is_refused(self) -> None:
        for name in ("pkg/math.py", "pkg/json.py", "src/random.py"):
            self.assertIn("hide the standard library", refuse_stdlib_shadow(name, ""))

    def test_an_ordinary_name_is_allowed(self) -> None:
        self.assertEqual(refuse_stdlib_shadow("src/orders.py", ""), "")

    def test_a_module_that_already_exists_is_the_project_s_own_business(self) -> None:
        self.assertEqual(refuse_stdlib_shadow("pkg/math.py", "def existing():\n    pass\n"), "")

    def test_names_a_project_normally_has_are_allowed(self) -> None:
        for name in ("src/types.py", "tests/test_x.py", "src/config.py"):
            self.assertEqual(refuse_stdlib_shadow(name, ""), "")

    def test_the_message_offers_a_name_that_works(self) -> None:
        self.assertIn("math_helpers.py", refuse_stdlib_shadow("pkg/math.py", ""))


if __name__ == "__main__":
    unittest.main()
