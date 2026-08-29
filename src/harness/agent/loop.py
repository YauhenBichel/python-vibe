"""Run one task from start to finish.

    from harness import Agent, AgentOptions

    result = Agent(AgentOptions(project=Path("~/app"))).run("fix the NameError")

This class is responsible for the order of steps and nothing else. It asks
`harness.agent.prompt` what to send to the model, `harness.agent.policy`
whether a proposed action is allowed, and `harness.agent.dispatch` to carry
an allowed action out.
"""

from __future__ import annotations

from dataclasses import dataclass

from harness.act.autofix import apply_cover_test
from harness.act.parse import parse_turn_smart
from harness.act.tools import run_python
from harness.scan.names import undefined_in_file
from harness.agent.dispatch import ACTIONS, run_action
from harness.agent.options import AgentOptions, AgentResult, Step
from harness.agent.policy import LoopState, next_prompt, refuse_before, refuse_done
from harness.agent.prompt import Preamble, build_preamble
from harness.locate import named_file_review_summary
from harness.model.engine import make_generate
from harness.observe.trace_record import append_turn
from harness.scan.design import render_design_review
from harness.task import (
    looks_like_add_feature,
    looks_like_bugfix,
    looks_like_design_loop,
    looks_like_question,
    looks_like_ship,
    looks_unclear,
    named_project_file,
)


@dataclass(frozen=True)
class Question:
    """A question the agent needs answered before it can continue.

    Fields:
        text: the question.
        options: answers the agent considers likely. May be empty.
    """

    text: str
    options: tuple[str, ...] = ()

    def render(self) -> str:
        if not self.options:
            return self.text
        listed = "\n".join(f"  {i}. {opt}" for i, opt in enumerate(self.options, 1))
        return f"{self.text}\n{listed}"


def _question_from(turn) -> Question:
    text = (turn.query or turn.summary or "").strip() or "What should I do?"
    raw = turn.append or turn.replace or ""
    options = tuple(
        line.strip(" -*\t")
        for line in raw.splitlines()
        if line.strip(" -*\t")
    )
    return Question(text, options[:4])


