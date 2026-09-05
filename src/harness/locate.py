"""Deterministic first steps for a small everyday model. No LLM."""

from __future__ import annotations

import re
from pathlib import Path

from harness.act.tools import grep_py, read_py
from harness.scan.names import undefined_names
from harness.task import looks_like_question, question_symbol
from harness.task import looks_like_add_feature
from harness.task import (
    covered_symbol,
    everyday_example_path,
    everyday_skill_name,
    named_project_file,
    looks_like_design_loop,
    looks_like_everyday_code,
    looks_like_fix_smell,
    looks_like_new_package,
    looks_like_refactor,
    looks_like_review,
    looks_like_write_tests,
    smell_symbol,
)

_DEF = re.compile(r"\b(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")


def subject_of(task: str) -> str:
    """The longest dotted name in the task, or "".

    A name like `result.stopped` is the strongest hint a task gives
    about *where* in a file the work is, and it is what an excerpt
    should be centred on. Without it the model was shown the first
    3,500 characters and the last 800 of a 13,476-character file, and
    the dict it had been asked to change was in neither.
    """
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", task)
    dotted = [word for word in words if not word.endswith((".py", ".md", ".txt"))]
    return max(dotted, key=len) if dotted else ""


def signature_line(text: str, symbol: str) -> str:
    if not symbol:
        return ""
    needle = f"def {symbol}("
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            continue
        if raw.count(":") >= 2 and not raw.lstrip().startswith(("def ", "class ", "async ")):
            line = raw.split(":", 2)[-1].strip()
        if needle in line:
            return line.rstrip()
    return ""


def return_annotation(signature: str) -> str:
    if "->" not in signature:
        return ""
    return signature.split("->", 1)[1].rstrip(":").strip()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


_ASKS_RETURN = re.compile(r"\b(return|returns|returned|type|give back|output)\b", re.I)
MIN_DESCRIPTION_WORDS = 4
# Words a return-type answer must add beyond the type itself. The
# bare answer to "what does compute_total return?" was `"int"`, which
# is the annotation read back, not what the function does. Two extra
# words is enough for "compute_total sums int"; asking for four
# rejected answers a person would accept, and the loop then spent
# every remaining step asking again.
MIN_EXTRA_WORDS = 2


def asks_what_it_returns(task: str) -> bool:
    """True for "what does X return?", false for "what does X do?"."""
    return bool(_ASKS_RETURN.search(task))


def refuse_shallow_done(task: str, summary: str, signature: str) -> str:
    """Refuse an answer that is thinner than the question asked for.

    Quoting the return type was added because the model answered "a tuple".
    It was applied to every question, so "what does apply_discount do?" was
    refused for the answer "it reduces a total by a whole percentage" —
    the harness insisting on a worse reply than the one it was given.
    """
    if not looks_like_question(task):
        return ""
    if not asks_what_it_returns(task):
        # A question about behaviour wants a sentence, not a type name.
        if len((summary or "").split()) >= MIN_DESCRIPTION_WORDS:
            return ""
        return (
            "too thin. Action: done Summary: say in a sentence what it does, "
            "from the code you read."
        )
    wanted = return_annotation(signature)
    if not wanted:
        return ""
    compact = _compact(summary or "")
    if _compact(wanted) not in compact:
        return (
            f"too thin. Action: done Summary: must quote {wanted} "
            f"from {signature} and say what it computes."
        )
    extra = [
        word
        for word in re.findall(r"[A-Za-z0-9_]+", summary or "")
        if _compact(word) not in _compact(wanted)
    ]
    if len(extra) < MIN_EXTRA_WORDS:
        return (
            f"too thin. Action: done Summary: quote {wanted} and say in a "
            "sentence what it computes, from the code you read."
        )
    return ""


def def_hit_path(grep_text: str, symbol: str) -> str:
    wanted = symbol.strip()
    if not wanted or grep_text.startswith(("(no hits)", "bad regex")):
        return ""
    fallback = ""
    for line in grep_text.splitlines():
        if line.startswith("#") or line.count(":") < 2:
            continue
        path, _ln, content = line.split(":", 2)
        if not fallback:
            fallback = path
        if re.search(rf"\b(?:def|class)\s+{re.escape(wanted)}\b", content):
            return path
    return fallback


def locate_py(project: Path, query: str, scope: str = "") -> tuple[str, str]:
    if not query.strip():
        return "locate needs Query:", ""
    hits = grep_py(project, query, scope=scope)
    symbol = query.removeprefix("def ").removeprefix("class ").split()[0]
    path = def_hit_path(hits, symbol)
    if not path:
        return hits, ""
    body = read_py(project, path)
    return f"{hits}\n\n# auto-read {path}\n{body}", path


