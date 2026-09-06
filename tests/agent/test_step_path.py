"""A step must name the file its action was about.

`_carry_out` reads the path back out of `run_action`, so a successful
action records the file it touched. When the action *raises* — and
`apply_source` raises `ValueError` on a syntax error, which is the
commonest way a patch fails — it returned early and `last_path` still
held the previous step's file.

The step log then blamed a file the model never named. Diagnosing #173 I
read four consecutive steps as `pricing.py` and wrote that the model was
patching the implementation instead of a test. It was not: every draft
said `tests/test_apply_discount.py`. The log was wrong, and a wrong log
sends the next hour at the wrong file.

The repair prompt reads the same field, so it was naming the wrong file
too.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.agent.loop import Agent  # noqa: E402
from harness.agent.options import AgentOptions  # noqa: E402
from harness.agent.policy import LoopState  # noqa: E402


class _Run:
    def __init__(self, project: Path) -> None:
        self.options = AgentOptions(project=project, task="write tests")
        self.preamble = SimpleNamespace(target=None)
        self.writes: list[str] = []


class AFailedActionNamesItsOwnFileTest(unittest.TestCase):
    def _carry(self, turn_path: str, body: str, last: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pricing.py").write_text("x = 1\n", encoding="utf-8")
            (root / "tests").mkdir()
            agent = Agent(AgentOptions(project=root, task="write tests"))
            state = LoopState(task="write tests", project=root, last_path=last)
            turn = SimpleNamespace(
                action="patch", path=turn_path, find="", replace="",
                append=body, source="", argv=(), summary="", name="",
                query="", pattern="", scope="", number="", title="", body="",
            )
            agent._carry_out(turn, state, _Run(root))
            return state.last_path

    def test_a_syntax_error_still_names_the_patched_file(self) -> None:
        """The shape from #173: an indented method, appended."""
        landed = self._carry(
            "tests/test_apply_discount.py",
            "        def test_x(self) -> None:\n            pass\n    oops(\n",
            last="pricing.py",
        )
        self.assertEqual(landed, "tests/test_apply_discount.py")

    def test_a_successful_patch_still_names_its_file(self) -> None:
        landed = self._carry(
            "tests/test_pricing.py",
            "def helper() -> int:\n    return 1\n",
            last="pricing.py",
        )
        self.assertEqual(landed, "tests/test_pricing.py")

    def test_an_action_with_no_path_keeps_the_last_one(self) -> None:
        """`run` and `grep` name no file, so the previous one still
        describes where the run is working."""
        landed = self._carry("", "oops(\n", last="pricing.py")
        self.assertEqual(landed, "pricing.py")


if __name__ == "__main__":
    unittest.main()
