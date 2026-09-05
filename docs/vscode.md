---
title: Use python-vibe in VS Code
description: A real recording. Install the tasks, then brief, ask, and run from the Command Palette. Same commands the tasks execute, captured on demo/orders.
permalink: /vscode/
date: 2026-09-05
---

# Use python-vibe in VS Code

VS Code talks to python-vibe through **Tasks**. Each task opens the
integrated terminal, runs the same command as [Start]({{ '/start/' | relative_url }}),
and stays inside the folder you have open. There is no chat plugin to
install and no tunnel.

This page is a live walkthrough on `demo/orders`. 5 September 2026.
`brief` needs no model. `ask` calls `llama3.1:8b`. The NameError repair
is a harness demo — no model.

![python-vibe VS Code tasks on demo/orders]({{ '/media/vscode-demo.gif' | relative_url }})

Recorded with asciinema. The GIF is what **Tasks: Run Task** runs in
the integrated terminal, not a screenshot of the editor window. Replay:

```bash
asciinema play docs/media/vscode-demo.cast
```

Re-record it (needs Ollama `llama3.1:8b`):

```bash
PYTHONPATH=src python scripts/measure/record_vscode.py
```

## One-time setup

From a clone (same installer as [Start]({{ '/start/' | relative_url }})):

```bash
python3 scripts/run/install.py
source .venv/bin/activate
ollama pull llama3.1:8b
python-vibe editors vscode
```

macOS often has no `pip` on PATH. The installer creates `.venv` and
runs `python -m pip` for you. Activate that venv in every new terminal
or `python-vibe` will still be missing.

Without installing, from the checkout:

```bash
PYTHONPATH=src python3 -m harness editors vscode
```

`--project` defaults to the folder you are in. The command writes
`.vscode/tasks.json`. `${workspaceFolder}` is filled by VS Code, so the
file has no personal path. You can commit it.

Open that folder in VS Code. If the window was already open:

1. Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`)
2. **Developer: Reload Window**

## Then in VS Code

1. Command Palette → **Tasks: Run Task**
2. Pick one of:
   - `python-vibe: brief`
   - `python-vibe: ask`
   - `python-vibe: run`
3. For **ask** and **run**, type the job in the box. The default in the
   box is `add multiply(a, b) and a unit test`. Replace it.

The answer appears in the **Terminal** panel. That is the whole demo.

Do not type `python-vibe: ask` in the shell. The colon is the **task
label** in the Command Palette. In a terminal the commands are:

```bash
python-vibe brief
python-vibe ask  "what does compute_total return?"
python-vibe run  "find the NameError and fix it"
```

`layout` is not a task. In the same terminal:

```bash
python-vibe layout
```

## Live: this folder, those tasks

Open `demo/orders` (or this repo and stay in that folder). Run Task.
`editors`, `brief`, `ask`, and the NameError `run` below are the GIF.
`layout` and the already-covered test are the same folder, not on the
recording.

### `python-vibe editors vscode`

Writes `.vscode/tasks.json`. No model.

```
$ python-vibe editors vscode
/private/tmp/vscode/.vscode/tasks.json

Reload the window, then Command Palette → Tasks: Run Task → python-vibe: ask
```

### `python-vibe: brief`

No prompt. Instant. No model.

```
$ python-vibe brief

10 Python and Markdown files, 2.9 KB in total.
Small enough that python-vibe can read all of it, so you can ask about any part.

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

python-vibe has 24 skills it can apply. It picks them from the wording of
your task; you do not choose them.
```

### `python-vibe layout` (terminal)

```
layout: 1 finding(s), worst first.
  [cycle] src/render.py and src/report.py import each other

Next move (do only this one): Move what they share into a new
module both import.
```

Also instant, also no model. That cycle is in the tree:
`render.py` imports `build_report`, `report.py` imports `render_line`.

### `python-vibe: ask`

Type: `what does compute_total return?`

Needs the 8B. About half a minute on this run. The first draft was
only `int`. The helper sent that back. The second draft named what
the function computes.

```
$ python-vibe ask "what does compute_total return?"
ollama:llama3.1:8b  project /private/tmp/vscode  mode small

--- step 1 ---
Action: done
Summary: “int”

too thin. Action: done Summary: quote int and say in a sentence what it
computes, from the code you read.

--- step 2 ---
Action: done
Summary: "int" - it computes the sum of the line prices of one order.

"int" - it computes the sum of the line prices of one order.
```

`ask` never writes a file.

### `python-vibe: run`

Type: `write tests for apply_discount`

The test is already there. Nothing is written. Suite stays green.

```
already has a test for apply_discount
```

Type: `find the NameError and fix it`

The planted typo is `subtotl` next to `subtotal =`. One candidate. No
model. About a tenth of a second.

```
$ python-vibe run "find the NameError and fix it"

bound unique NameError typo (subtotl → subtotal) in src/orders.py. Tests passed.
```

`run` only writes when you pass `--allow-writes` to a server, or when
you use the task (the task is a real `python-vibe run` in the project
folder, so it may write). It keeps a `.bak` of anything it edits.

## What to reach for

| Task | Needs a model? | When it is worth it |
| --- | --- | --- |
| `brief` | No | First look at a folder |
| `layout` | No | One next move, not a punch list |
| `ask` | Yes | A named function |
| `run` | Only if the harness cannot do it | Unique NameError, already-covered test, add a count next to `prices` |

For jobs the model has to reason about, read
[Experiments]({{ '/investigations/experiments/' | relative_url }}) first.

## Optional: chat through Continue

```bash
python-vibe editors continue
```

That writes a Continue config aimed at local Ollama. Chat then uses the
**editor’s** tools, not the python-vibe write limit. For a change that
must stay in one folder, use **Run Task**.

Do not point a hosted OpenAI-compatible chat at `127.0.0.1`. That
request often leaves the machine. Tasks stay here.

Related: [In your editor]({{ '/editor-demos/' | relative_url }}) ·
[local editor]({{ '/local-editor/' | relative_url }}) ·
[IDE plugins]({{ '/ide-plugins/' | relative_url }}) ·
[Live demo (shell)]({{ '/live/' | relative_url }}).
