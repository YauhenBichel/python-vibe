import unittest

from harness.act.parse import AgentTurn
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

    def test_repeated_patch_is_not_guarded(self) -> None:
        guard = LoopGuard()
        turn = AgentTurn(action="patch", path="a.py")
        self.assertEqual(guard.check(turn), "")
        self.assertEqual(guard.check(turn), "")

    def test_none_turn(self) -> None:
        self.assertEqual(LoopGuard().check(None), "")


if __name__ == "__main__":
    unittest.main()
