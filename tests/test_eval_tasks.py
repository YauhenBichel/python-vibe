import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finetune.python_vibe import all_pairs
from harness.eval_loop import score_generate, score_source
from harness.eval_tasks import Task, all_tasks


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
        seen: list[str] = []
        drafts = iter(
            [
                "```python\nprint('nope')\n```",
                "```python\n" + task.reference + "\n```",
            ]
        )

        def generate(prompt: str) -> str:
            seen.append(prompt)
            return next(drafts)

        score = score_generate(task, generate, repair=True)
        self.assertTrue(score.passed)
        self.assertTrue(score.repaired)
        self.assertEqual(score.samples, 1)
        self.assertEqual(score.hit, 1)
        self.assertTrue(
            any("stdout is wrong" in prompt for prompt in seen),
            seen,
        )

    def test_pass_at_k_keeps_first_hit(self) -> None:
        task = next(t for t in all_tasks() if t.id == "clamp")
        n = {"calls": 0}

        def generate(_prompt: str) -> str:
            n["calls"] += 1
            if n["calls"] < 3:
                return "```python\nprint('nope')\n```"
            return "```python\n" + task.reference + "\n```"

        score = score_generate(task, generate, samples=4)
        self.assertTrue(score.passed)
        self.assertEqual(score.hit, 3)
        self.assertEqual(score.samples, 3)
        self.assertEqual(n["calls"], 3)

    def test_pass_at_k_all_miss(self) -> None:
        task = next(t for t in all_tasks() if t.id == "clamp")
        n = {"calls": 0}

        def generate(_prompt: str) -> str:
            n["calls"] += 1
            return "```python\nprint('nope')\n```"

        score = score_generate(task, generate, samples=2)
        self.assertFalse(score.passed)
        self.assertEqual(score.hit, 0)
        self.assertEqual(score.samples, 2)
        self.assertEqual(n["calls"], 2)

    def test_missing_sys_import_is_fixed(self) -> None:
        task = Task(
            id="argv",
            prompt="print argv",
            reference="import sys\nprint(sys.argv[1])\n",
            argv=("hi",),
            expect_stdout="hi\n",
        )
        score = score_source(task, "print(sys.argv[1])\n")
        self.assertTrue(score.passed, score.stderr)

    def test_repair_skips_traceback_draft(self) -> None:
        task = next(t for t in all_tasks() if t.id == "clamp")
        drafts = iter(
            [
                "```python\nprint('nope')\n```",
                "```python\nTypeError: can only join an iterable\n```",
            ]
        )
        score = score_generate(task, lambda _prompt: next(drafts), repair=True)
        self.assertFalse(score.passed)
        self.assertTrue(score.repaired)
        self.assertEqual(score.reason, "no python block")


if __name__ == "__main__":
    unittest.main()
