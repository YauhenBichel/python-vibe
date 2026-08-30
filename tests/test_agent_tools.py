import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.act.tools import (
    edit_py,
    grep_py,
    map_py,
    patch_py,
    read_py,
    refuse_duplicate_module,
    repair_unittest_append,
    run_python,
)
from harness.act.code import resolve_project_file


class AgentToolsTest(unittest.TestCase):
    def test_resolve_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("print(1)\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                resolve_project_file(root, "../secret.py")

    def test_read_stays_inside_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("print(1)\n", encoding="utf-8")
            self.assertIn("print(1)", read_py(root, "ok.py"))

    def test_edit_keeps_bak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "ok.py"
            original = "\n".join(f"value_{i} = {i}" for i in range(20)) + "\n"
            dest.write_text(original, encoding="utf-8")
            rewrite = "\n".join(f"value_{i} = {i + 1}" for i in range(20)) + "\n"
            edit_py(root, "ok.py", rewrite)
            self.assertIn("value_0 = 1", dest.read_text(encoding="utf-8"))
            self.assertTrue(dest.with_suffix(".py.bak").is_file())

    def test_edit_refuses_a_god_module(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "kitchen.py"
            dest.write_text(
                "def one():\n    return 1\n\n"
                "def two():\n    return 2\n\n"
                "def three():\n    return 3\n\n"
                "def four():\n    return 4\n",
                encoding="utf-8",
            )
            result = edit_py(root, "kitchen.py", "def one():\n    return 1\n")
            self.assertIn("already has 4", result)
            self.assertIn("def four", dest.read_text(encoding="utf-8"))

    def test_patch_append_adds_function(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "ok.py"
            dest.write_text("def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")
            out = patch_py(
                root,
                "ok.py",
                "",
                "",
                append="def multiply(a: int, b: int) -> int:\n    return a * b\n",
            )
            self.assertIn("patched", out)
            text = dest.read_text(encoding="utf-8")
            self.assertIn("def add", text)
            self.assertIn("def multiply", text)

    def test_patch_one_occurrence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "ok.py"
            body = "\n".join(f"value_{i} = {i}" for i in range(20)) + "\nreturn tota\n"
            dest.write_text(body, encoding="utf-8")
            out = patch_py(root, "ok.py", "return tota", "return sum(cleaned)")
            self.assertIn("patched", out)
            self.assertIn("return sum(cleaned)", dest.read_text(encoding="utf-8"))

    def test_patch_rejects_short_find(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "ok.py"
            dest.write_text("\n".join(f"value_{i} = {i}" for i in range(20)) + "\n", encoding="utf-8")
            out = patch_py(root, "ok.py", "tota", "sum(x)")
            self.assertIn("8 characters", out)

    def test_grep_finds_markdown_and_respects_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("def apply_source():\n    pass\n", encoding="utf-8")
            (root / "README.md").write_text("apply_source creates parent dirs\n", encoding="utf-8")
            hits = grep_py(root, "apply_source")
            self.assertIn("README.md", hits)
            self.assertIn("src/a.py", hits)
            scoped = grep_py(root, "apply_source", scope="src")
            self.assertIn("src/a.py", scoped)
            self.assertNotIn("README.md", scoped)

    def test_map_lists_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "ok.py").write_text("print(1)\n", encoding="utf-8")
            out = map_py(root)
            self.assertIn("ok.py", out)

    def test_repair_unittest_append_places_method(self) -> None:
        original = (
            "from pkg.mathy import add\n\n"
            "class TestMathy(unittest.TestCase):\n"
            "    def test_add(self) -> None:\n"
            "        self.assertEqual(add(2, 3), 5)\n\n"
            "if __name__ == \"__main__\":\n"
            "    unittest.main()\n"
        )
        append = (
            "    def test_multiply(self) -> None:\n"
            "        self.assertEqual(multiply(2, 3), 6)\n"
        )
        out = repair_unittest_append(original, append)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertIn("from pkg.mathy import add, multiply", out)
        self.assertLess(out.index("def test_multiply"), out.index("if __name__"))
        self.assertIn("class TestMathy", out.split("def test_multiply")[0])

    def test_patch_refuses_a_duplicate_test_method(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "tests"
            dest.mkdir()
            dest.joinpath("test_mathy.py").write_text(
                "import unittest\n\n"
                "from pkg.mathy import add\n\n"
                "class TestMathy(unittest.TestCase):\n"
                "    def test_add_returns_the_sum(self) -> None:\n"
                "        got = add(2, 3)\n"
                "        self.assertEqual(got, 5)\n",
                encoding="utf-8",
            )
            out = patch_py(
                root,
                "tests/test_mathy.py",
                "",
                "",
                "    def test_add_returns_the_sum(self) -> None:\n"
                "        got = add(2, 3)\n"
                "        self.assertEqual(got, 5)\n",
            )
        self.assertIn("already exists", out)

    def test_patch_refuses_a_test_that_asserts_without_arranging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / "tests"
            dest.mkdir()
            # A real test file imports what it calls, so the harness can
            # extend that line. Without one, the missing import is the more
            # serious fault and is refused first.
            dest.joinpath("test_mathy.py").write_text(
                "import unittest\n\n"
                "from pkg.mathy import add\n\n"
                "class TestMathy(unittest.TestCase):\n"
                "    def test_add_returns_the_sum(self) -> None:\n"
                "        got = add(2, 3)\n"
                "        self.assertEqual(got, 5)\n",
                encoding="utf-8",
            )
            weak = patch_py(
                root,
                "tests/test_mathy.py",
                "",
                "",
                "    def test_multiply(self) -> None:\n"
                "        self.assertEqual(multiply(2, 3), 6)\n",
            )
            # The name says what it tests; the arrangement is the problem.
            self.assertIn("AAA", weak)
            good = patch_py(
                root,
                "tests/test_mathy.py",
                "",
                "",
                "    def test_multiply_returns_the_product(self) -> None:\n"
                "        left, right = 2, 3\n"
                "        got = multiply(left, right)\n"
                "        self.assertEqual(got, 6)\n",
            )
            self.assertTrue(good.startswith("patched"), good)
            body = dest.joinpath("test_mathy.py").read_text(encoding="utf-8")
            self.assertIn("got = multiply", body)

    def test_run_refuses_dash_c(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = run_python(Path(tmp), ("-c", "print(1)"))
        self.assertIn("refusing", out)


class ImportRepairFollowsTheStyleRulesTest(unittest.TestCase):
    """The import repair and the style rules used to contradict each other.

    The repair read the called name out of `assertEqual(multiply(...))`.
    The style rules ask for the opposite shape — assign to `got`, then
    assert `got` — so a test written the way the harness demands never got
    its import, and the suite went red. Seen in an editor session.
    """

    ORIGINAL = (
        "import unittest\n\n"
        "from src.orders import compute_total\n\n\n"
        "class TestOrders(unittest.TestCase):\n"
        "    def test_compute_total_sums(self) -> None:\n"
        "        self.assertEqual(compute_total([1, 2]), 3)\n"
    )

    def _append(self, body: str) -> str:
        from harness.act.gate import repair_unittest_append

        out = repair_unittest_append(self.ORIGINAL, body)
        self.assertIsNotNone(out)
        assert out is not None
        return out

    def test_the_arranged_shape_gets_its_import(self) -> None:
        out = self._append(
            "    def test_total_lines_counts(self) -> None:\n"
            "        prices = [1, 2, 3]\n"
            "        got = total_lines(prices)\n"
            "        self.assertEqual(got, 3)\n"
        )
        self.assertIn("from src.orders import compute_total, total_lines", out)

    def test_the_inline_shape_still_gets_its_import(self) -> None:
        out = self._append(
            "    def test_total_lines_counts(self) -> None:\n"
            "        self.assertEqual(total_lines([1, 2, 3]), 3)\n"
        )
        self.assertIn("total_lines", out.splitlines()[2])

    def test_the_result_has_no_unbound_name(self) -> None:
        from harness.scan.names import undefined_names

        out = self._append(
            "    def test_total_lines_counts(self) -> None:\n"
            "        got = total_lines([1, 2, 3])\n"
            "        self.assertEqual(got, 3)\n"
        )
        self.assertEqual(undefined_names(out), [])


class DuplicateModuleTest(unittest.TestCase):
    """Live 8B wrote pkg/orders.py after src/orders.py already existed."""

    def test_a_second_orders_module_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text("def compute_total():\n    return 0\n")
            blocked = refuse_duplicate_module(root, "pkg/orders.py", "")
        self.assertIn("src/orders.py", blocked)
        self.assertIn("patch Path: src/orders.py", blocked)

    def test_patching_the_existing_module_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            original = "def compute_total():\n    return 0\n"
            (root / "src" / "orders.py").write_text(original)
            self.assertEqual(
                refuse_duplicate_module(root, "src/orders.py", original), ""
            )

class DuplicateDefinitionTest(unittest.TestCase):
    """Appending a function the file already defines is refused.

    Only `def test_...` was checked, so an ordinary function could go in
    twice: a live run appended `def slugify` to one file on two separate
    turns and left both there.
    """

    ORIGINAL = (
        "def compute_total(prices):\n"
        "    return sum(prices)\n\n\n"
        "def slugify(text):\n"
        "    return text.lower()\n"
    )

    def _project(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "orders.py").write_text(self.ORIGINAL, encoding="utf-8")
        return root

    def test_a_second_copy_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = patch_py(
                self._project(tmp),
                "src/orders.py",
                "",
                "",
                "def slugify(text):\n    return text.upper()\n",
            )
        self.assertIn("already defined", out)

    def test_a_genuinely_new_function_still_goes_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            out = patch_py(
                root,
                "src/orders.py",
                "",
                "",
                "def shout(text):\n    return text.upper()\n",
            )
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertNotIn("already defined", out)
        self.assertIn("def shout", body)
        self.assertEqual(body.count("def slugify"), 1)


class EditRepairsGoThroughTheToolTest(unittest.TestCase):
    """The repairs must be reachable from `edit`, not just importable.

    Both were first tested by calling the helper directly, so removing
    the call from `edit_py` left every test passing. A mutation check
    caught that; these go through the tool.
    """

    ORIGINAL = (
        '"""Order arithmetic."""\n\n\n'
        "def compute_total(prices: list[int]) -> int:\n"
        "    return sum(prices)\n\n\n"
        "def apply_discount(total: int, percent: int) -> int:\n"
        "    return total - (total * percent) // 100\n"
    )

    def _project(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "src").mkdir()
        (root / "src" / "orders.py").write_text(self.ORIGINAL, encoding="utf-8")
        return root

    def test_a_short_new_function_is_appended_not_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            out = edit_py(
                root,
                "src/orders.py",
                "def slugify(text: str) -> str:\n"
                "    return '-'.join(w.lower() for w in text.split())\n",
                task="add a function slugify(text) and a unit test",
            )
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertNotIn("too short", out)
        self.assertIn("appended", out)
        self.assertIn("def compute_total", body)
        namespace: dict = {}
        exec(compile(body, "m", "exec"), namespace)
        self.assertEqual(namespace["slugify"]("Hello There"), "hello-there")

    def test_a_stub_body_is_refused_through_edit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            out = edit_py(
                root,
                "src/orders.py",
                "def slugify(text: str) -> str: ...\n",
                task="add a function slugify(text) and a unit test",
            )
            body = (root / "src" / "orders.py").read_text(encoding="utf-8")
        self.assertIn("no body", out)
        self.assertNotIn("def slugify", body)


class ActionTableTest(unittest.TestCase):
    """Every action the model may take has somewhere to go.

    This was nineteen `if turn.action == ...` tests in a row, which hid
    both the list and the fact that a new action has to be added to it.
    Forgetting produced a silent "unknown Action" rather than an error
    anybody would notice.
    """

    HANDLED_BY_THE_LOOP = {"ask", "done"}

    def test_the_table_and_the_advertised_list_agree(self) -> None:
        from harness.agent.dispatch import ACTIONS, HANDLERS

        advertised = set(ACTIONS.replace("|", " ").split())
        self.assertEqual(
            advertised - set(HANDLERS) - self.HANDLED_BY_THE_LOOP,
            set(),
            "advertised to the model with nothing to carry it out",
        )
        self.assertEqual(
            set(HANDLERS) - advertised,
            set(),
            "carried out but never offered to the model",
        )

    def test_every_entry_is_callable(self) -> None:
        from harness.agent.dispatch import HANDLERS

        for name, handler in HANDLERS.items():
            with self.subTest(action=name):
                self.assertTrue(callable(handler))

    def test_an_action_nobody_wrote_says_so(self) -> None:
        from harness.act.parse import parse_turn
        from harness.agent.dispatch import run_action

        turn = parse_turn("Action: teleport\nPath: x.py")
        with tempfile.TemporaryDirectory() as tmp:
            out, path = run_action(Path(tmp), turn, "kept.py", "")
        self.assertIn("unknown Action", out)
        self.assertEqual(path, "kept.py", "an unknown action moves nothing")

    def test_a_read_without_a_path_keeps_the_last_one(self) -> None:
        from harness.act.parse import parse_turn
        from harness.agent.dispatch import run_action

        turn = parse_turn("Action: read")
        with tempfile.TemporaryDirectory() as tmp:
            out, path = run_action(Path(tmp), turn, "", "")
        self.assertIn("needs Path", out)
        self.assertEqual(path, "")



if __name__ == "__main__":
    unittest.main()
