import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.act.code import apply_source, extract_python, read_project_file, resolve_project_file, write_and_run
from harness.scan.project_scan import list_small_py_files
from harness.observe.report_md import render_markdown


class ExtractPythonTest(unittest.TestCase):
    def test_fenced_block(self) -> None:
        text = "Note.\n\n```python\nprint(1)\n```\n"
        self.assertEqual(extract_python(text), "print(1)")

    def test_longest_block_wins(self) -> None:
        text = "```python\nx=1\n```\n```python\nprint(2)\nprint(3)\n```"
        self.assertIn("print(2)", extract_python(text) or "")

    def test_bare_import(self) -> None:
        self.assertEqual(extract_python("import json\nprint(1)"), "import json\nprint(1)")

    def test_run_print(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "_test_run.py"
            result = write_and_run("print('ok')", dest)
        self.assertEqual(result.code, 0)
        self.assertEqual(result.stdout.strip(), "ok")

    def test_run_reads_stdin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "_test_stdin.py"
            result = write_and_run(
                "import sys\nprint(sys.argv[1] + sys.stdin.read(), end='')\n",
                dest,
                ["hi"],
                stdin=" there",
            )
        self.assertEqual(result.code, 0)
        self.assertEqual(result.stdout, "hi there")

    def test_resolve_stays_in_project(self) -> None:
        root = Path(__file__).resolve().parents[2]
        path = resolve_project_file(root, "src/harness/act/code.py")
        self.assertTrue(path.is_file())
        with self.assertRaises(ValueError):
            resolve_project_file(root, "../other-repo/README.md")

    def test_report_md_counts_no_issues(self) -> None:
        text = render_markdown(
            [
                {"file": "a.py", "bytes": 200, "review": "no issues", "applied": False},
                {"file": "b.py", "bytes": 300, "review": "NameError in main", "applied": False},
            ],
            project="/tmp/app",
        )
        self.assertIn("Said no issues: **1**", text)
        self.assertIn("`a.py`", text)
        self.assertIn("NameError", text)

    def test_scan_skips_venv_and_respects_limit(self) -> None:
        root = Path(__file__).resolve().parents[2]
        files = list_small_py_files(root, limit=5, max_bytes=4000)
        self.assertLessEqual(len(files), 5)
        self.assertTrue(all(".venv" not in p.parts for p in files))

    def test_apply_creates_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "tests" / "test_new.py"
            apply_source(dest, "def test_ok():\n    assert True\n", original="")
            self.assertTrue(dest.is_file())

    def test_read_keeps_a_tail_when_truncated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "long.py"
            dest.write_text("HEAD\n" + ("x\n" * 4000) + "return tota\n", encoding="utf-8")
            shown = read_project_file(dest, limit=200)
            self.assertIn("HEAD", shown)
            self.assertIn("return tota", shown)
            self.assertIn("truncated", shown)

    def test_read_keeps_a_small_file_whole(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "listen.py"
            body = (
                "HOST = os.environ.get('HOST', '127.0.0.1')\n"
                "def listen_addr(argv=None) -> tuple[str, int]:\n"
                "    return HOST, 8080\n"
            ) * 80
            dest.write_text(body, encoding="utf-8")
            self.assertGreater(len(body), 3500)
            self.assertLess(len(body), 12_000)
            shown = read_project_file(dest)
            self.assertNotIn("truncated", shown)
            self.assertIn("HOST", shown)
            self.assertIn("listen_addr", shown)

    def test_apply_refuses_syntax_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "ok.py"
            good = "def add(left: int, right: int) -> int:\n    return left + right\n"
            dest.write_text(good, encoding="utf-8")
            broken = "def multiply(a: int, b: int) -> int:: int, right: int) -> int:\n    return a * b\n"
            with self.assertRaises(ValueError) as ctx:
                apply_source(dest, broken, original=good)
            self.assertIn("syntax error", str(ctx.exception).lower())
            self.assertEqual(dest.read_text(encoding="utf-8"), good)

    def test_apply_refuses_tiny_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "_apply.py"
            dest.write_text("x = 1\n" * 20, encoding="utf-8")
            with self.assertRaises(ValueError):
                apply_source(dest, "x=1\n", original=dest.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
