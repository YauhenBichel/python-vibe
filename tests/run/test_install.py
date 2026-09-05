"""scripts/run/install.py — dry-run planning only. No pip. No venv."""

from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INSTALL = ROOT / "scripts" / "run" / "install.py"


def _load():
    spec = importlib.util.spec_from_file_location("pv_install", INSTALL)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {INSTALL}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class InstallScriptTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load()

    def test_repo_root_is_this_checkout(self) -> None:
        self.assertEqual(self.mod.repo_root(), ROOT)
        self.assertTrue((self.mod.repo_root() / "pyproject.toml").is_file())

    def test_a_folder_without_pyproject_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as raised:
                self.mod.repo_root(Path(tmp))
        self.assertIn("not a python-vibe checkout", str(raised.exception))

    def test_a_foreign_pyproject_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "pyproject.toml").write_text(
                'name = "other"\n', encoding="utf-8"
            )
            with self.assertRaises(SystemExit) as raised:
                self.mod.repo_root(Path(tmp))
        self.assertIn("not a python-vibe checkout", str(raised.exception))

    def test_old_python_is_refused(self) -> None:
        self.assertIn("3.11", self.mod.require_python((3, 10)))
        self.assertEqual(self.mod.require_python((3, 11)), "")
        self.assertEqual(self.mod.require_python((3, 14)), "")

    def test_pip_spec_stays_stdlib_until_asked(self) -> None:
        self.assertEqual(self.mod.pip_spec(), ["-e", "."])
        self.assertEqual(self.mod.pip_spec(train=True), ["-e", ".[train]"])
        self.assertEqual(self.mod.pip_spec(hub=True), ["-e", ".[hub]"])
        self.assertEqual(
            self.mod.pip_spec(train=True, hub=True),
            ["-e", ".[train,hub]"],
        )

    def test_console_script_follows_the_platform(self) -> None:
        posix = Path("/tmp/.venv/bin/python")
        win = Path("app") / ".venv" / "Scripts" / "python.exe"
        self.assertEqual(
            self.mod.console_script(posix, windows=False),
            Path("/tmp/.venv/bin/python-vibe"),
        )
        got = self.mod.console_script(win, windows=True)
        self.assertEqual(got.name, "python-vibe.exe")
        self.assertEqual(got.parent.name, "Scripts")

    def test_dry_run_prints_pip_and_does_not_install(self) -> None:
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = self.mod.main(["--dry-run"])
        finally:
            sys.stdout = old
        text = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("-m pip install", text)
        self.assertIn("-e .", text)
        self.assertIn("would install", text)
        self.assertIn("python-vibe", text)

    def test_the_file_is_not_a_curl_pipe(self) -> None:
        text = INSTALL.read_text(encoding="utf-8")
        self.assertNotIn("curl |", text)
        self.assertIn("Do not pipe a download", text)

    def test_activate_hint_is_relative(self) -> None:
        """An absolute hint is a home path. Print `.venv`, not /Users/…."""
        posix = self.mod.activate_hint(Path("/Users/you/app/.venv"), windows=False)
        win = self.mod.activate_hint(Path(r"C:\app\.venv"), windows=True)
        self.assertEqual(posix, "source .venv/bin/activate")
        self.assertEqual(win, r".venv\Scripts\Activate.ps1")
        self.assertNotIn("/Users/", posix)
        self.assertNotIn("C:\\", win)

    def test_next_steps_name_activate_and_the_demo(self) -> None:
        text = self.mod.next_steps(system=False, already_in_venv=False, windows=False)
        self.assertIn("source .venv/bin/activate", text)
        self.assertIn("every new terminal", text)
        self.assertIn("command not found", text)
        self.assertIn("cd demo/orders", text)
        self.assertIn("python-vibe brief", text)
        self.assertNotIn("/Users/", text)

    def test_start_page_names_the_script(self) -> None:
        start = (ROOT / "docs" / "start.md").read_text(encoding="utf-8")
        self.assertIn("scripts/run/install.py", start)
        self.assertIn("source .venv/bin/activate", start)
        self.assertIn("demo/orders", start)
        self.assertIn("command not found", start)
        self.assertNotIn("curl", start)


if __name__ == "__main__":
    unittest.main()
