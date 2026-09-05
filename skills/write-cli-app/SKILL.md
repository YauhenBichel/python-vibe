---
name: write-cli-app
description: One argparse GitHub PR CLI in pkg/ with urllib. Use when the task is design or develop a CLI app that talks to GitHub. Do not use for weekday scripts.
---

stdlib urllib. Token from os.environ. argparse subcommands. No curl. No secrets.

Action: edit
Path: {{module}}
```python
import argparse
import json
import os
import urllib.request
from typing import Any


def list_pulls(owner: str, repository: str) -> list[dict[str, Any]]:
    token = os.environ["GITHUB_TOKEN"]
    url = f"https://api.github.com/repos/{owner}/{repository}/pulls"
    request = urllib.request.Request(
        url,
        headers={"authorization": f"Bearer {token}", "accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=10.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("json array required")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    listed = sub.add_parser("list")
    listed.add_argument("owner")
    listed.add_argument("repository")
    args = parser.parse_args()
    if args.command == "list":
        print(list_pulls(args.owner, args.repository))
```