def prelude(project: Path, task: str, scope: str = "") -> tuple[str, str]:
    """Search before the model runs, and say what to do with what was found.

    Small models skip the first grep, so the harness does it for them and
    hands over the file with an instruction attached.

    Each kind of task needs a different opening, so each one is its own
    function below and this only chooses between them. They were a single
    if-chain of a hundred and forty lines, which made the shared tail at
    the end read as if it belonged to whichever branch you had just
    finished reading.
    """
    if looks_like_new_package(task):
        return "", ""
    for opening in (
        _opening_for_design_loop,
        _opening_for_write_tests,
        _opening_for_a_named_file,
    ):
        found = opening(project, task, scope)
        if found is not None:
            return found
    return _opening_found_by_symbol(project, task, scope)


def _opening_for_design_loop(
    project: Path, task: str, scope: str
) -> tuple[str, str] | None:
    """A review or refactor starts from the structure report, not a file."""
    if not looks_like_design_loop(task):
        return None
    from harness.scan.design import design_is_clean, render_design_review

    report = render_design_review(project, scope)
    kind = "refactor" if looks_like_refactor(task) and not looks_like_review(task) else "review"
    if design_is_clean(report):
        next_line = (
            "Next Action must be done. Summary: quote no structure findings."
        )
    else:
        next_line = (
            "Next Action must be edit Path: pkg/<new_concern>.py with one function."
        )
    return f"Harness design review ({kind})\n{next_line}\n\n{report}", ""


def _opening_for_write_tests(
    project: Path, task: str, scope: str
) -> tuple[str, str] | None:
    """Writing a test needs the subject located and a destination chosen."""
    if not looks_like_write_tests(task):
        return None
    symbol = covered_symbol(task) or question_symbol(task)
    dest = named_project_file(task, project)
    rel = dest.replace("\\", "/").lower()
    if dest and "test" not in rel and not rel.split("/")[-1].startswith("test_"):
        dest = ""
    if not dest and symbol:
        dest = f"tests/test_{symbol.split('.')[-1]}.py"
    if not dest:
        dest = "tests/test_module.py"
    text, path = locate_py(project, symbol, scope) if symbol else ("", "")
    header = (
        f"Harness locate (write-tests) Query: {symbol or 'the function'}\n"
        f"Next Action must be patch Path: {dest} Append: one AAA "
        f"test_<unit>_<result> that calls {symbol or 'the function'}.\n"
        "Do not edit the implementation. Do not ask."
    )
    return f"{header}\n\n{text}", path


def _opening_for_a_named_file(
    project: Path, task: str, scope: str
) -> tuple[str, str] | None:
    """Open the file the task names, and say what may be done to it.

    A task that names a file has already said which file to open.
    Looking up a word out of that path instead found every file in the
    project: "src/harness/model/engine.py" was searched for as
    "harness".

    `scope` is unused here and kept so every opening has one shape and
    the caller can try them in turn.
    """
    named = named_project_file(task, project)
    if named:
        try:
            body = read_py(project, named, about=subject_of(task))
        except (OSError, ValueError):
            body = ""
        if body:
            if looks_like_question(task):
                next_line = (
                    "Next Action must be done. Quote what this file does. "
                    "Do not grep, read, or edit."
                )
            elif reviews_one_named_file(task):
                findings = named_file_review_summary(project, task)
                extra = f"\n{findings}" if findings else ""
                next_line = (
                    "Next Action must be done. Quote a defect from the "
                    "findings below. Do not patch, edit, or run."
                    f"{extra}"
                )
            else:
                next_line = (
                    f"Next Action must be patch Path: {named} with a Find: "
                    "line copied whole from the file below, and a Replace:. "
                    "Do not map or grep."
                )
            return (
                f"Harness opened the file named in the task: {named}\n"
                f"{next_line}\n"
                f"Only {named} may be changed.\n\n"
                f"# auto-read {named}\n{body}",
                named,
            )
    return None


def _opening_found_by_symbol(
    project: Path, task: str, scope: str
) -> tuple[str, str]:
    """Nothing named a file, so find the symbol and say what to do with it."""
    symbol = smell_symbol(task) if looks_like_fix_smell(task) else question_symbol(task)
    if not symbol and looks_like_add_feature(task):
        symbol = question_symbol(task) or ""
    if not symbol:
        return "", ""
    text, path = locate_py(project, symbol, scope)
    if looks_like_question(task):
        kind = "question"
    elif looks_like_fix_smell(task):
        kind = "fix-smell"
    elif looks_like_everyday_code(task):
        kind = everyday_skill_name(task) or "everyday"
    else:
        kind = "add-feature"
    header = f"Harness locate ({kind}) Query: {symbol}"
    header += _what_to_do_next(project, task, symbol, text, path)
    return f"{header}\n\n{text}", path


