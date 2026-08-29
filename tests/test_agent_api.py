"""The public surface: options, the loop's sequencing, and read-only mode.

No model. `Agent.run` is driven with a scripted generator, so what is under
test is the harness's decisions, not llama's.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from harness import Agent, AgentOptions
from harness.agent.loop import Question, _question_from
from harness.act.parse import parse_turn

MODULE = "def compute_total(rows: list[int]) -> int:\n    return sum(rows)\n"
TEST = (
    "import unittest\n\n\nclass AppTest(unittest.TestCase):\n"
    "    def test_total(self) -> None:\n        self.assertEqual(1, 1)\n"
)


def _project(tmp: str) -> Path:
    root = Path(tmp)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "app.py").write_text(MODULE, encoding="utf-8")
    (root / "tests" / "test_app.py").write_text(TEST, encoding="utf-8")
    return root


def _scripted(*drafts: str):
    """Stand in for the model: hand back these drafts in order."""
    remaining = list(drafts)

    def generate(_prompt: str) -> str:
        return remaining.pop(0) if remaining else "Action: done\nSummary: out of drafts"

    return lambda *a, **k: ("scripted", generate)


class OptionsTest(unittest.TestCase):
    def test_missing_project_is_a_clear_error(self) -> None:
        options = AgentOptions(project=Path("/no/such/place"), task="x")
        with self.assertRaises(ValueError):
            options.resolved_project()

    def test_writes_are_on_by_default_for_a_person(self) -> None:
        self.assertTrue(AgentOptions(project=Path(".")).allow_writes)


class LoopTest(unittest.TestCase):
    def test_done_returns_the_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            options = AgentOptions(project=project, task="add multiply(a, b)")
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(
                    "Action: patch\nPath: src/app.py\nAppend:\n"
                    "def multiply(a: int, b: int) -> int:\n    return a * b\n",
                    "Action: run\nArgv: -m unittest discover -s tests -q",
                    "Action: done\nSummary: added multiply",
                ),
            ):
                result = Agent(options).run()
        self.assertTrue(result.ok, result.refusals)
        self.assertEqual(result.stopped, "done")
        self.assertIn("multiply", result.summary)

    def test_a_patch_is_recorded_as_a_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            draft = (
                "Action: patch\nPath: src/app.py\nAppend:\n"
                "def multiply(a: int, b: int) -> int:\n    return a * b\n"
            )
            options = AgentOptions(project=project, task="add multiply(a, b)")
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(draft, "Action: done\nSummary: done"),
            ):
                result = Agent(options).run()
            body = (project / "src" / "app.py").read_text(encoding="utf-8")
        self.assertIn("src/app.py", result.writes)
        self.assertIn("def multiply", body)

    def test_read_only_refuses_the_patch_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            before = (project / "src" / "app.py").read_text(encoding="utf-8")
            draft = (
                "Action: patch\nPath: src/app.py\nAppend:\n"
                "def multiply(a: int, b: int) -> int:\n    return a * b\n"
            )
            options = AgentOptions(
                project=project, task="add multiply(a, b)", allow_writes=False
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(draft, "Action: done\nSummary: would add multiply"),
            ):
                result = Agent(options).run()
            after = (project / "src" / "app.py").read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertTrue(any("read-only" in r for r in result.refusals))

    def test_read_only_says_so_in_the_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp), task="add multiply", allow_writes=False
            )
            self.assertIn("read-only", Agent(options).preamble().prompt)

    def test_step_budget_stops_the_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp), task="add multiply(a, b)", steps=3
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted("Action: grep\nQuery: a", "Action: grep\nQuery: b",
                          "Action: grep\nQuery: c"),
            ):
                result = Agent(options).run()
        self.assertFalse(result.ok)
        self.assertEqual(result.stopped, "steps")
        self.assertEqual(len(result.steps), 3)

    def test_an_unparsable_draft_is_a_step_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp),
                task="what does compute_total return?",
                steps=3,
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(
                    "I think I should look around.",
                    "Action: done\nSummary: compute_total returns int",
                ),
            ):
                result = Agent(options).run()
        self.assertEqual(result.steps[0].refused, "unparsed")
        self.assertTrue(result.ok, result.refusals)

    def test_empty_task_is_refused_before_any_model_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                Agent(AgentOptions(project=_project(tmp), task="  ")).run()


class AskTest(unittest.TestCase):
    def test_a_question_reaches_the_handler_and_the_answer_goes_back(self) -> None:
        seen = []

        def answer(question: Question) -> str:
            seen.append(question.text)
            return "the second one"

        with tempfile.TemporaryDirectory() as tmp:
            # A change task: asking is allowed, because the harness has not
            # already found the answer the way it does for a question.
            options = AgentOptions(
                project=_project(tmp),
                task="add multiply(a, b) and a unit test",
                on_question=answer,
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(
                    "Action: ask\nQuery: which module?\nAppend:\n- src/app.py\n- other.py",
                    "Action: patch\nPath: src/app.py\nAppend:\n"
                    "def multiply(a: int, b: int) -> int:\n    return a * b\n",
                    "Action: run\nArgv: -m unittest discover -s tests -q",
                    "Action: done\nSummary: added multiply",
                ),
            ):
                result = Agent(options).run()
        self.assertEqual(seen, ["which module?"])
        self.assertTrue(result.ok, result.refusals)

    def test_a_question_the_harness_already_answered_is_not_asked_about(self) -> None:
        """If the symbol was located, stalling to ask the user is wrong."""
        asked = []

        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp),
                task="what does compute_total return?",
                on_question=lambda q: (asked.append(q.text), "x")[1],
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(
                    "Action: ask\nQuery: which module?",
                    "Action: done\nSummary: compute_total returns int",
                ),
            ):
                result = Agent(options).run()
        self.assertEqual(asked, [])
        self.assertTrue(any("already located" in r for r in result.refusals))
        self.assertTrue(result.ok, result.refusals)

    def test_with_nobody_to_answer_the_loop_hands_the_question_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(project=_project(tmp), task="add multiply")
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted("Action: ask\nQuery: which module?"),
            ):
                result = Agent(options).run()
        self.assertEqual(result.stopped, "question")
        self.assertFalse(result.ok)
        self.assertIn("which module?", result.summary)

    def test_repeated_asking_is_capped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp),
                task="add multiply",
                steps=5,
                on_question=lambda q: "either",
            )
            ask = "Action: ask\nQuery: which module?"
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(ask, ask, ask, "Action: done\nSummary: chose one"),
            ):
                result = Agent(options).run()
        self.assertTrue(any("already asked" in r for r in result.refusals))

    def test_options_are_parsed_off_the_turn(self) -> None:
        turn = parse_turn("Action: ask\nQuery: which one?\nAppend:\n- alpha\n- beta")
        question = _question_from(turn)
        self.assertEqual(question.text, "which one?")
        self.assertEqual(question.options, ("alpha", "beta"))
        self.assertIn("1. alpha", question.render())


class EchoedSummaryTest(unittest.TestCase):
    """An 8B pastes the skill line back. That is not an answer."""

    SKILL = ("quote the -> type from the def line (example: tuple[str, int])",)

    def test_verbatim_echo_is_refused(self) -> None:
        from harness.agent.policy import refuse_echoed_summary

        self.assertTrue(refuse_echoed_summary(self.SKILL[0], self.SKILL))

    def test_a_real_answer_passes(self) -> None:
        from harness.agent.policy import refuse_echoed_summary

        self.assertEqual(
            refuse_echoed_summary("compute_total returns int, the sum of rows", self.SKILL),
            "",
        )

    def test_a_short_summary_is_not_judged(self) -> None:
        from harness.agent.policy import refuse_echoed_summary

        self.assertEqual(refuse_echoed_summary("done", self.SKILL), "")

    def test_no_instructions_means_nothing_to_echo(self) -> None:
        from harness.agent.policy import refuse_echoed_summary

        self.assertEqual(refuse_echoed_summary("anything at all here", ()), "")


class SystemPromptTest(unittest.TestCase):
    """The system prompt is a template, not a set of literal paths."""

    def test_no_fixture_path_survives_into_the_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            options = AgentOptions(project=project, task="add multiply(a, b)")
            pre = Agent(options).preamble()
        self.assertNotIn("pkg/mathy.py", pre.system)
        self.assertIn("Path: src/app.py", pre.system)

    def test_no_placeholder_is_left_unfilled(self) -> None:
        import re

        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(project=_project(tmp), task="add multiply(a, b)")
            pre = Agent(options).preamble()
        self.assertEqual(re.findall(r"\{\{\w+\}\}", pre.system), [])

    def test_every_path_in_the_system_prompt_is_real(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            pre = Agent(AgentOptions(project=project, task="add multiply")).preamble()
            for line in pre.system.splitlines():
                if line.startswith("Path:"):
                    rel = line.split(":", 1)[1].strip()
                    self.assertTrue(
                        (project / rel).is_file(), f"system prompt names {rel}"
                    )


class OpeningQuestionTest(unittest.TestCase):
    """A task naming nothing is asked about before the model is called."""

    def test_a_vague_task_is_asked_about_first(self) -> None:
        asked = []

        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp),
                task="clean this up",
                on_question=lambda q: (asked.append(q.text), "src/app.py")[1],
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted("Action: done\nSummary: tidied src/app.py"),
            ):
                result = Agent(options).run()
        self.assertEqual(len(asked), 1)
        self.assertIn("does not name a file", asked[0])
        self.assertTrue(result.ok)

    def test_a_clear_task_is_not_asked_about(self) -> None:
        asked = []

        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp),
                task="add multiply(a, b) and a test",
                on_question=lambda q: (asked.append(q.text), "x")[1],
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted("Action: done\nSummary: added multiply"),
            ):
                Agent(options).run()
        self.assertEqual(asked, [])

    def test_with_nobody_to_answer_the_run_stops_before_the_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(project=_project(tmp), task="clean this up")
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted("Action: patch\nPath: src/app.py\nAppend:\nx = 1\n"),
            ):
                result = Agent(options).run()
        self.assertEqual(result.stopped, "question")
        self.assertEqual(result.steps, ())
        self.assertEqual(result.writes, ())


class TestsPassedTest(unittest.TestCase):
    """Passing tests end the task only when the task changed something."""

    def _state(self, task: str, project):
        from harness.agent.policy import LoopState

        return LoopState(task=task, project=project)

    def _run_turn(self):
        from types import SimpleNamespace

        return SimpleNamespace(action="run", path="")

    def test_a_green_suite_before_any_change_says_nothing(self) -> None:
        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state("add multiply(a, b) and a test", _project(tmp))
            self.assertEqual(next_prompt(state, self._run_turn(), "exit 0\nOK"), "")

    def test_a_green_suite_after_a_change_ends_the_task(self) -> None:
        """Only once the function the task asked for actually exists.

        A green suite is not proof on its own: the oracle checks that the
        named function is in the project, because the existing tests very
        often do not call the new one.
        """
        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            app = project / "src" / "app.py"
            app.write_text(
                app.read_text(encoding="utf-8")
                + "\n\ndef multiply(a: int, b: int) -> int:\n    return a * b\n",
                encoding="utf-8",
            )
            state = self._state("add multiply(a, b) and a test", project)
            state.wrote_something = True
            self.assertIn(
                "Action: done", next_prompt(state, self._run_turn(), "exit 0\nOK")
            )

    def test_a_green_suite_is_not_done_if_the_function_is_missing(self) -> None:
        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state("add multiply(a, b) and a test", _project(tmp))
            state.wrote_something = True
            got = next_prompt(state, self._run_turn(), "exit 0\nOK")
        self.assertIn("multiply is not in the project", got)

    def test_a_failing_suite_never_ends_the_task(self) -> None:
        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state("add multiply(a, b) and a test", _project(tmp))
            state.wrote_something = True
            self.assertEqual(next_prompt(state, self._run_turn(), "exit 1\nE"), "")


if __name__ == "__main__":
    unittest.main()
