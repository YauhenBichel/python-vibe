"""Repairs the harness can make on its own, before any model turn.

One file of nine hundred lines held six separate jobs: repairing a
name, resolving a conflict, writing a test, adding a function, adding
an import, and the pass that runs them in order. They are six modules
now, and this is the door on to them.
"""

from __future__ import annotations

from harness.act.autofix.names import (
    UnboundTypo,
    _all_defined_names,
    _bound_in_scope,
    _class_body_ids,
    _is_typo,
    _rename_name_tokens,
    apply_person_bind,
    apply_typo_fixes,
    levenshtein,
    replacement_from_answer,
    typo_pairs,
    unbound_typo,
)
from harness.act.autofix.conflicts import (
    CONFLICT_END,
    CONFLICT_MID,
    CONFLICT_START,
    _resolve_conflict,
    conflict_blocks,
    looks_like_conflict,
    resolve_keeping_both,
)
from harness.act.autofix.cover import (
    MIN_SHARE_REACHED,
    _add_import_symbol,
    _append_class_method,
    _body_lines,
    _candidates,
    _find_callable,
    _imports,
    _lines_reached,
    _sample_values,
    _test_file_for,
    apply_cover_test,
)
from harness.act.autofix.additions import (
    _COUNT_NAME,
    _assign_names_for_module,
    _impl_py,
    _top_level_names,
    append_instead_of_replacing,
    apply_add_function,
    apply_function_rename,
    usual_first_arg,
)
from harness.act.autofix.missing_imports import (
    apply_missing_imports,
)
from harness.act.autofix.mechanical import (
    apply_mechanical,
)

__all__ = [
    "CONFLICT_END",
    "CONFLICT_MID",
    "CONFLICT_START",
    "MIN_SHARE_REACHED",
    "UnboundTypo",
    "_is_typo",
    "_rename_name_tokens",
    "_sample_values",
    "_test_file_for",
    "append_instead_of_replacing",
    "apply_add_function",
    "apply_cover_test",
    "apply_function_rename",
    "apply_mechanical",
    "apply_missing_imports",
    "apply_person_bind",
    "apply_typo_fixes",
    "conflict_blocks",
    "levenshtein",
    "looks_like_conflict",
    "replacement_from_answer",
    "resolve_keeping_both",
    "typo_pairs",
    "unbound_typo",
    "usual_first_arg",
]
