"""Score one draft against a held-out task. No model. No network."""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

from harness.act.code import RunResult, extract_python, write_and_run
from harness.guard.fallbacks import PYTHON_VIBE_FALLBACK
from harness.guard.python_vibe import PythonVibeGuard
from harness.guard.run import complete
from harness.guard.types import Outcome
from harness.observe.eval_tasks import REPAIR_PREFIX, RUN_PREFIX, Task

GenerateFn = Callable[[str], str]


@dataclass(frozen=True)
class Score:
    task_id: str
    passed: bool
    repaired: bool
    reason: str
    stdout: str
    stderr: str
    exit_code: int
    fallback: bool


def stdout_matches(expect: str, got: str) -> bool:
    return got.rstrip("\n") == expect.rstrip("\n")


def _remember(generate: GenerateFn, prompt: str, draft: str) -> None:
    memory = getattr(generate, "memory", None)
    if memory is None:
        return
    memory.remember(prompt, draft)


def _reset(generate: GenerateFn) -> None:
    memory = getattr(generate, "memory", None)
    if memory is not None:
        memory.clear()
        return
    history = getattr(generate, "history", None)
    if history is not None:
        history.clear()


def run_source(task: Task, source: str, dest: Path) -> tuple[bool, RunResult]:
    work = dest.parent
    for rel, content in task.files:
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    try:
        result = write_and_run(
            source,
            dest,
            list(task.argv),
            cwd=work,
            timeout=task.timeout,
            stdin=task.stdin or None,
        )
    except subprocess.TimeoutExpired as exc:
        result = RunResult(
            124,
            (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            (exc.stderr or "") if isinstance(exc.stderr, str) else "timed out",
        )
    ok = result.code == 0 and stdout_matches(task.expect_stdout, result.stdout)
    return ok, result


def score_source(task: Task, source: str) -> Score:
    if not source.strip():
        return Score(task.id, False, False, "empty source", "", "", 1, False)
    with tempfile.TemporaryDirectory(prefix=f"pv-eval-{task.id}-") as tmp:
        dest = Path(tmp) / "task.py"
        ok, result = run_source(task, source, dest)
    return Score(
        task.id,
        ok,
        False,
        (
            "pass"
            if ok
            else "timeout"
            if result.code == 124
            else "wrong output"
            if result.code == 0
            else "nonzero exit"
        ),
        result.stdout,
        result.stderr,
        result.code,
        False,
    )


def _draft_source(outcome: Outcome) -> tuple[str | None, Score | None]:
    if outcome.fallback or not outcome.output:
        return None, Score(
            "",
            False,
            False,
            "guard fallback" if outcome.fallback else "empty draft",
            "",
            "",
            1,
            outcome.fallback,
        )
    source = extract_python(outcome.output)
    if not source:
        return None, Score("", False, False, "no python block", "", "", 1, False)
    return source, None


def score_generate(
    task: Task,
    generate: GenerateFn,
    *,
    repair: bool = False,
    guard: PythonVibeGuard | None = None,
) -> Score:
    checker = guard or PythonVibeGuard()
    prompt = RUN_PREFIX + task.prompt
    try:
        outcome = complete(generate, checker, PYTHON_VIBE_FALLBACK, prompt)
    except (TimeoutError, RuntimeError, OSError) as exc:
        return Score(task.id, False, False, f"generate error: {exc}", "", str(exc), 1, False)
    source, early = _draft_source(outcome)
    if early is not None:
        return Score(task.id, early.passed, False, early.reason, "", "", 1, early.fallback)
    assert source is not None
    _remember(generate, prompt, outcome.output or source)
    first = score_source(task, source)
    if first.passed or not repair:
        return first
    err = (first.stderr or first.stdout).strip() or first.reason
    repair_prompt = f"{REPAIR_PREFIX}```\n{err}\n```"
    try:
        repaired = complete(generate, checker, PYTHON_VIBE_FALLBACK, repair_prompt)
    except (TimeoutError, RuntimeError, OSError) as exc:
        return Score(
            task.id, False, True, f"generate error: {exc}", first.stdout, first.stderr, first.exit_code, False
        )
    source2, early2 = _draft_source(repaired)
    if early2 is not None:
        return Score(
            task.id, False, True, early2.reason, first.stdout, first.stderr, first.exit_code, early2.fallback
        )
    assert source2 is not None
    second = score_source(task, source2)
    return Score(
        task.id,
        second.passed,
        True,
        f"repair {second.reason}",
        second.stdout,
        second.stderr,
        second.exit_code,
        False,
    )


def run_repeats(
    tasks: list[Task],
    generate: GenerateFn,
    *,
    repair: bool,
    repeats: int,
    reset: Callable[[], None] | None = None,
) -> Iterator[Score]:
    for _ in range(repeats):
        for task in tasks:
            if reset is not None:
                reset()
            else:
                _reset(generate)
            yield score_generate(task, generate, repair=repair)
