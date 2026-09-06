---
title: Use py-harness in Cursor
description: A real recording. Install the local MCP, then brief, ask, and run from chat or Tasks. Same commands the tools execute, captured on demo/orders.
permalink: /cursor/
date: 2026-09-05
---

# Use py-harness in Cursor

Cursor talks to py-harness as a **local child process**. Your code stays
on this machine. You do not open a port and you do not point chat at
`127.0.0.1`.

This page is a live walkthrough on `demo/orders`. 5 September 2026.
`brief` needs no model. `ask` calls `llama3.1:8b`. The NameError repair
is a harness demo — no model.

![py-harness Cursor MCP on demo/orders]({{ '/media/cursor-demo.gif' | relative_url }})

Recorded with asciinema. The GIF is what chat and **Tasks: Run Task**
run after `py-harness editors cursor --allow-writes`, not a screenshot
of the editor window. Replay:

```bash
asciinema play docs/media/cursor-demo.cast
```

Re-record it (needs Ollama `llama3.1:8b`):

```bash
PYTHONPATH=src python scripts/measure/record_cursor.py
```

## One-time setup

From a clone (same installer as [Start]({{ '/start/' | relative_url }})):

```bash
python3 scripts/run/install.py
source .venv/bin/activate
ollama pull llama3.1:8b
py-harness editors cursor --allow-writes
```

macOS often has no `pip` on PATH. The installer creates `.venv` and
runs `python -m pip` for you. Activate that venv in every new terminal
or `py-harness` will still be missing.

Without installing, from the checkout:

```bash
PYTHONPATH=src python3 -m harness editors cursor --allow-writes
```

`--project` defaults to the folder you are in. The command writes two
files:

| File | What it is for |
| --- | --- |
| `.cursor/mcp.json` | Cursor starts `python3 -m harness mcp` itself |
| `.vscode/tasks.json` | Command Palette → Tasks: Run Task → `py-harness: ask` / `run` |

`${workspaceFolder}` is filled by Cursor, so the MCP file has **no
personal path**. You can commit it. Anyone who clones the repo and
reloads the window gets the same tools. The task file names the
interpreter that ran `editors cursor`. Do not commit that path.

## Then in Cursor

1. Command Palette → **Developer: Reload Window**
2. Open **Customize → MCP** and enable `py-harness`
3. In chat, say what you want. Name the tool if you like:
   - “ask py-harness what `compute_total` returns”
   - “run py-harness: write tests for apply_discount”
   - “run py-harness: find the NameError and fix it”

`ask` never writes. `run` writes only when you passed `--allow-writes`.

A large tree: add a scope (“stay in `src/`”). The write limit already
refuses to load the whole tree.

The same jobs are also **Tasks: Run Task** → `py-harness: brief` /
`ask` / `run`. Do not type `py-harness: ask` in the shell. The colon
is the task label. In a terminal the commands are:

```bash
source .venv/bin/activate
cd demo/orders
py-harness brief
py-harness ask  "what does compute_total return?"
py-harness run  "find the NameError and fix it"
```

If the shell says `command not found: py-harness`, the venv is not
active. Activate it in every new terminal.

## Live: this folder, those tools

Open `demo/orders` (or this repo and stay in that folder). Reload,
enable the server, then ask in chat. `editors`, `brief`, `ask`, and
the NameError `run` below are the GIF.

### `py-harness editors cursor --allow-writes`

Writes `.cursor/mcp.json` and `.vscode/tasks.json`. No model.

```
$ py-harness editors cursor --allow-writes
/private/tmp/cursor/.cursor/mcp.json
/private/tmp/cursor/.vscode/tasks.json

py-harness is set up for this folder (read-write).
1. ollama pull llama3.1:8b
2. Command Palette → Developer: Reload Window
3. Open Customize → MCP → enable py-harness
4. In chat: ask py-harness what compute_total returns
   or Tasks: Run Task → py-harness: ask
Do not point Override OpenAI Base URL at 127.0.0.1. That request often
leaves this machine.
```

### `py-harness brief`

No prompt. Instant. No model.

```
$ py-harness brief

10 Python and Markdown files, 2.9 KB in total.
Small enough that py-harness can read all of it, so you can ask about any part.

Files:
  README.md  685 B
  src/__init__.py  68 B
  src/orders.py  467 B
  src/orders_controller.py  568 B
  src/orders_service.py  285 B
  src/render.py  193 B
  src/report.py  155 B
  src/util.py  67 B
  tests/__init__.py  0 B
  tests/test_orders.py  511 B

py-harness has 24 skills it can apply. It picks them from the wording of
your task; you do not choose them.
```

### `py-harness ask`

Type: `what does compute_total return?`

Needs the 8B. About fifteen seconds on this run. The first draft was
only `int`. The helper sent that back. The second draft named what
the function computes.

```
$ py-harness ask "what does compute_total return?"
ollama:llama3.1:8b  project /private/tmp/cursor  mode small

--- step 1 ---
Action: done
Summary: "int"

too thin. Action: done Summary: quote int and say in a sentence what it
computes, from the code you read.

--- step 2 ---
Action: done
Summary: The `compute_total` function computes the sum of the line
prices of one order, returning an integer value.

The `compute_total` function computes the sum of the line prices of one
order, returning an integer value.
```

`ask` never writes a file.

### `py-harness run`

Type: `find the NameError and fix it`

The planted typo is `subtotl` next to `subtotal =`. One candidate. No
model. About a tenth of a second.

```
$ py-harness run "find the NameError and fix it"

bound unique NameError typo (subtotl → subtotal) in src/orders.py. Tests passed.
```

`run` writes only with `--allow-writes` on the server, or when you use
the task (a real `py-harness run` in the project folder). It keeps a
`.bak` of anything it edits.

## Every workspace on this laptop

```bash
py-harness editors cursor --global --allow-writes
```

Merges `py-harness` into `~/.cursor/mcp.json`. Other servers stay.
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

Related: [In your editor]({{ '/editor-demos/' | relative_url }}) ·
[VS Code]({{ '/vscode/' | relative_url }}) ·
[local editor]({{ '/local-editor/' | relative_url }}) ·
[IDE plugins]({{ '/ide-plugins/' | relative_url }}) ·
[Live demo (shell)]({{ '/live/' | relative_url }}).
