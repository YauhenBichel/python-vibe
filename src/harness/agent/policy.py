"""Decide whether a proposed action is allowed, and what to do next.

The loop consults three functions, in this order:

* `refuse_before` runs before an action is carried out. It returns the
  reason the action is not allowed, or an empty string if it is allowed.
* `refuse_done` runs when the model reports that the task is finished. It
  returns the reason the work is not finished, or an empty string.
* `next_prompt` runs after an action has been carried out. It returns the
  single next instruction to send, or an empty string to leave the choice
  to the model.

Keeping these separate from the loop means a new rule is a new function
rather than another branch inside the loop.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from harness.act.tools import read_py
from harness.agent.dispatch import SHIP_ACTIONS, WRITE_ACTIONS
from harness.guard.loop_guard import LoopGuard
from harness.paths import as_project_rel
from harness.locate import (
    refuse_design_dirty,
    refuse_early_done,
    refuse_invented_review,
    refuse_question_ask,
    refuse_question_write,
    refuse_redundant_explore,
    refuse_redundant_locate,
    refuse_shallow_done,
    refuse_thin_review,
    refuse_write_tests_ask,
)
from harness.skillkit.catalog import get_skill, render_skill
from harness.scan.names import undefined_in_file
from harness.skillkit.refuse_change import (
    refuse_god_target,
    refuse_smell_wrong_file,
)
from harness.skillkit.refuse_finish import (
    refuse_done_oracle,
    refuse_unwired_addition,
    refuse_write_done,
)

from harness.task import (
    everyday_example_path,
    looks_like_add_feature,
    looks_like_ops,
    looks_like_platform,
    looks_like_bugfix,
    looks_like_design_loop,
    named_project_file,
    looks_like_fix_smell,
    looks_like_write_tests,
    covered_symbol,
    looks_like_merge,
    looks_like_new_package,
    looks_like_question,
    looks_like_ship,
    looks_like_ticket,
    question_symbol,
    rename_target,
    smell_symbol,
)

MAX_QUESTIONS = 2
# How often the loop may send a summary back for being too thin.
MAX_THIN_DONE = 2
# How often a failed Action: run is sent back with the traceback.
# One repair is the daily-work default; a second failure is reported.
MAX_REPAIRS = 1
# How often a change task may finish without changing anything before the
# run stops calling it done.
MAX_EMPTY_DONE = 2
# A quoted line short enough to appear by chance proves nothing. `return`
# and `import os` are in half the files in any project.
MIN_QUOTED_CHARS = 12
# A Summary this close to a line it was given is an echo, not an answer.
ECHO_RATIO = 0.75


@dataclass
class LoopState:
    """Facts the loop has gathered, used to judge the next action.

    Fields:
        task: the user's request.
        project: directory being worked in.
        located_path: file the harness found before the model started.
        located_signature: the definition line found in that file.
        prelude_ran: whether the harness searched before the model started.
        allow_writes: whether file changes are permitted in this run.
        last_path: file the most recent action applied to.
        ran_tests: whether the test suite has passed during this run.
        design_report: last deterministic structure scan, if any.
        autofixed: the harness already applied a rename or unique typo.
        scope: optional subdirectory the run is limited to.
        questions_asked: how many questions the agent has put to the user.
        thin_done_refused: how often a summary was sent back as too thin.
        instructions: skill lines the model was given, used to detect a
            reply that repeats an instruction instead of answering.
        guard: record of read-only actions already performed.
        files_seen: files whose text this run has in front of it, either
            because it read them or because the harness located them.
        repairs: how many failed runs have already been sent back with
            the traceback. Daily work gets one; a second failure stops
            the nudge so the model reports rather than looping.
    """

    task: str
    project: Path
    located_path: str = ""
    located_signature: str = ""
    prelude_ran: bool = False
    allow_writes: bool = True
    last_path: str = ""
    ran_tests: bool = False
    design_report: str = ""
    autofixed: bool = False
    scope: str = ""
    questions_asked: int = 0
    wrote_something: bool = False
    empty_done_refused: int = 0
    thin_done_refused: int = 0
    instructions: tuple[str, ...] = ()
    guard: LoopGuard = field(default_factory=LoopGuard)
    files_seen: set[str] = field(default_factory=set)
    repairs: int = 0


def refuse_patch_before_reading(state: LoopState, turn) -> str:
    """Reject a Find: for a file this run has never looked at.

    A `Find:` string has to match the file exactly. One written without
    reading the file is written from memory, and memory is where
    `result = run_case(case, model, steps)` came from — a line that is
    not in the file at all, refused, and then sent again. Across every
    failing run of one task the model went from `grep` straight to
    `patch`, and spent the budget guessing at a line it could have read.

    An append needs no Find, so it is not refused. Nor is a file the
    harness located, because its text is already in the opening turn.
    """
    if turn.action != "patch" or not turn.find.strip():
        return ""
    rel = as_project_rel(turn.path or state.last_path)
    if not rel:
        return ""
    seen = {as_project_rel(item) for item in state.files_seen}
    if state.located_path:
        seen.add(as_project_rel(state.located_path))
    if rel in seen:
        return ""
    return (
        f"Nothing has read {rel} in this run, so Find: is being written "
        f"from memory. Action: read Path: {rel} first, then copy a whole "
        "line from it."
    )


def refuse_wrong_file(task: str, project: Path, action: str, path: str) -> str:
    """Reject a write to a file other than the one the task named.

    When a task names exactly one file that exists, that file is the whole
    instruction. An 8B given `src/harness/model/engine.py` was observed
    patching `src/harness/act/patch_fix.py` instead.
    """
    if action not in WRITE_ACTIONS or action == "run":
        return ""
    if looks_like_write_tests(task):
        got = as_project_rel(path)
        parts = got.split("/") if got else []
        if got and "tests" not in parts and not parts[-1].startswith("test_"):
            symbol = covered_symbol(task)
            dest = (
                f"tests/test_{symbol.split('.')[-1]}.py"
                if symbol
                else "tests/test_module.py"
            )
            return f"Tests go in {dest}. Do not change {got}."
    # A file the task names outright beats any routing rule below. "in
    # src/app.py ... fix it for Windows" was being sent to pkg/paths.py,
    # which ignores the one instruction the person gave.
    if named_project_file(task, project):
        return _refuse_other_than_named(task, project, path)
    if looks_like_platform(task) or looks_like_ops(task):
        from harness.skillkit.target import pick_module

        wanted = (
            pick_module(project, "", task)
            if looks_like_ops(task)
            else everyday_example_path(task)
        )
        got = as_project_rel(path)
        parts = got.split("/") if got else []
        if (
            got
            and wanted
            and got != wanted
            and "tests" not in parts
            and not parts[-1].startswith("test_")
        ):
            return (
                f"This job writes {wanted}. Do not change {got}. "
                f"Action: edit Path: {wanted}"
            )
    if looks_like_add_feature(task):
        from harness.skillkit.target import pick_module

        wanted = pick_module(project, "", task)
        got = as_project_rel(path)
        parts = got.split("/") if got else []
        if (
            got
            and wanted
            and got != wanted
            and "tests" not in parts
            and not parts[-1].startswith("test_")
        ):
            return (
                f"The new function belongs in {wanted}. Do not change {got}. "
                f"Action: patch Path: {wanted}"
            )
    named = named_project_file(task, project)
    if not named:
        return ""
    wanted = as_project_rel(named)
    got = as_project_rel(path)
    if not got or got == wanted or wanted.endswith(got) or got.endswith(wanted):
        return ""
    # "write tests for apply_discount in src/orders.py" names the source
    # file, but the test belongs beside it, not inside it. A test file is
    # always an allowed destination.
    parts = got.split("/")
    if "tests" in parts or parts[-1].startswith("test_"):
        return ""
    return (
        f"The task names {wanted}. Do not change {got}. "
        f"Action: patch Path: {wanted}"
    )


def _refuse_other_than_named(task: str, project: Path, path: str) -> str:
    """Allow the named file and its tests; refuse anything else."""
    named = named_project_file(task, project)
    wanted = as_project_rel(named)
    got = as_project_rel(path)
    if not got or got == wanted or wanted.endswith(got) or got.endswith(wanted):
        return ""
    parts = got.split("/")
    if "tests" in parts or parts[-1].startswith("test_"):
        return ""
    return (
        f"The task names {wanted}. Do not change {got}. "
        f"Action: patch Path: {wanted}"
    )


def refuse_before(state: LoopState, turn) -> str:
    """The turn is about to run a tool. Return a refusal, or ""."""
    if state.autofixed and turn.action not in {"run", "done"}:
        if turn.action in {"edit", "patch"} and "test" in (
            turn.path or state.last_path or ""
        ).lower():
            return ""
        return (
            "Harness already applied the mechanical fix. "
            "Action: run Argv: -m unittest discover -s tests -q"
        )
    if not state.allow_writes and turn.action in WRITE_ACTIONS:
        return (
            "This run is read-only. Do not patch, edit, or run. "
            "Action: done Summary: say what you would change and why."
        )
    if turn.action == "ask" and state.wrote_something:
        # A live run wrote a function and a test, then asked which of two
        # readings was meant. The question was reasonable and far too
        # late: the files were already on disk under one of them. Once
        # something is written, the next move is to run or to report.
        if state.ran_tests:
            return (
                "Tests already passed. Action: done Summary: say what you changed."
            )
        return (
            "You have already changed files, so it is too late to ask. "
            "Action: run Argv: -m unittest discover -s tests -q"
        )
    if turn.action == "ask" and state.questions_asked >= MAX_QUESTIONS:
        return (
            "You have already asked. Choose the most likely reading, say "
            "which you chose, and continue."
        )
    blocked = refuse_write_tests_ask(state.task, turn.action)
    if blocked:
        return blocked
    blocked = refuse_patch_before_reading(state, turn)
    if blocked:
        return blocked
    blocked = refuse_wrong_file(
        state.task, state.project, turn.action, turn.path or state.last_path
    )
    if not blocked:
        blocked = refuse_question_write(state.task, turn.action)
    if not blocked:
        blocked = refuse_question_ask(state.task, turn.action, state.located_path)
    if not blocked:
        blocked = refuse_redundant_explore(
            state.task, turn.action, turn.path, state.located_path
        )
    if not blocked:
        blocked = refuse_redundant_locate(
            state.task, turn.action, state.prelude_ran, state.project
        )
    if not blocked:
        blocked = refuse_god_target(
            state.task, state.project, turn.action, turn.path or state.last_path
        )
    if not blocked:
        blocked = refuse_smell_wrong_file(
            state.task,
            turn.action,
            turn.path,
            state.located_path,
            _located_body(state),
        )
    if not blocked:
        blocked = state.guard.check(turn)
    if not blocked and turn.action in SHIP_ACTIONS:
        blocked = _refuse_ship(state.task, turn.action)
    return blocked


def _located_body(state: LoopState) -> str:
    if not state.located_path:
        return ""
    try:
        return read_py(state.project, state.located_path)
    except (OSError, ValueError):
        return ""


def _refuse_ship(task: str, action: str) -> str:
    if action in {"issue", "pr"} and looks_like_ticket(task):
        return ""
    if not looks_like_ship(task):
        return (
            "Ship actions only when the task is about an issue, PR, commit, "
            "or push."
        )
    if action == "merge" and not looks_like_merge(task):
        return "merge only when the task says merge"
    return ""


def refuse_echoed_summary(summary: str, instructions: tuple[str, ...]) -> str:
    """Reject a closing summary that repeats an instruction the model was given.

    A small model will sometimes copy a line out of its skill and present it
    as the answer. For example, given the instruction "quote the -> type
    from the def line (example: tuple[str, int])", it replies with that
    exact sentence. A check that only looks for the return type finds "int"
    inside the example and accepts it, so the text is compared against the
    instructions as well.
    """
    said = _squash(summary)
    if len(said) < 12:
        return ""
    for line in instructions:
        want = _squash(line)
        if len(want) < 12:
            continue
        if said in want or want in said:
            return (
                "That repeats an instruction you were given, it does not "
                "answer. Action: done Summary: say it in your own words and "
                "quote the code you read."
            )
        overlap = len(set(said.split()) & set(want.split()))
        if overlap and overlap / max(1, len(set(said.split()))) >= ECHO_RATIO:
            return (
                "That repeats an instruction you were given, it does not "
                "answer. Action: done Summary: quote the code you read."
            )
    return ""


def _squash(text: str) -> str:
    return " ".join(text.lower().split())


def change_task_file(state: LoopState) -> str | None:
    """The file a finish-without-changing would have to point at.

    None when the task never asked for a change, so finishing without one
    is a good answer and none of this applies.
    """
    task = state.task
    if looks_like_question(task) or looks_like_ship(task):
        return None
    named = named_project_file(task, state.project)
    wants_change = (
        looks_like_add_feature(task)
        or looks_like_fix_smell(task)
        or looks_like_new_package(task)
        or bool(named)
    )
    if not wants_change:
        return None
    return named or state.located_path


def quotes_a_line_from(summary: str, project: Path, rel: str) -> bool:
    """True when the summary copies a line that really is in that file.

    Copying a line is something only a reader can do. Saying a file is
    already correct is something anyone can do, and a model handed the
    words will hand them back: a run refused once for changing nothing
    replied "The line is already correct." That names no line, and it
    was accepted, so the run reported success having done nothing.
    """
    if not rel:
        return False
    try:
        text = (project / rel).read_text(encoding="utf-8")
    except OSError:
        return False
    flat = " ".join(summary.split())
    if not flat:
        return False
    for line in text.splitlines():
        quoted = " ".join(line.split())
        if len(quoted) >= MIN_QUOTED_CHARS and quoted in flat:
            return True
    return False


# A dotted or underscored name in the task is something the task is
# about. Plain words are not: "add the field stopped" is prose, while
# `result.stopped` is a thing that either is in the file or is not.
_CODE_NAME = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b|\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


def missing_from_file(task: str, project: Path, rel: str) -> str:
    """A name the task is about that is nowhere in the file.

    Quoting a line proves the model read the file. It does not prove it
    read the right one: a run asked to add `result.stopped` cleared that
    bar by quoting `if __name__ == "__main__":`, which is in every
    script ever written. Nothing can be already correct about adding a
    name that is not there, and that much is checkable.
    """
    if not rel:
        return ""
    try:
        text = (project / rel).read_text(encoding="utf-8")
    except OSError:
        return ""
    for name in _CODE_NAME.findall(task):
        if name.endswith(".py") or name in rel:
            continue
        if name not in text:
            return name
    return ""


def _proved_already_correct(state: LoopState, turn) -> bool:
    """The claim that nothing needed changing, backed by a line."""
    rel = change_task_file(state)
    if not rel:
        return False
    if missing_from_file(state.task, state.project, rel):
        return False
    summary = getattr(turn, "summary", "") or ""
    return quotes_a_line_from(summary, state.project, rel)


def refuse_done_without_change(state: LoopState, turn) -> str:
    """Reject a `done` on a change task that changed nothing.

    An 8B told to fix a named file was seen finishing after four steps
    with no write and a summary describing the project in general. A file
    that is already correct is a real answer, but the model has to show
    the line rather than assert it.
    """
    if state.wrote_something or change_task_file(state) is None:
        return ""
    if state.empty_done_refused and _proved_already_correct(state, turn):
        return ""
    if state.empty_done_refused >= MAX_EMPTY_DONE:
        return ""
    state.empty_done_refused += 1
    rel = change_task_file(state) or ""
    if state.empty_done_refused == 1:
        where = f"Path: {rel}" if rel else "Path: the file you read"
        return (
            f"Nothing was changed. Action: patch {where} with a Find: line "
            "copied whole from the file and a Replace:. If the file is "
            "already correct, Action: done Summary: copy the line that "
            "makes it correct, exactly as it appears."
        )
    if not rel:
        return (
            "Nothing was changed and the summary shows no line for it. "
            "Action: patch the file you read, or Action: done Summary: "
            "quote the line that already does the job."
        )
    return (
        f"That summary copies no line from {rel}. Action: read Path: "
        f"{rel}, then either patch it, or Action: done Summary: paste "
        "the one line that already does the job."
    )


def done_without_proof(state: LoopState, turn) -> str:
    """What to report instead of a `done` that has nothing to show.

    Returns the honest summary, or "" when the finish is a real one. The
    run ends either way. What changes is whether it claims success, and
    two of nine failures in a 45-run benchmark reported success having
    written nothing, which no stop reason can catch.
    """
    if state.wrote_something or not state.empty_done_refused:
        return ""
    if change_task_file(state) is None or _proved_already_correct(state, turn):
        return ""
    rel = change_task_file(state) or ""
    where = f" {rel} was" if rel else " the file was"
    return (
        f"Asked for a change,{where} left as it was, and the closing "
        "summary points at no line that made the change unnecessary. "
        "Reporting this as unfinished rather than done."
    )


def refuse_done(state: LoopState, turn) -> str:
    """The model says it is finished. Return a refusal, or ""."""
    blocked = refuse_echoed_summary(turn.summary, state.instructions)
    if not blocked:
        blocked = refuse_early_done(state.task, state.last_path, state.located_path)
    if not blocked:
        # Asking for a fuller sentence is worth two turns, not the whole
        # budget. A scripted or stubborn model that cannot produce one
        # otherwise spends every remaining step being told the same thing
        # and the run fails with the answer already in hand.
        thin = refuse_shallow_done(
            state.task, turn.summary, state.located_signature
        )
        if thin and state.thin_done_refused < MAX_THIN_DONE:
            state.thin_done_refused += 1
            blocked = thin
    if not blocked:
        blocked = refuse_unwired_addition(state.project, state.last_path)
    if not blocked:
        blocked = refuse_design_dirty(state.task, state.design_report)
    if not blocked:
        blocked = refuse_thin_review(state.task, turn.summary, state.design_report)
    if not blocked:
        blocked = refuse_invented_review(
            state.task, turn.summary, _located_body(state)
        )
    if not blocked:
        blocked = refuse_write_done(
            state.task, state.ran_tests, wrote=state.wrote_something
        )
    if not blocked:
        blocked = refuse_done_without_change(state, turn)
    if not blocked:
        blocked = refuse_done_oracle(state.task, state.project, state.last_path)
    return blocked


def repair_after_failed_run(state: LoopState, result: str) -> str:
    """Send the traceback back once. A second failure is for the model to stop on."""
    err = result.strip()
    if len(err) > 1200:
        err = err[-1200:]
    rel = state.last_path or "the file you changed"
    if state.repairs >= MAX_REPAIRS:
        return (
            "The repair still fails. Action: done Summary: quote the "
            "traceback line you could not fix.\n"
        )
    state.repairs += 1
    return (
        "The script failed when I ran it.\n"
        f"```\n{err}\n```\n"
        f"Action: patch Path: {rel} with a Find: line copied whole from "
        "the file. Then Action: run Argv: -m unittest discover -s tests -q\n"
    )


def next_prompt(state: LoopState, turn, result: str, target=None) -> str:
    """A tool just ran. Name the one right next step, or "" to stay open."""
    path = (turn.path or state.last_path).lower()
    # Tests passing only means the work is finished if there was some work.
    # An agent that runs the suite first, to see the starting state, would
    # otherwise be told to finish before it had changed anything.
    if turn.action in {"issue", "pr"}:
        for line in result.splitlines():
            if line.startswith("Next:"):
                return line.split(":", 1)[1].strip() + "\n"
    if turn.action == "run" and not result.startswith("exit 0"):
        if result.startswith("refusing") or "no tests/ directory" in result:
            return ""
        if state.wrote_something:
            return repair_after_failed_run(state, result)
        return ""
    if (
        turn.action == "run"
        and result.startswith("exit 0")
        and state.wrote_something
        and not looks_like_design_loop(state.task)
    ):
        leftover = refuse_done_oracle(state.task, state.project, state.last_path)
        if leftover:
            return leftover + "\n"
        return "Tests passed. Action: done Summary: say what you changed.\n"
    wrote = result.startswith(("patched", "wrote"))
    if wrote:
        rel = turn.path or state.last_path
        leftover = undefined_in_file(state.project / rel) if rel else []
        if leftover and looks_like_bugfix(state.task):
            return (
                f"undefined name {leftover[0]} in {rel}. "
                f"Next Action must be patch Path: {rel} Find: {leftover[0]} "
                "Replace: the name you assigned.\n"
            )
    if looks_like_design_loop(state.task) and wrote:
        from harness.scan.design import design_is_clean, render_design_review

        state.design_report = render_design_review(state.project, state.scope)
        if not design_is_clean(state.design_report):
            return (
                f"{state.design_report}\n\n"
                "Next Action must be edit Path: pkg/<new_concern>.py "
                "with one function.\n"
            )
        return (
            f"{state.design_report}\n\n"
            "Next Action must be run Argv: -m unittest discover -s tests -q\n"
        )
    if not wrote:
        return ""
    is_test = "test" in path
    if (
        looks_like_add_feature(state.task)
        and turn.action in {"patch", "edit"}
        and not is_test
        and "AAA test" in result
    ):
        return "Next Action must be run Argv: -m unittest discover -s tests -q\n"
    if (
        (looks_like_add_feature(state.task) or looks_like_bugfix(state.task))
        and turn.action in {"patch", "edit"}
        and not is_test
    ):
        loaded = get_skill("write-tests", state.project)
        if loaded is not None:
            return (
                f"{render_skill(loaded, target, state.project)}\n"
                "Next Action must be this write-tests patch. "
                "Do not Append after if __name__.\n"
            )
    if looks_like_new_package(state.task) and turn.action in {"edit", "patch"}:
        noun = question_symbol(state.task) or "service"
        if "__init__" in path:
            return (
                f"Next Action must be edit Path: pkg/{noun}.py with one "
                f"function def {noun}(...). snake_case. Not in __init__.py.\n"
            )
        if not is_test:
            return (
                f"Next Action must be edit Path: tests/test_{noun}.py as a "
                f"unittest.TestCase. Name test_{noun}_<result>. "
                f"AAA: got = {noun}(...); assert got. Then Action: run.\n"
            )
        return "Next Action must be run Argv: -m unittest discover -s tests -q\n"
    if looks_like_fix_smell(state.task) and turn.action == "patch" and not is_test:
        old, new = smell_symbol(state.task), rename_target(state.task)
        if old and new:
            return (
                f"Next Action: patch tests to replace {old} with {new}, "
                "then Action: run.\n"
            )
    return ""


def unclear(task: str) -> bool:
    """A task with no verb and no symbol cannot be started from."""
    text = task.strip()
    if looks_like_question(text):
        return False
    return len(text.split()) < 3 and not question_symbol(text)
