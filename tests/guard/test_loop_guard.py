from pathlib import Path
import unittest

from harness.act.parse import AgentTurn
from harness.agent.policy import LoopState, refuse_before
from harness.guard.loop_guard import LoopGuard


class LoopGuardTest(unittest.TestCase):
    def test_first_explore_passes(self) -> None:
        self.assertEqual(LoopGuard().check(AgentTurn(action="grep", query="total")), "")

    def test_same_grep_twice_is_refused(self) -> None:
        guard = LoopGuard()
        turn = AgentTurn(action="grep", query="total")
        self.assertEqual(guard.check(turn), "")
        blocked = guard.check(turn)
        self.assertIn("already ran that exact grep", blocked)
        self.assertIn("Action: read", blocked)

    def test_different_query_passes(self) -> None:
        guard = LoopGuard()
        guard.check(AgentTurn(action="grep", query="total"))
        self.assertEqual(guard.check(AgentTurn(action="grep", query="other")), "")

    def test_rerunning_tests_after_a_patch_is_progress(self) -> None:
        guard = LoopGuard()
        turn = AgentTurn(action="run", argv=("-m", "unittest"))
        self.assertEqual(guard.check(turn), "")
        self.assertEqual(guard.check(turn), "")

    def test_same_patch_body_is_refused_across_paths(self) -> None:
        guard = LoopGuard()
        first = AgentTurn(action="patch", path="a.py", append="value = 1")
        repeated = AgentTurn(action="patch", path="b.py", append="value = 1")
        self.assertEqual(guard.check(first), "")
        blocked = guard.check(repeated)
        self.assertIn("already proposed that exact patch body", blocked)
        self.assertIn("already applied or refused", blocked)

    def test_a_different_patch_body_passes(self) -> None:
        guard = LoopGuard()
        guard.check(AgentTurn(action="patch", path="a.py", append="value = 1"))
        self.assertEqual(
            guard.check(AgentTurn(action="patch", path="a.py", append="value = 2")),
            "",
        )

    def test_a_policy_refused_patch_is_still_remembered(self) -> None:
        state = LoopState(task="change app.py", project=Path("."), allow_writes=False)
        patch = AgentTurn(action="patch", path="app.py", append="value = 1")
        self.assertIn("read-only", refuse_before(state, patch).lower())
        self.assertIn("already proposed", refuse_before(state, patch))

    def test_none_turn(self) -> None:
        self.assertEqual(LoopGuard().check(None), "")


if __name__ == "__main__":
    unittest.main()