def _what_to_do_next(
    project: Path, task: str, symbol: str, text: str, path: str
) -> str:
    """The instruction attached to what was found, or "" for none.

    One line per kind of task. An 8B follows the first instruction it
    sees, so there is exactly one and it names the action, the path and
    the shape of the edit.
    """
    header = ""
    if looks_like_question(task) and path:
        header += (
            "\nNext Action must be done. Do not locate, grep, or read."
        )
        sig = signature_line(text, symbol)
        if return_annotation(sig):
            header += (
                f"\nSummary must quote the -> type from: {sig} "
                "and say what the function computes."
            )
    elif looks_like_fix_smell(task) and path:
        header += (
            "\nNext Action must be patch Find: the old def line "
            "Replace: a readable snake_case name. Do not grep."
        )
    elif looks_like_everyday_code(task):
        example = everyday_example_path(task)
        header += (
            f"\nNext Action must be edit Path: {example} with one function. "
            "Do not grep. Do not emit curl."
        )
    elif looks_like_add_feature(task):
        from harness.skillkit.target import pick_module

        dest = path or pick_module(project, path, task)
        header += (
            f"\nNext Action must be patch Path: {dest} "
            f"Append: def {symbol}(...). Do not grep. Do not create a second "
            f"{Path(dest).stem}.py."
        )
        dest_path = Path(project) / dest
        try:
            dest_body = dest_path.read_text(encoding="utf-8")
        except OSError:
            dest_body = ""
        names = [
            name
            for name in re.findall(r"^def \w+\((\w+)", dest_body, re.M)
            if name not in {"self", "cls"}
        ]
        # Only when the task left the argument open. `read_env_file(path)`
        # has already said what it takes, and telling the model to use the
        # neighbours' `prices` instead sent it round the loop until the
        # steps ran out.
        from harness.skillkit.refuse_change import task_names_arguments

        if names and not task_names_arguments(task):
            neighbor = max(set(names), key=names.count)
            header += (
                f" Neighbor functions take `{neighbor}`. Use the same "
                "argument unless the task says otherwise."
            )
    return header


_QUESTION_WRITE = frozenset({"patch", "edit", "run"})
_QUESTION_REEXPLORE = frozenset({"read", "locate", "grep"})


def refuse_redundant_locate(
    task: str, action: str, prelude_ran: bool, project: Path | None = None
) -> str:
    if action != "locate" or not prelude_ran:
        return ""
    if looks_like_question(task):
        return (
            "already located. Action: done Summary: quote the -> type."
        )
    if looks_like_everyday_code(task):
        example = everyday_example_path(task)
        return (
            f"already located. Action: edit Path: {example} with one function."
        )
    if looks_like_add_feature(task):
        dest = ""
        if project is not None:
            from harness.skillkit.target import pick_module

            dest = pick_module(project, "", task)
        where = f" Path: {dest}" if dest else ""
        return (
            f"already located. Action: patch{where} Append: the new function."
        )
    return ""


def refuse_write_tests_ask(task: str, action: str) -> str:
    """Cover-test jobs name the symbol. Asking where tests live wastes the step."""
    if action != "ask" or not looks_like_write_tests(task):
        return ""
    symbol = covered_symbol(task)
    dest = f"tests/test_{symbol}.py" if symbol else "tests/test_<unit>.py"
    return (
        "Do not ask. Action: patch Path: "
        f"{dest} Append: one AAA test_<unit>_<result> method."
    )


_INVENTED = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]{5,})\b")
_INVENTED_SKIP = frozenset(
    {
        "function",
        "returns",
        "return",
        "empty",
        "input",
        "output",
        "should",
        "because",
        "however",
        "potential",
        "defects",
        "defect",
        "errors",
        "found",
        "change",
        "would",
        "summary",
        "action",
        "module",
        "caller",
        "callers",
        "formatted",
        "present",
        "values",
        "counts",
        "measured",
        "estimated",
    }
)


