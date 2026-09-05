import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from finetune.python_vibe import all_pairs
from harness.observe.eval_loop import score_generate, score_source
from harness.observe.eval_tasks import Task, all_tasks


class EvalTasksTest(unittest.TestCase):
    def test_eighteen_held_out(self) -> None:
        tasks = all_tasks()
        self.assertEqual(len(tasks), 18)
        self.assertEqual(len({t.id for t in tasks}), 18)

    def test_no_overlap_with_train_prompts(self) -> None:
        train = {user.casefold() for user, _ in all_pairs()}
        for task in all_tasks():
            self.assertNotIn(task.prompt.casefold(), train, task.id)

    def test_reference_passes_and_junk_fails(self) -> None:
        for task in all_tasks():
            with self.subTest(task=task.id):
                ok = score_source(task, task.reference)
                self.assertTrue(ok.passed, f"{task.id}: {ok.reason} {ok.stdout!r} {ok.stderr!r}")
                bad = score_source(task, "print('nope')\n")
                self.assertFalse(bad.passed, task.id)

    def test_timeout_is_a_fail(self) -> None:
        task = Task(
            id="hang",
            prompt="hang",
            reference="print(1)\n",
            expect_stdout="1\n",
            timeout=0.4,
        )
        score = score_source(task, "while True:\n    pass\n")
        self.assertFalse(score.passed)
        self.assertEqual(score.reason, "timeout")

    def test_generate_then_repair(self) -> None:
        task = next(t for t in all_tasks() if t.id == "clamp")
        drafts = iter(
            [
                "```python\nprint('nope')\n```",
                "```python\n" + task.reference + "\n```",
            ]
        )
        score = score_generate(task, lambda _prompt: next(drafts), repair=True)
        self.assertTrue(score.passed)
        self.assertTrue(score.repaired)


if __name__ == "__main__":
    unittest.main()
