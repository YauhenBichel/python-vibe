"""Score one draft against a held-out task. No model. No network."""

from __future__ import annotations

import subprocess
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path

from harness.code import RunResult, extract_python, write_and_run_fixed
from harness.engines import GenerateFn, remember
from harness.eval_tasks import REPAIR_PREFIX, RUN_PREFIX, Task
from harness.fallbacks import PYTHON_VIBE_FALLBACK
from harness.python_vibe import PythonVibeGuard
from harness.run import complete
from harness.types import Outcome


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
    samples: int = 1
    hit: int = 0


def stdout_matches(expect: str, got: str) -> bool:
    return got.rstrip("\n") == expect.rstrip("\n")


def run_source(task: Task, source: str, dest: Path) -> tuple[bool, RunResult]:
    work = dest.parent
    for rel, content in task.files:
        path = work / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    try:
        result, _fixed = write_and_run_fixed(
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


def _reset_history(
    generate: GenerateFn, reset: Callable[[], None] | None = None
) -> None:
    if reset is not None:
        reset()
        return
    history = getattr(generate, "history", None)
    if history is not None:
        history.clear()


def _repair_prompt(err: str, hint: str | None) -> str:
    prefix = REPAIR_PREFIX
    if hint:
        prefix += f"Hint: {hint.strip()[:400]}\n"
    return f"{prefix}```\n{err}\n```"


def _score_one(
    task: Task,
    generate: GenerateFn,
    *,
    repair: bool,
    guard: PythonVibeGuard,
    hint: GenerateFn | None = None,
) -> Score:
    prompt = RUN_PREFIX + task.prompt
    try:
        outcome = complete(generate, guard, PYTHON_VIBE_FALLBACK, prompt)
    except (TimeoutError, RuntimeError, OSError) as exc:
        return Score(task.id, False, False, f"generate error: {exc}", "", str(exc), 1, False)
    source, early = _draft_source(outcome)
    if early is not None:
        return Score(task.id, early.passed, False, early.reason, "", "", 1, early.fallback)
    assert source is not None
    remember(generate, prompt, outcome.output or source)
    first = score_source(task, source)
    if first.passed or not repair:
        return first
    if first.exit_code == 0:
        got = (first.stdout or "").strip()[:800]
        err = (
            "The script exited 0 but stdout is wrong. "
            "Print exactly what was asked — no extra text.\n"
            f"Got:\n{got}"
        )
    else:
        err = (first.stderr or first.stdout).strip() or first.reason
    note = None
    if hint is not None:
        try:
            note = hint(
                "One line: what is wrong and how to fix it. No code.\n"
                f"```\n{err[:800]}\n```"
            )
        except (TimeoutError, RuntimeError, OSError):
            note = None
    repair_prompt = _repair_prompt(err, note)
    try:
        repaired = complete(generate, guard, PYTHON_VIBE_FALLBACK, repair_prompt)
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


def score_generate(
    task: Task,
    generate: GenerateFn,
    *,
    repair: bool = False,
    samples: int = 1,
    guard: PythonVibeGuard | None = None,
    reset: Callable[[], None] | None = None,
    hint: GenerateFn | None = None,
) -> Score:
    checker = guard or PythonVibeGuard()
    last: Score | None = None
    n = max(1, samples)
    for i in range(1, n + 1):
        _reset_history(generate, reset)
        last = _score_one(task, generate, repair=repair, guard=checker, hint=hint)
        if last.passed:
            return replace(last, samples=i, hit=i)
    assert last is not None
    return replace(last, samples=n, hit=0)


def run_repeats(
    tasks: list[Task],
    generate: GenerateFn,
    *,
    repair: bool,
    repeats: int,
    samples: int = 1,
    reset: Callable[[], None] | None = None,
    hint: GenerateFn | None = None,
) -> Iterator[Score]:
    for _ in range(repeats):
        for task in tasks:
            yield score_generate(
                task,
                generate,
                repair=repair,
                samples=samples,
                reset=reset,
                hint=hint,
            )
