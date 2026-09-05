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
        # The scripted model says it tidied the file and writes nothing.
        # That is the false finish, so the run must not call it a success.
        self.assertFalse(result.ok)
        self.assertIn("unfinished", result.summary)

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

    def test_a_failing_suite_is_sent_back_once(self) -> None:
        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state("add multiply(a, b) and a test", _project(tmp))
            state.wrote_something = True
            state.last_path = "src/app.py"
            first = next_prompt(state, self._run_turn(), "exit 1\nNameError: x")
            self.assertIn("failed when I ran it", first)
            self.assertIn("NameError: x", first)
            self.assertIn("Action: patch Path: src/app.py", first)
            second = next_prompt(state, self._run_turn(), "exit 1\nNameError: x")
            self.assertIn("repair still fails", second)

    def test_a_failing_suite_before_any_change_says_nothing(self) -> None:
        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state("add multiply(a, b) and a test", _project(tmp))
            self.assertEqual(next_prompt(state, self._run_turn(), "exit 1\nE"), "")

    def test_a_refused_run_is_not_a_repair(self) -> None:
        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state("add multiply(a, b) and a test", _project(tmp))
            state.wrote_something = True
            self.assertEqual(
                next_prompt(state, self._run_turn(), "refusing that argv"), ""
            )
            self.assertEqual(
                next_prompt(state, self._run_turn(), "no tests/ directory"), ""
            )

    def test_a_bugfix_write_asks_to_run_when_tests_exist(self) -> None:
        from types import SimpleNamespace

        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            project = _project(tmp)
            (project / "tests" / "test_app.py").write_text(
                "import unittest\nfrom src.app import compute_total\n\n"
                "class AppTest(unittest.TestCase):\n"
                "    def test_total(self) -> None:\n"
                "        self.assertEqual(compute_total([1]), 1)\n",
                encoding="utf-8",
            )
            state = self._state(
                "fix compute_total in src/app.py so it sums the rows", project
            )
            state.wrote_something = True
            state.last_path = "src/app.py"
            turn = SimpleNamespace(action="patch", path="src/app.py")
            got = next_prompt(state, turn, "patched src/app.py")
        self.assertIn("must be run", got)
        self.assertNotIn("write-tests", got)

    def test_an_add_without_a_test_still_asks_for_tests(self) -> None:
        from types import SimpleNamespace

        from harness.agent.policy import next_prompt

        with tempfile.TemporaryDirectory() as tmp:
            state = self._state("add multiply(a, b) and a test", _project(tmp))
            state.wrote_something = True
            state.last_path = "src/app.py"
            turn = SimpleNamespace(action="patch", path="src/app.py")
            got = next_prompt(state, turn, "patched src/app.py")
        self.assertIn("write-tests", got)

    def test_a_cli_app_write_names_pr_review_not_weekday(self) -> None:
        from types import SimpleNamespace

        from harness.agent.policy import next_prompt

        task = "design and develop a small cli app for reviewing github PRs"
        with tempfile.TemporaryDirectory() as tmp:
            from harness.act.autofix.scaffold import apply_package_scaffold

            root = Path(tmp)
            apply_package_scaffold(root, task)
            state = self._state(task, root)
            state.wrote_something = True
            state.last_path = "pkg/__init__.py"
            turn = SimpleNamespace(action="edit", path="pkg/__init__.py")
            got = next_prompt(state, turn, "wrote pkg/__init__.py")
        self.assertIn("pkg/pr_review.py", got)
        self.assertIn("urllib", got)
        self.assertNotIn("weekday_name", got)

    def test_a_failed_run_is_repaired_once(self) -> None:
        """Write a bad body; the harness runs the suite and sends the traceback."""
        prompts: list[str] = []
        remaining = [
            "Action: read\nPath: src/app.py",
            "Action: patch\nPath: src/app.py\nFind:     return 0\n"
            "Replace:     return 1\n",
            "Action: patch\nPath: src/app.py\nFind:     return 1\n"
            "Replace:     return sum(rows)\n",
            "Action: done\nSummary: compute_total now sums the rows",
        ]

        def generate(prompt: str) -> str:
            prompts.append(prompt)
            return remaining.pop(0) if remaining else "Action: done\nSummary: out"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "tests").mkdir()
            (root / "src" / "__init__.py").write_text("", encoding="utf-8")
            (root / "src" / "app.py").write_text(
                "def compute_total(rows: list[int]) -> int:\n    return 0\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_app.py").write_text(
                "import unittest\n\nfrom src.app import compute_total\n\n\n"
                "class AppTest(unittest.TestCase):\n"
                "    def test_total(self) -> None:\n"
                "        self.assertEqual(compute_total([1, 2]), 3)\n",
                encoding="utf-8",
            )
            options = AgentOptions(
                project=root,
                task="fix compute_total in src/app.py so it sums the rows",
                keep_no_record=True,
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                lambda *a, **k: ("scripted", generate),
            ):
                result = Agent(options).run()
            body = (root / "src" / "app.py").read_text(encoding="utf-8")
        self.assertTrue(result.ok, result.summary)
        self.assertIn("return sum(rows)", body)
        self.assertTrue(any("failed when I ran it" in p for p in prompts), prompts)


