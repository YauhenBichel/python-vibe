"""Deterministic first steps for a small everyday model. No LLM."""

from __future__ import annotations

import re
from pathlib import Path

from harness.act.tools import grep_py, read_py
from harness.task import looks_like_question, question_symbol
from harness.task import looks_like_add_feature
from harness.task import (
    everyday_example_path,
    everyday_skill_name,
    named_project_file,
    looks_like_design_loop,
    looks_like_everyday_code,
    looks_like_fix_smell,
    looks_like_new_package,
    looks_like_refactor,
    looks_like_review,
    smell_symbol,
)

_DEF = re.compile(r"\b(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")


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
    if _compact(wanted) in _compact(summary or ""):
        return ""
    return (
        f"too thin. Action: done Summary: must quote {wanted} "
        f"from {signature}"
    )


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
    """Run locate before the model. Small models skip the first grep."""
    if looks_like_design_loop(task):
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
    if looks_like_new_package(task):
        return "", ""

    # A task that names a file has already said which file to open. Looking
    # up a word out of that path instead finds every file in the project:
    # "src/harness/model/engine.py" was searched for as "harness".
    named = named_project_file(task, project)
    if named:
        try:
            body = read_py(project, named)
        except (OSError, ValueError):
            body = ""
        if body:
            if looks_like_question(task):
                next_line = (
                    "Next Action must be done. Quote what this file does. "
                    "Do not grep, read, or edit."
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
    if looks_like_question(task) and path:
        header += (
            "\nNext Action must be done. Do not locate, grep, or read."
        )
        sig = signature_line(text, symbol)
        if return_annotation(sig):
            header += f"\nSummary must quote the -> type from: {sig}"
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
        header += (
            "\nNext Action must be patch with Append: (see the skill). "
            "Do not grep."
        )
    return f"{header}\n\n{text}", path


_QUESTION_WRITE = frozenset({"patch", "edit", "run"})
_QUESTION_REEXPLORE = frozenset({"read", "locate", "grep"})


def refuse_redundant_locate(task: str, action: str, prelude_ran: bool) -> str:
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
        return (
            "already located. Action: patch Path: + Append: the new function."
        )
    return ""


def refuse_question_ask(task: str, action: str, located_path: str) -> str:
    if action != "ask" or not looks_like_question(task):
        return ""
    if not located_path:
        return ""
    return (
        "already located. Action: done Summary: quote the -> type from # auto-read."
    )


def reviews_one_named_file(task: str) -> bool:
    """True for "review src/orders.py for bugs", false for the design loop.

    A structure review is allowed to edit, because the loop it drives moves
    on to splitting a module. A review of one named file is not: it was
    asked to report.
    """
    from harness.task import looks_like_review_code, task_paths

    return bool(task_paths(task)) and looks_like_review_code(task)


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