def refuse_invented_review(task: str, summary: str, body: str) -> str:
    """Refuse a review that names a function the file does not contain.

    Live 8B on a real tree invented compute_total and estimate_tokens after
    reading an unrelated OpenSRE file. Demo-task prior, not a finding.
    """
    from harness.task import looks_like_review_code

    if not looks_like_review_code(task):
        return ""
    if not (summary or "").strip() or not (body or "").strip():
        return ""
    invented: list[str] = []
    for name in _INVENTED.findall(summary):
        if name.lower() in _INVENTED_SKIP:
            continue
        if name.lower() in task.lower():
            continue
        if "_" not in name:
            continue
        if name in body or f"def {name}" in body:
            continue
        invented.append(name)
    if not invented:
        return ""
    return (
        f"{invented[0]} is not in the file you read. "
        "Action: done Summary: quote a name that is in # auto-read, or say "
        "no defects found."
    )


def refuse_question_ask(task: str, action: str, located_path: str) -> str:
    if action != "ask" or not looks_like_question(task):
        return ""
    if not located_path:
        return ""
    return (
        "already located. Action: done Summary: quote the -> type from "
        "# auto-read and say what the function computes."
    )


def reviews_one_named_file(task: str) -> bool:
    """True for "review src/orders.py for bugs", false for the design loop.

    A structure review is allowed to edit, because the loop it drives moves
    on to splitting a module. A review of one named file is not: it was
    asked to report.
    """
    from harness.task import looks_like_review_code, task_paths

    return bool(task_paths(task)) and looks_like_review_code(task)


def named_file_review_summary(project: Path, task: str) -> str:
    """Quote compiler findings in a named file. Empty when there are none.

    Live 8B on `review src/orders.py for bugs` was told to patch, then
    refused, then burned the step budget. A hosted agent reads the file
    once and names `subtotl`. This is that read, without a model turn.
    """
    if not reviews_one_named_file(task):
        return ""
    named = named_project_file(task, project)
    if not named:
        return ""
    try:
        body = read_py(project, named, about=subject_of(task))
    except (OSError, ValueError):
        return ""
    leftover = undefined_names(body)
    if not leftover:
        return ""
    shown = ", ".join(leftover)
    return f"Compiler findings: undefined name {shown} in {named} (used, never bound)."


def refuse_question_write(task: str, action: str) -> str:
    if reviews_one_named_file(task) and action in _QUESTION_WRITE:
        return (
            "Reviews do not edit. Action: done Summary: name the defect and "
            "quote the line it is on."
        )
    if looks_like_design_loop(task):
        return ""
    if looks_like_question(task) and action in _QUESTION_WRITE:
        return (
            "Questions do not edit. "
            "Action: done Summary: quote return or refuse from # auto-read."
        )
    return ""


def refuse_thin_review(task: str, summary: str, report: str) -> str:
    if not looks_like_review(task):
        return ""
    from harness.scan.design import design_is_clean

    if design_is_clean(report):
        if "no structure findings" in (summary or "").lower():
            return ""
        return (
            "too thin. Action: done Summary: quote no structure findings"
        )
    keys = [
        word
        for word in ("SoC", "god", "tests", "scripts", "split", "__init__")
        if word.lower() in report.lower()
    ]
    if not keys:
        return ""
    text = (summary or "").lower()
    if any(key.lower() in text for key in keys):
        return ""
    return (
        "too thin. Action: done Summary: quote one finding "
        f"({', '.join(keys[:3])})"
    )


def refuse_design_dirty(task: str, report: str) -> str:
    if not looks_like_design_loop(task):
        return ""
    from harness.scan.design import design_is_clean

    if design_is_clean(report):
        return ""
    return (
        "not done. Structure findings remain. "
        "Action: edit Path: pkg/<new_concern>.py with one function. "
        "Then the harness will re-scan."
    )


def refuse_redundant_explore(
    task: str, action: str, path: str, located_path: str
) -> str:
    if not looks_like_question(task) or not located_path:
        return ""
    if action not in _QUESTION_REEXPLORE:
        return ""
    rel = path.replace("\\", "/").lstrip("./")
    located = located_path.replace("\\", "/").lstrip("./")
    same = (not rel) or rel == located or located.endswith(rel) or rel.endswith(located)
    if not same:
        return ""
    return (
        f"already have # auto-read {located}. "
        "Action: done Summary: quote return or refuse from that file."
    )


def refuse_early_done(task: str, last_path: str, located_path: str) -> str:
    if not looks_like_question(task):
        return ""
    symbol = question_symbol(task)
    if not symbol:
        return ""
    if located_path or (last_path and symbol.replace("_", "") in last_path.replace("_", "").lower()):
        return ""
    return (
        f"not done. Harness or you must locate {symbol} first. "
        f"Action: locate Query: {symbol}"
    )