class Agent:
    """Runs one task against one project."""

    def __init__(self, options: AgentOptions) -> None:
        self.options = options
        self.project = options.resolved_project()

    def preamble(self, task: str | None = None) -> Preamble:
        options = self.options if task is None else _with_task(self.options, task)
        return build_preamble(options)

    def run(self, task: str | None = None) -> AgentResult:
        options = self.options if task is None else _with_task(self.options, task)
        if not options.task.strip():
            raise ValueError("task required")
        pre = build_preamble(options)
        options.emit("preamble", pre.pre_text or "")

        # A task that names no file and no symbol cannot be started from.
        # The harness asks, rather than relying on the model to notice: a
        # small model reaches for `patch` long before it reaches for `ask`.
        opening = opening_question(options.task, pre)
        if opening is not None:
            answer = self._ask(opening, options)
            if answer is None:
                return AgentResult(
                    ok=False,
                    summary=opening.render(),
                    stopped="question",
                )
            options = _with_task(options, f"{options.task} ({answer})")
            pre = build_preamble(options)
            options.emit("preamble", f"user answered: {answer}")
        review = named_file_review_summary(self.project, options.task)
        if review:
            options.emit("result", review)
            return AgentResult(
                ok=True,
                summary=review,
                stopped="done",
            )
        writes: list[str] = []
        leftover_tests = ""
        if pre.autofix:
            writes.extend(_autofix_paths(pre.autofix))
            if not options.allow_writes:
                note = next(
                    (
                        line[2:]
                        for line in pre.autofix.splitlines()
                        if line.startswith("- ")
                    ),
                    "mechanical fix",
                )
                return AgentResult(
                    ok=True,
                    summary=f"Read-only: would {note}. Nothing written.",
                    stopped="done",
                    writes=(),
                )
            leftover_names = []
            if looks_like_bugfix(options.task):
                for rel in writes:
                    leftover_names.extend(
                        undefined_in_file(self.project / rel)
                    )
            verdict, test_out = _verify_mechanical(self.project)
            options.emit("result", test_out)
            if leftover_names:
                leftover_tests = (
                    f"undefined name {leftover_names[0]} after the "
                    "mechanical fix. The suite is not enough."
                )
                options.emit("result", leftover_tests)
            elif verdict in {"passed", "no suite"}:
                note = next(
                    (
                        line[2:]
                        for line in pre.autofix.splitlines()
                        if line.startswith("- ")
                    ),
                    "mechanical fix applied",
                )
                tail = (
                    "Tests passed."
                    if verdict == "passed"
                    else "This project has no tests to check it against."
                )
                return AgentResult(
                    ok=True,
                    summary=f"{note}. {tail}",
                    stopped="done",
                    writes=tuple(writes),
                )
            else:
                leftover_tests = test_out
        leftover_q = leftover_bind_question(options.task, self.project)
        if leftover_q is not None:
            answer = self._ask(leftover_q, options)
            if answer is None:
                return AgentResult(
                    ok=False,
                    summary=leftover_q.render(),
                    stopped="question",
                    writes=tuple(writes),
                )
            options = _with_task(options, f"{options.task} ({answer})")
            options.emit("preamble", f"user answered: {answer}")
        label, generate = make_generate(
            options.engine,
            options.max_tokens,
            model=options.model,
            system=pre.system or options.system,
        )
        options.emit("engine", f"{label}  project {self.project}  mode {pre.brief.kind}")
        state = LoopState(
            task=options.task,
            project=self.project,
            located_path=pre.located_path,
            located_signature=pre.located_signature,
            prelude_ran=bool(pre.pre_text),
            allow_writes=options.allow_writes,
            last_path=pre.located_path,
            instructions=_instruction_lines(pre),
            scope=options.scope,
            autofixed=bool(pre.autofix),
            wrote_something=bool(pre.autofix),
            design_report=(
                render_design_review(self.project, options.scope)
                if looks_like_design_loop(options.task)
                else ""
            ),
        )
        prompt = pre.prompt
        if leftover_tests:
            prompt = (
                f"{pre.prompt}\n\nHarness ran tests after the mechanical fix:\n"
                f"{leftover_tests}\n"
                "Action: patch the remaining failure, or Action: done if "
                "the task is already met."
            )
        steps: list[Step] = []

        for number in range(1, options.steps + 1):
            draft = generate(prompt)
            _remember(generate, prompt, draft)
            options.emit("draft", f"--- step {number} ---\n{draft}")
            turn = parse_turn_smart(
                draft,
                question=looks_like_question(options.task),
                ship=looks_like_ship(options.task),
            )
            if options.record:
                append_turn(
                    options.record.expanduser(),
                    {
                        "user": prompt,
                        "assistant": draft,
                        "action": turn.action if turn else "",
                    },
                )
            if turn is None:
                steps.append(Step(number, "", refused="unparsed", draft=draft))
                prompt = f"Could not parse. One Action: {ACTIONS}"
                continue

            if turn.action == "done":
                blocked = refuse_done(state, turn)
                if blocked:
                    steps.append(Step(number, "done", refused=blocked, draft=draft))
                    options.emit("refused", blocked)
                    prompt = blocked
                    continue
                steps.append(Step(number, "done", result=turn.summary, draft=draft))
                return AgentResult(
                    ok=True,
                    summary=turn.summary or "done",
                    stopped="done",
                    steps=tuple(steps),
                    writes=tuple(writes),
                )

            # Policy first, ask included: the cap on repeated questions
            # lives there, so it has to run before the question is put.
            blocked = refuse_before(state, turn)
            if blocked:
                steps.append(
                    Step(number, turn.action, turn.path, refused=blocked, draft=draft)
                )
                options.emit("refused", blocked)
                prompt = blocked
                continue

            if turn.action == "ask":
                question = _question_from(turn)
                state.questions_asked += 1
                answer = self._ask(question, options)
                if answer is None:
                    steps.append(
                        Step(number, "ask", result=question.render(), draft=draft)
                    )
                    return AgentResult(
                        ok=False,
                        summary=question.render(),
                        stopped="question",
                        steps=tuple(steps),
                        writes=tuple(writes),
                    )
                steps.append(Step(number, "ask", result=answer, draft=draft))
                prompt = f"The user answered: {answer}\n\nNext Action:"
                continue

            try:
                result, state.last_path = run_action(
                    self.project,
                    turn,
                    state.last_path,
                    options.scope,
                    pre.target,
                    task=options.task,
                )
            except (ValueError, OSError) as exc:
                result = str(exc)
            if turn.action == "run" and result.startswith("exit 0"):
                state.ran_tests = True
            if result.startswith(("patched", "wrote")):
                writes.append(turn.path or state.last_path)
                state.wrote_something = True
                cover = _cover_after_add(
                    self.project, options.task, turn.path or state.last_path
                )
                if cover:
                    for rel in _autofix_paths(f"- {cover}"):
                        if rel not in writes:
                            writes.append(rel)
                    result = f"{result}\n{cover}"
            options.emit("result", result)
            steps.append(
                Step(number, turn.action, state.last_path, result=result, draft=draft)
            )
            nudge = next_prompt(state, turn, result, pre.target)
            prompt = (
                f"Tool result:\n{result}\n\n{nudge}"
                if nudge
                else f"Tool result:\n{result}\n\nNext Action:"
            )

        return AgentResult(
            ok=False,
            summary=f"stopped after {options.steps} steps",
            stopped="steps",
            steps=tuple(steps),
            writes=tuple(writes),
        )

    def _ask(self, question: Question, options: AgentOptions) -> str | None:
        """None means nobody is there to answer — the caller decides."""
        handler = getattr(options, "on_question", None)
        if handler is None:
            return None
        return handler(question)


