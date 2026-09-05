---
title: Use python-vibe in Cursor
description: Three commands to add the python-vibe write limit to Cursor. Local MCP, no tunnel, no Override OpenAI Base URL.
permalink: /cursor/
date: 2026-08-29
---

# Use python-vibe in Cursor

Cursor talks to python-vibe as a **local child process**. Your code stays
on this machine. You do not open a port and you do not point chat at
`127.0.0.1`.

## Three commands

From a clone, or after `pip install python-vibe`:

```bash
pip install -e .
ollama pull llama3.1:8b
python-vibe editors cursor --allow-writes
```

`--project` defaults to the folder you are in. The command writes two
files and prints the next clicks:

| File | What it is for |
| --- | --- |
| `.cursor/mcp.json` | Cursor starts `python3 -m harness mcp` itself |
| `.vscode/tasks.json` | Command Palette → Tasks: Run Task → `python-vibe: ask` / `run` |

`${workspaceFolder}` is filled by Cursor, so the MCP file has **no
personal path**. You can commit it. Anyone who clones the repo and
reloads the window gets the same tools.

## Then in Cursor

1. Command Palette → **Developer: Reload Window**
2. Open **Customize → MCP** and enable `python-vibe`
3. In chat, say what you want. Name the tool if you like:
   - “ask python-vibe what `compute_total` returns”
   - “run python-vibe: write tests for apply_discount”
   - “run python-vibe: fix compute_total so it sums the rows”

`ask` never writes. `run` writes only when you passed `--allow-writes`.

A large tree: add a scope (“stay in `src/`”). The write limit already refuses
to load the whole tree.

## Every workspace on this laptop

```bash
python-vibe editors cursor --global --allow-writes
```

Merges `python-vibe` into `~/.cursor/mcp.json`. Other servers stay.
Each window limits changes to **the folder you have open**.

## Clone this repo

This repository already ships `.cursor/mcp.json`. Open the folder in
Cursor, reload, enable the server. No extra command.

## What not to do

Do not set **Models → Override OpenAI Base URL** to
`http://127.0.0.1:8081/v1` or `:8090`. Many Cursor builds send that
request from a remote backend, which cannot see your loopback. A public
HTTPS tunnel would let the internet reach it.

Use MCP or **Run Task**. Both stay on this machine.

Related: [local editor]({{ '/local-editor/' | relative_url }}) ·
[IDE plugins]({{ '/ide-plugins/' | relative_url }}) ·
[Using python-vibe]({{ '/api/' | relative_url }}).
