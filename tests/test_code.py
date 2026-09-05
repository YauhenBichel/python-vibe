import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from harness.code import (
    apply_source,
    extract_python,
    is_traceback_source,
    read_project_file,
    resolve_project_file,
    write_and_run,
    write_and_run_fixed,
)


class ExtractPythonTest(unittest.TestCase):
    def test_longest_fence(self) -> None:
        text = "note\n```python\nx=1\n```\n```python\nx = 2\ny = 3\n```\n"
        self.assertEqual(extract_python(text), "x = 2\ny = 3")

    def test_bare_script(self) -> None:
        self.assertEqual(extract_python("import os\nprint(1)\n"), "import os\nprint(1)")

    def test_no_code(self) -> None:
        self.assertIsNone(extract_python("sorry, I cannot help with that"))

    def test_rejects_traceback_fence(self) -> None:
        self.assertTrue(is_traceback_source("TypeError: can only join an iterable\n"))
        self.assertIsNone(
            extract_python("```python\nTraceback (most recent call last):\n  File x\n```")
        )
        self.assertIsNone(
            extract_python("```python\nTypeError: can only join an iterable\n```")
        )


class PathJailTest(unittest.TestCase):
    def test_stays_inside_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pkg").mkdir()
            dest = resolve_project_file(root, "pkg/mod.py")
            self.assertEqual(dest, (root / "pkg" / "mod.py").resolve())

    def test_rejects_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "proj"
            root.mkdir()
            with self.assertRaises(ValueError):
                resolve_project_file(root, "../secret.py")

    def test_rejects_venv_and_non_py(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".venv").mkdir()
            with self.assertRaises(ValueError):
                resolve_project_file(root, ".venv/x.py")
            with self.assertRaises(ValueError):
                resolve_project_file(root, "notes.md")


class ApplySourceTest(unittest.TestCase):
    def test_refuses_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.py"
            with self.assertRaises(ValueError):
                apply_source(path, "  \n", original="")

    def test_refuses_shrink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.py"
            original = "x" * 200
            with self.assertRaises(ValueError):
                apply_source(path, "print(1)\n", original=original)

    def test_writes_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.py"
            path.write_text("old\n", encoding="utf-8")
            apply_source(path, "print(1)\n", original="")
            self.assertEqual(path.read_text(encoding="utf-8"), "print(1)\n")
            self.assertEqual(path.with_suffix(".py.bak").read_text(encoding="utf-8"), "old\n")


class WriteAndRunTest(unittest.TestCase):
    def test_stdin_and_argv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "echo.py"
            source = "import sys\nprint(sys.argv[1], sys.stdin.read(), sep='')\n"
            result = write_and_run(source, dest, ["hi"], stdin=" there")
            self.assertEqual(result.code, 0)
            self.assertEqual(result.stdout, "hi there\n")

    def test_prepends_missing_sys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "argv.py"
            result, fixed = write_and_run_fixed("print(sys.argv[1])\n", dest, ["hi"])
            self.assertTrue(fixed)
            self.assertEqual(result.code, 0)
            self.assertEqual(result.stdout, "hi\n")

    def test_prepends_from_datetime_for_strptime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "day.py"
            source = (
                "date_obj = datetime.strptime('2026-09-05', '%Y-%m-%d')\n"
                "print(date_obj.strftime('%A'))\n"
            )
            result, fixed = write_and_run_fixed(source, dest)
            self.assertTrue(fixed)
            self.assertEqual(result.code, 0)
            self.assertEqual(result.stdout, "Saturday\n")

    def test_prepends_import_datetime_for_module_use(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "iso.py"
            source = "print(datetime.date(2026, 9, 5).isoformat())\n"
            result, fixed = write_and_run_fixed(source, dest)
            self.assertTrue(fixed)
            self.assertEqual(result.code, 0)
            self.assertEqual(result.stdout, "2026-09-05\n")

    def test_read_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.py"
            path.write_text("a" * 80, encoding="utf-8")
            text = read_project_file(path, limit=10)
            self.assertTrue(text.startswith("aaaaaaaaaa"))
            self.assertIn("truncated", text)


if __name__ == "__main__":
    unittest.main()
