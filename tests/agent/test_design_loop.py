"""Design loop: review → one-split → re-scan until clean."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from harness.agent.policy import LoopState, next_prompt, refuse_done
from harness.locate import prelude, refuse_question_write
from harness.scan.design import design_is_clean, render_design_review
from harness.skillkit.catalog import list_skills, pick_skills
from harness.skillkit.refuse_change import refuse_god_target
from harness.skillkit.refuse_finish import refuse_write_done
from harness.task import looks_like_design_loop


class _Turn:
    def __init__(self, action: str, path: str = "", summary: str = "") -> None:
        self.action = action
        self.path = path
        self.summary = summary


class DesignLoopTest(unittest.TestCase):
    def _dirty_tree(self) -> Path:
        root = Path(self._tmp)
        pkg = root / "pkg"
        pkg.mkdir()
        (pkg / "kitchen.py").write_text(
            "def one():\n    return 1\n\n"
            "def two():\n    return 2\n\n"
            "def three():\n    return 3\n\n"
            "def four():\n    return 4\n",
            encoding="utf-8",
        )
        (pkg / "__init__.py").write_text("def leftover():\n    return 1\n", encoding="utf-8")
        return root

    def setUp(self) -> None:
        self._ctx = tempfile.TemporaryDirectory()
        self._tmp = self._ctx.name

    def tearDown(self) -> None:
        self._ctx.cleanup()

    def test_prelude_asks_for_a_split_when_dirty(self) -> None:
        root = self._dirty_tree()
        text, _path = prelude(root, "review the project structure")
        self.assertIn("god module", text)
        self.assertIn("edit Path:", text)
        self.assertTrue(looks_like_design_loop("review the project structure"))

    def test_review_may_edit(self) -> None:
        self.assertEqual(
            refuse_question_write("review the project structure", "edit"),
            "",
        )

    def test_god_module_is_refused_before_the_draft_runs(self) -> None:
        root = self._dirty_tree()
        self.assertIn(
            "already has 4",
            refuse_god_target(
                "review the project structure", root, "edit", "pkg/kitchen.py"
            ),
        )
        self.assertEqual(
            refuse_god_target(
                "review the project structure", root, "edit", "pkg/prices.py"
            ),
            "",
        )

    def test_pick_design_skills(self) -> None:
        names = [s.name for s in pick_skills("refactor kitchen into concerns", list_skills())]
        self.assertIn("review-design", names)
        self.assertIn("refactor-split", names)
        self.assertIn("readable-layout", names)

    def test_refuse_done_while_dirty(self) -> None:
        root = self._dirty_tree()
        report = render_design_review(root)
        self.assertFalse(design_is_clean(report))
        state = LoopState(
            task="review the project structure",
            project=root,
            design_report=report,
        )
        blocked = refuse_done(state, _Turn("done", summary="looks ok"))
        self.assertIn("findings remain", blocked)

    def test_re_scan_after_a_split(self) -> None:
        root = self._dirty_tree()
        state = LoopState(
            task="review the project structure",
            project=root,
            design_report=render_design_review(root),
        )
        nudge = next_prompt(
            state,
            _Turn("edit", path="pkg/pricing.py"),
            "wrote pkg/pricing.py",
        )
        self.assertIn("design review", nudge)
        self.assertTrue(state.design_report)

    def test_write_tasks_need_a_run(self) -> None:
        self.assertIn("run", refuse_write_done("add a function multiply", False, wrote=True))
        self.assertIn("run", refuse_write_done("find a NameError and fix it", False, wrote=True))
        self.assertEqual(refuse_write_done("add a function multiply", True, wrote=True), "")
        self.assertEqual(refuse_write_done("add a function multiply", False, wrote=False), "")
        self.assertEqual(
            refuse_write_done("review the project structure", False, wrote=False),
            "",
        )


class LiveFixesTest(unittest.TestCase):
    def test_after_tests_pass_the_next_step_is_done(self) -> None:
        from harness.agent.policy import LoopState, next_prompt, refuse_before

        state = LoopState(
            task="find a NameError and fix it",
            project=Path("."),
            ran_tests=True,
            wrote_something=True,
        )
        self.assertIn(
            "done",
            next_prompt(state, _Turn("run"), "exit 0\n.").lower(),
        )
        self.assertIn(
            "already passed",
            refuse_before(state, _Turn("ask", summary="which?")).lower(),
        )


if __name__ == "__main__":
    unittest.main()
