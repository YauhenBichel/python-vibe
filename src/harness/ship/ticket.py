"""Turn a GitHub issue or pull request into something to act on.

Reading a ticket is not the same as knowing what to do with it. A ticket
names files, functions and a list of things to finish, and all three are
buried in prose. This pulls out the parts that point at code, checks them
against the project in front of the agent, and quotes comments from other
GitHub users on the same thread — using the signed-in `gh` user, the same
account that can see those comments.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

MAX_BODY = 1600
MAX_ITEMS = 8
MAX_PEER = 400
_PATH = re.compile(r"[\w./-]+\.(?:py|pyi|md|toml|yml|yaml|json|cfg|ini)\b")
_SYMBOL = re.compile(
    r"`([A-Za-z_]\w*)(?:\(\))?`|\b(?:def|function|class)\s+([A-Za-z_]\w*)"
)
_CHECK = re.compile(r"^\s*[-*]\s*\[( |x|X)\]\s*(.+)$", re.MULTILINE)
_BULLET = re.compile(r"^\s*[-*]\s+(?!\[)(.+)$", re.MULTILINE)
_DONE_WHEN = re.compile(r"^#+\s*(done when|acceptance|tasks?|todo)\b", re.I | re.MULTILINE)

# github.com/claude comments on tickets when that product is used on a repo.
# The login is a GitHub username, not a product name in the brief.
WATCHED_LOGINS = frozenset({"claude", "claude[bot]"})


@dataclass(frozen=True)
class Ticket:
    """A ticket, and where in this project it points."""

    number: str
    kind: str
    title: str
    body: str = ""
    state: str = ""
    files: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    symbols: tuple[str, ...] = ()
    todo: tuple[str, ...] = field(default_factory=tuple)
    job: str = ""
    viewer: str = ""
    peers: tuple[tuple[str, str], ...] = ()


def named_paths(text: str) -> list[str]:
    """File paths the text mentions, in order, without repeats."""
    seen: list[str] = []
    for hit in _PATH.findall(text):
        cleaned = hit.strip("./`,;:()[]'\"")
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def named_symbols(text: str) -> list[str]:
    """Functions or classes named in backticks or after def/class."""
    seen: list[str] = []
    for backticked, declared in _SYMBOL.findall(text):
        name = backticked or declared
        if not name or name in seen or len(name) < 3:
            continue
        if "." in name or name.endswith(".py"):
            continue
        seen.append(name)
    return seen


def unfinished_items(text: str) -> list[str]:
    """What the ticket still asks for."""
    boxes = _CHECK.findall(text)
    if boxes:
        return [item.strip() for mark, item in boxes if mark == " "][:MAX_ITEMS]
    match = _DONE_WHEN.search(text)
    if not match:
        return []
    section = text[match.end() :]
    end = re.search(r"^#+\s", section, re.MULTILINE)
    if end:
        section = section[: end.start()]
    return [item.strip() for item in _BULLET.findall(section)][:MAX_ITEMS]


def ticket_job(text: str) -> str:
    """Which write skill the ticket body is asking for."""
    from harness.task import (
        looks_like_add_feature,
        looks_like_bugfix,
        looks_like_fix_smell,
        looks_like_ops,
        looks_like_platform,
        looks_like_write_tests,
    )

    if looks_like_write_tests(text):
        return "write-tests"
    if looks_like_ops(text):
        return "write-workflow"
    if looks_like_platform(text):
        return "write-paths"
    if looks_like_fix_smell(text):
        return "fix-smell"
    if looks_like_bugfix(text):
        return "bugfix"
    if looks_like_add_feature(text):
        return "add-feature"
    return ""


def comments_from(data: dict) -> list[tuple[str, str]]:
    """(login, body) from gh issue/pr JSON comments and reviews."""
    found: list[tuple[str, str]] = []
    blobs: list = []
    for key in ("comments", "reviews"):
        raw = data.get(key) or []
        if isinstance(raw, dict):
            raw = raw.get("nodes") or raw.get("comments") or []
        if isinstance(raw, list):
            blobs.extend(item for item in raw if isinstance(item, dict))
    for item in blobs:
        author = item.get("author")
        if isinstance(author, dict):
            login = str(author.get("login") or "")
        else:
            login = str(author or "")
        body = str(item.get("body") or "").strip()
        if login and body:
            found.append((login, body))
    return found


def identity_from_user_json(payload: str) -> tuple[str, str, str]:
    """login, name, email from `gh api user` JSON."""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return "", "", ""
    if not isinstance(data, dict):
        return "", "", ""
    login = str(data.get("login") or "").strip()
    name = str(data.get("name") or login or "").strip()
    email = str(data.get("email") or "").strip()
    if login and not email:
        email = f"{login}@users.noreply.github.com"
    return login, name, email


def parse_ticket(
    payload: str,
    project: Path,
    *,
    kind: str = "issue",
    viewer: str = "",
) -> Ticket | None:
    """Read what `gh ... view --json` returned, and locate it in the project."""
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    body = str(data.get("body") or "")
    title = str(data.get("title") or "")
    text = f"{title}\n{body}"
    root = Path(project).resolve()
    named = named_paths(text)
    for item in data.get("files") or []:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("path") or item.get("filename") or "").strip()
        if rel and rel not in named:
            named.append(rel)
    here = [rel for rel in named if (root / rel).is_file()]
    peers = [
        (login, body[:MAX_PEER])
        for login, body in comments_from(data)
        if login.lower() in WATCHED_LOGINS
    ]
    return Ticket(
        number=str(data.get("number") or ""),
        kind=kind,
        title=title,
        body=body[:MAX_BODY],
        state=str(data.get("state") or ""),
        files=tuple(here),
        missing=tuple(rel for rel in named if rel not in here),
        symbols=tuple(named_symbols(text)),
        todo=tuple(unfinished_items(body)),
        job=ticket_job(text),
        viewer=viewer,
        peers=tuple(peers),
    )


def next_ticket_action(ticket: Ticket) -> str:
    """The one Action the 8B should take after reading the ticket."""
    if ticket.files:
        return f"Action: read Path: {ticket.files[0]}"
    if ticket.symbols:
        return f"Action: locate Query: {ticket.symbols[0]}"
    words = " ".join(ticket.title.split()[:4]) or "the ask"
    return f"Action: locate Query: {words}"


def render_ticket(ticket: Ticket) -> str:
    """What the agent is shown: the ask, then where it points."""
    lines = [f"{ticket.kind} #{ticket.number}: {ticket.title}"]
    if ticket.state:
        lines.append(f"state: {ticket.state}")
    if ticket.viewer:
        lines.append(f"viewing as @{ticket.viewer} (signed-in gh user)")
    else:
        lines.append("viewing as: not signed in to gh")
    if ticket.job:
        lines.append(f"Job: {ticket.job}")
    if ticket.todo:
        lines.append("")
        lines.append("Still to do:")
        lines.extend(f"  - {item}" for item in ticket.todo)
    if ticket.files:
        lines.append("")
        lines.append("Where (files in this project):")
        lines.extend(f"  {rel}" for rel in ticket.files)
    if ticket.missing:
        lines.append("")
        lines.append(
            "Named but not here (do not create these blindly): "
            + ", ".join(ticket.missing[:5])
        )
    if ticket.symbols:
        lines.append("")
        lines.append("Functions it names: " + ", ".join(ticket.symbols[:8]))
    if ticket.peers:
        lines.append("")
        lines.append("Also on this ticket:")
        for login, excerpt in ticket.peers:
            one = " ".join(excerpt.split())
            lines.append(f"  @{login}: {one}")
    nxt = next_ticket_action(ticket)
    lines.append("")
    lines.append(f"Next: {nxt}")
    if ticket.body:
        lines.append("")
        lines.append(ticket.body)
    return "\n".join(lines)
