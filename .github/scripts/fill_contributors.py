#!/usr/bin/env python3
"""Fill README contributor markers from the GitHub API. No third-party Action.

Bots are omitted. Does not open a pull request (protected main cannot).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

START = "<!-- readme: contributors,bots/- -start -->"
END = "<!-- readme: contributors,bots/- -end -->"
IMAGE = 48
COLUMNS = 6
API = "https://api.github.com"


def _get(url: str, token: str) -> object:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "py-harness-fill-contributors",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_people(repo: str, token: str) -> list[dict[str, str]]:
    people: list[dict[str, str]] = []
    page = 1
    while True:
        rows = _get(
            f"{API}/repos/{repo}/contributors?per_page=100&anon=false&page={page}",
            token,
        )
        if not isinstance(rows, list) or not rows:
            break
        for row in rows:
            if not isinstance(row, dict):
                continue
            login = str(row.get("login") or "")
            kind = str(row.get("type") or "")
            if not login or kind == "Bot" or login.endswith("[bot]"):
                continue
            profile = _get(f"{API}/users/{login}", token)
            name = login
            if isinstance(profile, dict) and profile.get("name"):
                name = str(profile["name"])
            people.append({"login": login, "name": name})
        if len(rows) < 100:
            break
        page += 1
    return people


def render_table(people: list[dict[str, str]]) -> str:
    if not people:
        return ""
    cells = []
    for person in people:
        login = person["login"]
        name = person["name"]
        cells.append(
            "\t\t\t<td align=\"center\">\n"
            f"\t\t\t\t<a href=\"https://github.com/{login}\">\n"
            f"\t\t\t\t\t<img src=\"https://avatars.githubusercontent.com/{login}?s={IMAGE}\" "
            f"width=\"{IMAGE}\" alt=\"{name}\" />\n"
            "\t\t\t\t\t<br />\n"
            f"\t\t\t\t\t<sub><b>{name}</b></sub>\n"
            "\t\t\t\t</a>\n"
            "\t\t\t</td>"
        )
    rows = []
    for index in range(0, len(cells), COLUMNS):
        chunk = "\n".join(cells[index : index + COLUMNS])
        rows.append(f"\t\t<tr>\n{chunk}\n\t\t</tr>")
    return (
        "<table>\n\t<tbody>\n" + "\n".join(rows) + "\n\t</tbody>\n</table>\n"
    )


def apply_readme(text: str, table: str) -> str:
    if START not in text or END not in text:
        raise SystemExit(f"README is missing {START} / {END}")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    return f"{before}{START}\n{table}{END}{after}"


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    readme = root / "README.md"
    repo = os.environ.get("GITHUB_REPOSITORY", "YauhenBichel/py-harness")
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    people = list_people(repo, token)
    table = render_table(people)
    updated = apply_readme(readme.read_text(encoding="utf-8"), table)
    check = "--check" in sys.argv
    if updated == readme.read_text(encoding="utf-8"):
        print(f"README contributors already current ({len(people)} people)")
        return 0
    if check:
        print("README contributors are stale")
        return 1
    readme.write_text(updated, encoding="utf-8")
    print(f"wrote {len(people)} contributors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
