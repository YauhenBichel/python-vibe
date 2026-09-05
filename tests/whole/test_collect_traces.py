"""Gathering the turns that would otherwise be thrown away.

A run records beside the project it ran in, which is right for somebody
working on their own code and useless for gathering training data: the
benchmark and the eval build a project in a temporary directory and
delete it, so every turn they produce goes with it. Between them they
hold tasks nobody has to invent.
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))


def _script():
    spec = importlib.util.spec_from_file_location(
        "python_vibe_collect_traces",
        ROOT / "scripts" / "weights" / "collect_traces.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TheTasksItRunsTest(unittest.TestCase):
    def test_it_uses_the_benchmark_cases(self) -> None:
        jobs = _script().bench_tasks()
        self.assertGreaterEqual(len(jobs), 15)
        for key, task, files in jobs:
            with self.subTest(key=key):
                self.assertTrue(task.strip(), "a task with no words")
                self.assertTrue(files, "a task with no project to run in")

    def test_it_uses_the_held_out_eval_tasks(self) -> None:
        jobs = _script().eval_task_list()
        self.assertGreaterEqual(len(jobs), 15)
        for key, task, _files in jobs:
            with self.subTest(key=key):
                self.assertTrue(task.strip())

    def test_the_two_sets_are_different_tasks(self) -> None:
        """Repeating one task many times is volume, not variety."""
        build = _script()
        bench = {task for _k, task, _f in build.bench_tasks()}
        held_out = {task for _k, task, _f in build.eval_task_list()}
        self.assertEqual(bench & held_out, set())


class CountingWhatItWroteTest(unittest.TestCase):
    def test_an_absent_file_counts_as_nothing(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(build._line_count(Path(tmp) / "gone.jsonl"), 0)

    def test_it_counts_the_lines_that_are_there(self) -> None:
        build = _script()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "turns.jsonl"
            path.write_text(
                "".join(json.dumps({"user": str(n), "assistant": "x"}) + "\n"
                        for n in range(4)),
                encoding="utf-8",
            )
            self.assertEqual(build._line_count(path), 4)


class WhatItWritesIsUsableTest(unittest.TestCase):
    def test_the_builder_can_read_what_this_collects(self) -> None:
        """Two scripts, one format. The point of collecting is training."""
        collect = _script()
        spec = importlib.util.spec_from_file_location(
            "python_vibe_build_agent_data",
            ROOT / "scripts" / "weights" / "build_agent_data.py",
        )
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "turns.jsonl"
            path.write_text(
                json.dumps({"user": "Action: read", "assistant": "Action: done"}) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(collect._line_count(path), 1)
            self.assertEqual(build.load_turns(path), [("Action: read", "Action: done")])


if __name__ == "__main__":
    unittest.main()
