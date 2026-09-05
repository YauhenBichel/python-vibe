"""The everyday-ready remasure must show what the 8B did.

Four live runs stored only stopped + writes. After #238 that was
[] × 3 and no way to tell patch from refused grep from empty done.
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _script():
    spec = importlib.util.spec_from_file_location(
        "python_vibe_eval_everyday_bar",
        ROOT / "scripts" / "measure" / "eval_everyday_bar.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EverydayBarTurnsTest(unittest.TestCase):
    def test_turns_name_action_path_and_refusal(self) -> None:
        script = _script()
        result = SimpleNamespace(
            steps=(
                SimpleNamespace(
                    number=1, action="grep", path="", refused="Do not grep."
                ),
                SimpleNamespace(
                    number=2, action="patch", path="pkg/util_stats.py", refused=""
                ),
            )
        )
        got = script._turns(result)
        self.assertEqual(
            got,
            [
                {
                    "n": 1,
                    "action": "grep",
                    "path": "",
                    "refused": "Do not grep.",
                },
                {
                    "n": 2,
                    "action": "patch",
                    "path": "pkg/util_stats.py",
                    "refused": "",
                },
            ],
        )

    def test_turns_trim_a_long_refusal(self) -> None:
        script = _script()
        result = SimpleNamespace(
            steps=(
                SimpleNamespace(
                    number=1, action="read", path="pkg/util_stats.py", refused="x" * 400
                ),
            )
        )
        got = script._turns(result)
        self.assertEqual(len(got[0]["refused"]), 200)

    def test_compiler_only_write_does_not_count(self) -> None:
        script = _script()
        self.assertFalse(script._model_fix_ok(True, []))
        self.assertFalse(script._model_fix_ok(False, [{"n": 1}]))
        self.assertTrue(script._model_fix_ok(True, [{"n": 1, "action": "patch"}]))

    def test_live_cell_is_clip_not_the_retired_zero_return(self) -> None:
        script = _script()
        self.assertEqual(script.FIXTURE.name, "everyday_live")
        self.assertIn("clip", script.TASK)


if __name__ == "__main__":
    unittest.main()