class LateQuestionTest(unittest.TestCase):
    """Once files are written, a clarifying question is too late.

    A live run wrote `total_lines` and a test under one reading of an
    ambiguous task, left the project's suite red, and only then asked
    which reading was meant. The question was reasonable; the timing
    made it useless, because the answer could no longer change what was
    on disk.
    """

    def test_asking_after_a_write_is_sent_back(self) -> None:
        asked = []
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp),
                task="add multiply and a unit test",
                on_question=lambda q: (asked.append(q.text), "either")[1],
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(
                    "Action: patch\nPath: src/app.py\nAppend:\n"
                    "def multiply(left: int, right: int) -> int:\n    return left * right\n",
                    "Action: ask\nQuery: which reading did you mean?",
                    "Action: run\nArgv: -m unittest discover -s tests -q",
                    "Action: done\nSummary: added multiply to src/app.py",
                ),
            ):
                result = Agent(options).run()
        self.assertEqual(asked, [], "the question should not reach the user")
        self.assertTrue(
            any(
                "too late to ask" in item or "Tests already passed" in item
                for item in result.refusals
            ),
            result.refusals,
        )

    def test_asking_before_any_write_still_reaches_the_user(self) -> None:
        """The rule is about timing, not about forbidding questions."""
        asked = []
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp),
                task="add multiply and a unit test",
                on_question=lambda q: (asked.append(q.text), "src/app.py")[1],
            )
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(
                    "Action: ask\nQuery: which module?",
                    "Action: patch\nPath: src/app.py\nAppend:\n"
                    "def multiply(left: int, right: int) -> int:\n    return left * right\n",
                    "Action: run\nArgv: -m unittest discover -s tests -q",
                    "Action: done\nSummary: added multiply to src/app.py",
                ),
            ):
                result = Agent(options).run()
        self.assertEqual(asked, ["which module?"])
        self.assertTrue(result.ok, result.refusals)


class ThinSummaryIsCappedTest(unittest.TestCase):
    """Sending a summary back for being thin must not cost the whole run.

    The check that a return-type answer says more than the type is worth
    having: the bare answer was `"int"`. Without a cap it was handed back
    every turn until the steps ran out, and a run that had the answer in
    hand reported failure.
    """

    def test_the_run_finishes_even_if_the_summary_never_improves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            options = AgentOptions(
                project=_project(tmp),
                task="what does compute_total return?",
                steps=8,
            )
            thin = 'Action: done\nSummary: "int"'
            with mock.patch(
                "harness.agent.loop.make_generate",
                _scripted(thin, thin, thin, thin, thin, thin),
            ):
                result = Agent(options).run()
        self.assertTrue(result.ok, result.refusals)
        self.assertLessEqual(
            sum(1 for item in result.refusals if "too thin" in item),
            2,
            result.refusals,
        )


if __name__ == "__main__":
    unittest.main()
