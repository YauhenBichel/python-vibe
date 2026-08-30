"""Build the first prompt sent to the model.

The prompt is assembled from the project summary, the project's own
contributor instructions, the list of available skills, the skills selected
for this task, and anything the harness looked up before the model started.

There is one builder so that the agent loop, the skill probe and the HTTP
server all send the same prompt. These were previously written out
separately and had drifted apart, which meant measurements taken with the
probe did not describe the prompt the agent actually used.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from harness.act.autofix import apply_mechanical
from harness.agent.options import AgentOptions
from harness.locate import prelude, signature_line
from harness.scan.project_brief import (
    ProjectBrief,
    classify_project,
    render_brief,
    start_hint,
)
from harness.scan.project_docs import render_house_rules
from harness.ship.git_ship import read_ticket
from harness.skillkit.catalog import (
    Skill,
    get_skill,
    list_skills,
    pick_skills,
    render_catalog,
    render_skill,
)
from harness.skillkit.target import Target, pick_target, retarget
from harness.task import issue_number, looks_like_pr_ref, question_symbol


@dataclass(frozen=True)
class Preamble:
    """Everything the loop learned before the model's first turn."""

    prompt: str
    brief: ProjectBrief
    target: Target
    system: str = ""
    catalog: tuple[Skill, ...] = ()
    skills: tuple[Skill, ...] = ()
    located_path: str = ""
    located_signature: str = ""
    pre_text: str = ""
    autofix: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)


def choose_skills(
    project: Path, task: str, brief: ProjectBrief, names: tuple[str, ...]
) -> list[Skill]:
    """Explicit `--skill` names win; otherwise the task picks."""
    catalog = list_skills(project)
    if names:
        chosen = []
        for name in names:
            found = get_skill(name, project)
            if found is None:
                raise ValueError(f"unknown skill: {name}")
            chosen.append(found)
        return chosen
    chosen = pick_skills(task, catalog)
    if brief.kind == "large":
        extra = get_skill("stay-scoped", project)
        if extra and extra.name not in {item.name for item in chosen}:
            chosen.append(extra)
    return chosen


def build_preamble(options: AgentOptions) -> Preamble:
    project = options.resolved_project()
    task = options.task
    brief = classify_project(project, options.scope)
    catalog = list_skills(project)
    notes: list[str] = []

    pre_text, located_path = prelude(project, task, options.scope)
    autofix = apply_mechanical(
        project, task, located_path, write=options.allow_writes
    )
    if autofix and options.allow_writes:
        pre_text, located_path = prelude(project, task, options.scope)
        pre_text = f"{pre_text}\n\n{autofix}" if pre_text else autofix
    elif autofix:
        pre_text = f"{pre_text}\n\n{autofix}" if pre_text else autofix
    located_signature = (
        signature_line(pre_text, question_symbol(task)) if pre_text else ""
    )
    if pre_text:
        notes.append(pre_text)

    ticket = issue_number(task)
    if ticket:
        prefer = "pr" if looks_like_pr_ref(task) else "issue"
        block = (
            f"Harness ticket #{ticket}\n"
            f"{read_ticket(project, ticket, prefer=prefer)}"
        )
        notes.append(block)
        pre_text = f"{pre_text}\n\n{block}" if pre_text else block

    skills = choose_skills(project, task, brief, options.skills)
    target = pick_target(project, task, options.scope, located_path)
    skill_block = ""
    if skills:
        skill_block = (
            "\n\n".join(render_skill(item, target, project) for item in skills)
            + "\n\n"
        )
    house = render_house_rules(project)
    read_only = (
        "" if options.allow_writes
        else "This run is read-only. Do not patch, edit, or run. Answer instead.\n"
    )
    prompt = (
        f"{render_brief(brief, scope=options.scope)}\n\n"
        + (f"{house}\n\n" if house else "")
        + f"{render_catalog(catalog)}\n\n"
        + skill_block
        + (f"{pre_text}\n\n" if pre_text else "")
        + f"Project root: {project}\n"
        + (f"Scope: {options.scope}\n" if options.scope else "")
        + read_only
        + f"Task: {task}\n"
        + start_hint(brief, task, located=bool(located_path))
    )
    return Preamble(
        prompt=prompt,
        system=retarget(options.system, target),
        brief=brief,
        target=target,
        catalog=tuple(catalog),
        skills=tuple(skills),
        located_path=located_path,
        located_signature=located_signature,
        pre_text=pre_text,
        autofix=autofix,
        notes=tuple(notes),
    )
