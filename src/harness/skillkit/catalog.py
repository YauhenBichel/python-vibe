"""Load SKILL.md files. Deterministic. No model.

Looks in the project `skills/` folder and the py-harness kit
(`<repo>/skills`). Same name: project wins.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness.paths import KIT_SKILLS_DIR
from harness.task import (
    looks_like_add_feature,
    looks_like_algorithm,
    looks_like_analytics,
    looks_like_design_loop,
    looks_like_fix_smell,
    looks_like_http_client,
    looks_like_app_loop,
    looks_like_app_overflow,
    looks_like_new_package,
    looks_like_ops,
    looks_like_platform,
    looks_like_question,
    looks_like_script,
    mentions_cli,
    mentions_http,
)

_FRONT = re.compile(r"^---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
_NAME = re.compile(r"^name:\s*(.+)$", re.MULTILINE)
_DESC = re.compile(r"^description:\s*(.+)$", re.MULTILINE)
MAX_SKILL_CHARS = 2500


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    path: Path


def kit_skills_dir() -> Path:
    return KIT_SKILLS_DIR


def _parse_skill(path: Path) -> Skill | None:
    text = path.read_text(encoding="utf-8")
    match = _FRONT.match(text)
    if not match:
        return None
    meta, body = match.group(1), match.group(2).strip()
    name = _NAME.search(meta)
    desc = _DESC.search(meta)
    raw_name = name.group(1).strip() if name else path.parent.name
    if not raw_name or not desc:
        return None
    return Skill(
        name=raw_name,
        description=desc.group(1).strip(),
        body=body,
        path=path,
    )


def _scan_dir(root: Path) -> dict[str, Skill]:
    found: dict[str, Skill] = {}
    if not root.is_dir():
        return found
    for skill_md in sorted(root.glob("*/SKILL.md")):
        parsed = _parse_skill(skill_md)
        if parsed:
            found[parsed.name] = parsed
    return found


def list_skills(project: Path | None = None, extra: Path | None = None) -> list[Skill]:
    merged: dict[str, Skill] = {}
    merged.update(_scan_dir(kit_skills_dir()))
    if extra:
        merged.update(_scan_dir(extra))
    if project:
        merged.update(_scan_dir(project.resolve() / "skills"))
    return sorted(merged.values(), key=lambda item: item.name)


def get_skill(name: str, project: Path | None = None) -> Skill | None:
    key = name.strip().lower()
    if not key:
        return None
    for skill in list_skills(project):
        if skill.name.lower() == key:
            return skill
    return None


def skill_from_action(
    action: str, name: str = "", path: str = "", project: Path | None = None
) -> Skill | None:
    """Action: skill + Name:, or Action: write-tests as a shortcut."""
    if action == "skill":
        return get_skill(name or path, project)
    return get_skill(action, project)


def pick_skills(task: str, catalog: list[Skill]) -> list[Skill]:
    picked: list[Skill] = []
    if looks_like_question(task):
        picked.extend(s for s in catalog if s.name == "answer-question")
    from harness.task import (
        looks_like_merge,
        looks_like_ship,
        looks_like_ticket,
        looks_like_ticket_work,
    )

    if looks_like_merge(task):
        picked.extend(s for s in catalog if s.name == "merge-pr")
        return picked
    if looks_like_ship(task) and not looks_like_ticket_work(task):
        picked.extend(s for s in catalog if s.name == "open-pr")
        return picked
    if looks_like_ticket(task):
        picked.extend(s for s in catalog if s.name == "read-issue")
        if not looks_like_ticket_work(task) and not looks_like_ship(task):
            return picked
    if looks_like_new_package(task):
        picked.extend(s for s in catalog if s.name == "new-package")
        if looks_like_app_loop(task):
            picked.extend(s for s in catalog if s.name == "write-cli-app")
        if mentions_http(task):
            picked.extend(s for s in catalog if s.name == "call-http")
        elif mentions_cli(task):
            picked.extend(s for s in catalog if s.name == "write-script")
        if mentions_cli(task) or mentions_http(task):
            picked.extend(s for s in catalog if s.name == "write-tests")
        return picked
    if looks_like_app_overflow(task):
        picked.extend(s for s in catalog if s.name == "write-cli-app")
        picked.extend(s for s in catalog if s.name == "call-http")
        picked.extend(s for s in catalog if s.name == "write-tests")
        return picked
    if looks_like_fix_smell(task):
        picked.extend(s for s in catalog if s.name == "fix-smell")
        return picked
    if looks_like_design_loop(task):
        from harness.task import looks_like_review_code, task_paths

        # "review src/app.py" is a review of one file; "review the project
        # structure" is a review of the tree. The named path decides.
        if task_paths(task) and looks_like_review_code(task):
            picked.extend(s for s in catalog if s.name == "review-code")
            return picked
        picked.extend(
            s
            for s in catalog
            if s.name in {"review-design", "refactor-split", "readable-layout"}
        )
        return picked
    if looks_like_ops(task):
        picked.extend(s for s in catalog if s.name == "write-workflow")
        return picked
    if looks_like_platform(task):
        picked.extend(s for s in catalog if s.name == "write-paths")
        picked.extend(s for s in catalog if s.name == "write-tests")
        return picked
    if looks_like_http_client(task):
        picked.extend(s for s in catalog if s.name == "call-http")
        picked.extend(s for s in catalog if s.name == "write-tests")
        return picked
    if looks_like_analytics(task):
        picked.extend(s for s in catalog if s.name == "analyze-data")
        picked.extend(s for s in catalog if s.name == "write-tests")
        return picked
    if looks_like_algorithm(task):
        picked.extend(s for s in catalog if s.name == "write-algorithm")
        picked.extend(s for s in catalog if s.name == "write-tests")
        return picked
    if looks_like_script(task):
        picked.extend(s for s in catalog if s.name == "write-script")
        picked.extend(s for s in catalog if s.name == "write-tests")
        return picked
    if looks_like_add_feature(task):
        picked.extend(s for s in catalog if s.name == "add-feature")
        picked.extend(s for s in catalog if s.name == "write-tests")
    from harness.task import (
        looks_like_archive,
        looks_like_compare,
        looks_like_review_code,
        looks_like_walk_files,
        looks_unclear,
    )

    # Scripting jobs: the model reaches for the shallow primitive on its own
    # (os.listdir for "under a folder", a shell call for a zip), so the skill
    # is what supplies the right one.
    for matches, skill_name in (
        (looks_like_archive, "use-archive"),
        (looks_like_compare, "compare-things"),
        (looks_like_walk_files, "walk-files"),
    ):
        if matches(task) and not any(s.name == skill_name for s in picked):
            picked.extend(s for s in catalog if s.name == skill_name)
            break

    if looks_unclear(task):
        picked.extend(s for s in catalog if s.name == "ask-when-unclear")
    if looks_like_review_code(task) and not picked:
        picked.extend(s for s in catalog if s.name == "review-code")
    lowered = task.strip().lower()
    if "test" in lowered and not any(s.name == "write-tests" for s in picked):
        picked.extend(s for s in catalog if s.name == "write-tests")
    return picked


def render_catalog(catalog: list[Skill]) -> str:
    if not catalog:
        return "Skills: (none)"
    lines = ["Skills (Action: skill + Name: …, or --skill):"]
    for skill in catalog:
        lines.append(f"  {skill.name} — {skill.description}")
    return "\n".join(lines)


def render_skill(skill: Skill, target=None, project: Path | None = None) -> str:
    """Render one skill, repointed at `project` when a target is given.

    Without a target the kit paths stay literal, which is only right for the
    eval fixtures. See harness.skillkit.target.
    """
    body = skill.body
    if target is not None:
        from harness.skillkit.target import retarget

        body = retarget(body, target, project)
    if len(body) > MAX_SKILL_CHARS:
        body = body[:MAX_SKILL_CHARS] + "\n# … skill truncated\n"
    return f"# skill {skill.name}\n{skill.description}\n\n{body}"