def _cover_after_add(project, task: str, path: str) -> str:
    """Add the AAA test once the new function exists. Empty if not this job."""
    if not looks_like_add_feature(task):
        return ""
    if "test" in (path or "").replace("\\", "/").lower():
        return ""
    return apply_cover_test(project, task, write=True)


def _autofix_paths(note: str) -> list[str]:
    """Paths named in mechanical-fix notes, in the order they were written."""
    found: list[str] = []
    for line in note.splitlines():
        if not line.startswith("- ") or " in " not in line:
            continue
        tail = line.rsplit(" in ", 1)[-1].strip()
        if tail.endswith(".py") and tail not in found:
            found.append(tail)
    return found


def _verify_mechanical(project) -> tuple[str, str]:
    """Run the project suite after a mechanical fix. No model.

    Returns "passed", "failed", or "no suite". A project with no tests has
    not failed anything, and saying so keeps the loop from asking the model
    to repair a failure that does not exist.
    """
    result = run_python(project, ("-m", "unittest", "discover", "-s", "tests", "-q"))
    if result.startswith("exit 0"):
        return "passed", result
    if "no tests/ directory" in result:
        return "no suite", result
    return "failed", result


def leftover_bind_question(task: str, project) -> Question | None:
    """Ask when a named file holds a typo the harness must not guess at.

    `stauts` inside `def status` reads as a misspelling of `status`, and
    `status` is the method's own name, which is not in scope in its body.
    Binding it writes `return status`, still a NameError, in a tenth of a
    second and reports success. Sending it to the model instead spent
    twenty steps and left `return stauts` untouched. A person has to say
    what was meant.

    Only a name that looks like a typo counts. Any other undefined name
    is work the model can do: a missing import, or something the task is
    asking to be written. Asking about those would stop a run that had
    every chance of finishing.
    """
    from pathlib import Path

    from harness.act.autofix import _is_typo, typo_pairs

    if not looks_like_bugfix(task):
        return None
    named = named_project_file(task, project)
    if not named:
        return None
    path = Path(project) / named
    leftover = undefined_in_file(path)
    if not leftover:
        return None
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if typo_pairs(source):
        return None  # a unique bind exists, so the mechanical pass has it
    known = _names_in_file(source)
    for bad in leftover:
        near = sorted(name for name in known if _is_typo(bad, name))
        if near:
            shown = ", ".join(f"`{name}`" for name in near[:3])
            return Question(
                f"`{bad}` in {named} looks like {shown}, but none of those "
                "is in scope where it is used. What did you mean?",
            )
    return None


def _names_in_file(source: str) -> set[str]:
    """Every name the file defines, wherever it defines it."""
    import ast

    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            found.add(node.id)
        elif isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            found.add(node.name)
            for arg in (
                *node.args.args,
                *node.args.posonlyargs,
                *node.args.kwonlyargs,
            ) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else ():
                found.add(arg.arg)
    return found


def opening_question(task: str, pre) -> Question | None:
    """Return a question to put before the run starts, or None to proceed.

    Only returned when the task names nothing the agent can search for and
    the harness did not find a file on its own.
    """
    if pre.located_path or not looks_unclear(task):
        return None
    options = tuple(
        item for item in (pre.target.module, pre.target.test) if item
    )
    return Question(
        f'"{task.strip()}" does not name a file or a function. '
        "Which file should I work on?",
        options,
    )


def _instruction_lines(pre) -> tuple[str, ...]:
    """Every line the model was handed, so an echo of any of them is caught.

    The skills were checked but the system prompt was not, and its examples
    are handed over on every single turn. Asked what a function returns, an
    8B answered with the system prompt's own example line: "one short
    question, when the task could mean two different things".
    """
    lines: list[str] = []
    sources = [skill.body for skill in pre.skills]
    if getattr(pre, "system", ""):
        sources.append(pre.system)
    for body in sources:
        lines.extend(
            line.strip()
            for line in body.splitlines()
            if len(line.strip()) >= 12 and not line.strip().startswith("Action:")
        )
    return tuple(lines)


def _with_task(options: AgentOptions, task: str) -> AgentOptions:
    from dataclasses import replace

    return replace(options, task=task)


def _remember(generate, prompt: str, draft: str) -> None:
    history = getattr(generate, "history", None)
    if history is None:
        return
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": draft})
