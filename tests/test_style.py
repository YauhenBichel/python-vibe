import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.task import looks_like_fix_smell, looks_like_new_package, rename_target, smell_symbol
from harness.skillkit.style import (
    refuse_done_oracle,
    refuse_stub_body,
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
            refuse_weak_test(
                "tests/test_mathy.py",
                "    def test_weekday_returns_day_name(self) -> None:\n"
                "        day_index = 2\n"
                "        got = weekday(day_index)\n"
                "        self.assertEqual(got, 'Tuesday')\n",
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


class AnImportIsNotCoverageTest(unittest.TestCase):
    """A `write tests` run must leave a test that calls the symbol.

    Measured on a real repository, not the demo tree: asked to cover
    `redact_slack_token`, the run wrote a file holding one import line
    and nothing else, and reported `done`. The oracle asked only whether
    the name appeared anywhere in tests/, and it did — in that import.
    `unittest discover` found no tests at all.
    """

    TASK = (
        "write tests for redact_slack_token in "
        "infrastructure/delivery/notifications/redaction.py"
    )

    def _project(self, tmp: str, test_body: str) -> Path:
        root = Path(tmp)
        pkg = root / "infrastructure" / "delivery" / "notifications"
        pkg.mkdir(parents=True)
        for part in (root / "infrastructure", root / "infrastructure" / "delivery", pkg):
            (part / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "redaction.py").write_text(
            "def redact_slack_token(text: str, token: str) -> str:\n"
            "    return text.replace(token, '<redacted>')\n",
            encoding="utf-8",
        )
        tests = root / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_redaction.py").write_text(test_body, encoding="utf-8")
        return root

    IMPORT_ONLY = (
        "from infrastructure.delivery.notifications.redaction import "
        "redact_slack_token\n"
    )
    REAL_TEST = (
        "import unittest\n\n"
        "from infrastructure.delivery.notifications.redaction import "
        "redact_slack_token\n\n\n"
        "class TestRedaction(unittest.TestCase):\n"
        "    def test_redact_slack_token_hides_the_token(self) -> None:\n"
        "        got = redact_slack_token('a xoxb-1 b', 'xoxb-1')\n"
        "        self.assertIn('<redacted>', got)\n"
    )

    def test_a_file_holding_only_an_import_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp, self.IMPORT_ONLY)
            blocked = refuse_done_oracle(self.TASK, root, "")
        self.assertIn("no test calls redact_slack_token", blocked)

    def test_a_real_test_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp, self.REAL_TEST)
            self.assertEqual(refuse_done_oracle(self.TASK, root, ""), "")

    def test_the_name_in_a_comment_is_not_a_test(self) -> None:
        body = (
            "import unittest\n\n\n"
            "class TestRedaction(unittest.TestCase):\n"
            "    def test_placeholder(self) -> None:\n"
            "        # redact_slack_token goes here\n"
            "        self.assertTrue(True)\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp, body)
            blocked = refuse_done_oracle(self.TASK, root, "")
        self.assertIn("no test calls redact_slack_token", blocked)

class StubBodyTest(unittest.TestCase):
    """`def slugify(text): ...` parses, names right, and does nothing.

    A live 8B wrote exactly that when asked to create the function, and
    nothing rejected it: it is valid Python with a sensible name.
    """

    TASK = "create a function slugify(text) that lowercases and joins words"

    def test_an_ellipsis_body_is_refused(self) -> None:
        blocked = refuse_stub_body(
            self.TASK, "src/orders.py", "def slugify(text: str) -> str: ...\n"
        )
        self.assertIn("no body", blocked)

    def test_a_pass_body_is_refused(self) -> None:
        blocked = refuse_stub_body(
            self.TASK, "src/orders.py", "def slugify(text):\n    pass\n"
        )
        self.assertIn("no body", blocked)

    def test_a_real_body_is_allowed(self) -> None:
        self.assertEqual(
            refuse_stub_body(
                self.TASK,
                "src/orders.py",
                "def slugify(text):\n    return text.lower()\n",
            ),
            "",
        )

    def test_a_docstring_plus_a_body_is_allowed(self) -> None:
        draft = 'def slugify(text):\n    """Lowercase it."""\n    return text.lower()\n'
        self.assertEqual(refuse_stub_body(self.TASK, "src/orders.py", draft), "")

    def test_a_test_file_is_not_judged(self) -> None:
        self.assertEqual(
            refuse_stub_body(self.TASK, "tests/test_x.py", "def slugify(t): ...\n"),
            "",
        )


class EveryRuleIsWiredTest(unittest.TestCase):
    """A rule that is written and not listed does nothing.

    The refusals used to run as thirty lines of `blocked = rule(...); if
    blocked: return blocked`, eleven times over, which hid both the order
    they run in and the fact that a new rule has to be added to it. I
    added `refuse_stub_body` and only found the missing line because a
    mutation check went green with the call removed.
    """

    # Rules that judge a proposed change. Anything else in style.py
    # answers a different question and is called from somewhere else.
    NOT_ABOUT_A_DRAFT = {
        "refuse_done_oracle",      # judges the project after a run
        "refuse_write_done",       # judges whether a run may finish
        "refuse_package_done",     # the same, for a new package
        "refuse_god_target",       # judges the file a change would target
        "refuse_smell_wrong_file",
        "refuse_opaque_names",     # called from the draft rules themselves
        "refuse_duplicate_module",
        "refuse_missing_import_target",
    }

    def test_every_draft_rule_is_in_the_list(self) -> None:
        import ast

        from harness.act.gate import STYLE_RULES

        source = (ROOT / "src" / "harness" / "skillkit" / "style.py").read_text(
            encoding="utf-8"
        )
        written = {
            node.name
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name.startswith("refuse_")
        }
        listed = (ROOT / "src" / "harness" / "act" / "gate.py").read_text(
            encoding="utf-8"
        )
        start = listed.index("STYLE_RULES")
        table = listed[start : listed.index("def style_blocks")]
        missing = sorted(
            name
            for name in written - self.NOT_ABOUT_A_DRAFT
            if name not in table
        )
        self.assertEqual(
            missing,
            [],
            f"written but never run: {missing}. Add it to STYLE_RULES, "
            "or to NOT_ABOUT_A_DRAFT with the reason.",
        )
        self.assertEqual(len(STYLE_RULES), 11)

    def test_each_entry_is_named_and_callable(self) -> None:
        from harness.act.gate import STYLE_RULES

        for name, rule in STYLE_RULES:
            with self.subTest(rule=name):
                self.assertTrue(name.strip())
                self.assertTrue(callable(rule))

    def test_the_rules_run_in_order_and_stop_at_the_first(self) -> None:
        from harness.act.gate import ProposedChange, style_blocks

        change = ProposedChange(
            task="add a helper",
            rel="pkg/math.py",          # shadows the standard library
            original="",
            draft="def f():\n    return 1\n",
        )
        first = style_blocks(
            change.task, change.rel, change.original, change.draft
        )
        self.assertIn("math", first, "the earliest rule should answer")


class FileOperationsHaveNoSymbolTest(unittest.TestCase):
    """Moving a file is not a job with a function name in it.

    Asked to "create a new module and move the helpers into it", the
    harness read `create` as the symbol, looked for a test naming it,
    found the word somewhere, and answered "already has a test for
    create". Nothing was created and nothing moved.
    """

    OPERATIONS = (
        "create a new module src/x.py and move the helpers into it",
        "move src/a.py to src/b.py",
        "rename src/a.py to src/b.py",
        "split cover.py into two modules",
        "delete src/old.py",
    )
    NOT_OPERATIONS = (
        "add a function total_lines and a test",
        "write tests for apply_discount",
        "fix the NameError in src/orders.py",
        "review src/orders.py for bugs",
    )

    def test_a_file_operation_is_recognised(self) -> None:
        from harness.task import looks_like_file_operation

        for task in self.OPERATIONS:
            with self.subTest(task=task):
                self.assertTrue(looks_like_file_operation(task))

    def test_ordinary_work_is_not_mistaken_for_one(self) -> None:
        from harness.task import looks_like_file_operation

        for task in self.NOT_OPERATIONS:
            with self.subTest(task=task):
                self.assertFalse(looks_like_file_operation(task))

    def test_the_opening_verb_is_not_a_symbol(self) -> None:
        from harness.task import question_symbol

        for task, wanted in (
            ("create a function slugify(text) that lowercases", "slugify"),
            ("add a function total_lines and a test", "total_lines"),
        ):
            with self.subTest(task=task):
                self.assertEqual(question_symbol(task), wanted)

    def test_no_cover_test_is_written_for_a_move(self) -> None:
        from harness.act.autofix import apply_cover_test

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tests").mkdir()
            (root / "tests" / "test_x.py").write_text(
                "def test_create_works():\n    pass\n", encoding="utf-8"
            )
            for task in self.OPERATIONS:
                with self.subTest(task=task):
                    self.assertEqual(apply_cover_test(root, task, write=False), "")



if __name__ == "__main__":
    unittest.main()
