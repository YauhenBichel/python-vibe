"""Which local weight a task should use. Deterministic. No LLM router.

Papers call this routing (pick one model first) versus cascading (cheap
model first, escalate if a judge fails). This harness already cascades on
compiler oracles, same model. The router only names a *lane*. It never
selects the 0.5B sidecar or the 30B that timed out on this laptop.
"""

from __future__ import annotations

from harness.task import (
    looks_like_add_feature,
    looks_like_bugfix,
    looks_like_design_loop,
    looks_like_everyday_code,
    looks_like_fix_smell,
    looks_like_question,
    looks_like_review_code,
    looks_like_ship,
    looks_like_write_tests,
    task_paths,
)

EVERYDAY = "llama3.1:8b"
TINY = "qwen2.5-coder:0.5b"
FAST = "qwen2.5-coder:1.5b"
CODER = "qwen2.5-coder:7b"
HEAVY = "qwen3coder:latest"

LANES = ("none", "read", "write", "structure")


def model_lane(task: str) -> str:
    """One of LANES. Ship and one-file reviews are not write jobs."""
    if looks_like_ship(task):
        return "none"
    if looks_like_question(task):
        return "read"
    if looks_like_design_loop(task) and not task_paths(task):
        return "structure"
    if looks_like_review_code(task) and task_paths(task):
        return "read"
    if (
        looks_like_add_feature(task)
        or looks_like_everyday_code(task)
        or looks_like_write_tests(task)
        or looks_like_fix_smell(task)
        or looks_like_bugfix(task)
    ):
        return "write"
    if looks_like_design_loop(task):
        return "structure"
    return "write"


def suggest_ollama(task: str) -> str:
    """Ollama name to run, or empty when the harness needs no model."""
    if model_lane(task) == "none":
        return ""
    return EVERYDAY


def route_advice(task: str) -> str:
    """Human-readable pick. Safe to print from `brief` / `route`."""
    lane = model_lane(task)
    model = suggest_ollama(task)
    if lane == "none":
        return (
            "Lane: none. No model. Ship actions are limited git/gh. "
            "Do not pull a larger weight for this."
        )
    extra = {
        "read": (
            f"Lane: read. Use {model}. "
            "A chat 8B is enough for a typed question. "
            "Do not use the 0.5B sidecar (misses Action:). "
            f"{FAST} is on disk but unproven on this protocol."
        ),
        "write": (
            f"Lane: write. Use {model}. "
            f"Optional specialist when pulled: {CODER} via --model. "
            f"Do not auto-switch to {HEAVY} (180s timeout on this laptop). "
            "Oracles stay on the same model — do not load a second weight mid-run."
        ),
        "structure": (
            f"Lane: structure. Use {model}. "
            "The design scan is deterministic. A 30B does not replace it."
        ),
    }
    return extra[lane]
