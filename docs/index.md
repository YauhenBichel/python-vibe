---
title: A local tool for one Python folder
description: A command-line tool for one Python project. Ask a question, write a test, fix a bug, or add a small function. Files stay in the folder you name.
date: 2026-09-06
---

<div class="hero">
<h1>A local tool for one Python folder</h1>
<p><code>python-vibe</code> is a command-line tool. You point it at <strong>one Python project</strong>. It can answer a question, write a unit test, fix a failing test, or add a small function. It only reads and writes files in that folder.</p>
<p class="cta"><a href="{{ '/start/' | relative_url }}">Install</a> <a href="{{ '/live/' | relative_url }}">See a demo</a></p>
</div>

## Commands

<div class="cards">
<article class="card"><p class="card-k"><code>brief</code></p><p>Lists the files in the folder. No model needed.</p></article>
<article class="card"><p class="card-k"><code>ask</code></p><p>Answers a question. Does not change files.</p></article>
<article class="card"><p class="card-k"><code>run</code></p><p>Changes files, then runs the tests.</p></article>
</div>

## Try it

`demo/orders` is the sample project. Activate the virtualenv first
(`source .venv/bin/activate`). If the shell says `command not found`,
the virtualenv is not active.

```bash
source .venv/bin/activate
cd demo/orders
python-vibe brief
python-vibe ask  "what does compute_total return?"
python-vibe run  "write tests for apply_discount"
python-vibe run  "find the NameError and fix it"
python-vibe run  "add a function total_lines and a test"
```

Do not run `brief` on the python-vibe repository root. That scans
hundreds of files. Another project:

`python-vibe ask ~/app "what does add return?"`.

On a large project add `--scope src`. Full install steps:
[Start]({{ '/start/' | relative_url }}).

## This site

| Page | What is on it |
| --- | --- |
| [Start]({{ '/start/' | relative_url }}) | Install, then the four commands |
| [Commands]({{ '/api/' | relative_url }}) | Every flag, the Python API, and the local HTTP server |
| [Live]({{ '/live/' | relative_url }}) | A recorded session |
| [Demo]({{ '/demo/' | relative_url }}) | Eleven sample tasks and what happened |
| [Folders]({{ '/tree/' | relative_url }}) | What each directory in this repository is |
| [Editors]({{ '/editor-demos/' | relative_url }}) | VS Code and Cursor |
| [Results]({{ '/investigations/' | relative_url }}) | Measured scores |
| [References]({{ '/references/' | relative_url }}) | Papers the design sits on |
| [Architecture]({{ '/architecture/' | relative_url }}) | How `src/harness/` is layered |

## Limits

It does not browse the web or run arbitrary shell commands. `run` keeps
a `.bak` of each file it edits. The NameError and `total_lines` samples
on `demo/orders` are built into the tool; they do not call a model.
