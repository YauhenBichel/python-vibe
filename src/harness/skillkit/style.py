"""The rules a change and a finish are judged by.

Two questions, and they were in one file of nearly seven hundred
lines. Whether a proposed change may be written is `draft_rules`;
whether a run may say it is done is `finish_rules`. This is the door
on to both, so nothing that imports from here had to change.
"""

from harness.skillkit.draft_rules import (
    _opaque_param,
    _undefined_message,
    refuse_add_opens_file,
    refuse_god_target,
    refuse_layout,
    refuse_opaque_names,
    refuse_ops_draft,
    refuse_platform_draft,
    refuse_rename_incomplete,
    refuse_shell_fetch,
    refuse_smell_wrong_file,
    refuse_stdlib_shadow,
    refuse_stub_body,
    refuse_test_in_impl,
    refuse_undefined_draft,
    refuse_weak_test,
    task_names_arguments,
    wrap_bare_unittest,
)
from harness.skillkit.finish_rules import (
    _a_test_uses,
    refuse_done_oracle,
    refuse_package_done,
    refuse_unwired_addition,
    refuse_write_done,
)

__all__ = [
    "refuse_add_opens_file",
    "refuse_god_target",
    "refuse_layout",
    "refuse_opaque_names",
    "refuse_ops_draft",
    "refuse_platform_draft",
    "refuse_rename_incomplete",
    "refuse_shell_fetch",
    "refuse_smell_wrong_file",
    "refuse_stdlib_shadow",
    "refuse_stub_body",
    "refuse_test_in_impl",
    "refuse_undefined_draft",
    "refuse_weak_test",
    "task_names_arguments",
    "wrap_bare_unittest",
    "refuse_done_oracle",
    "refuse_package_done",
    "refuse_write_done",
]
