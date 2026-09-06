---
title: Start
description: Install py-harness. Four commands in your project folder. Python 3.11+, Ollama. You do not need a GPU.
permalink: /start/
date: 2026-09-06
---

# Start

Install the tool, then run four commands in a project folder. You do
not need a GPU.

## You need

<ul class="need">
  <li>Python 3.11 or newer, on macOS, Linux or Windows. Check with <code>python3 --version</code>. macOS <code>/usr/bin/python3</code> is often 3.9 and cannot install this package</li>
  <li>A folder to point at — yours, or the sample below</li>
  <li><a href="https://ollama.com" rel="noreferrer">Ollama</a> later, for <code>ask</code> and daily <code>run</code> (about 5 GB). <code>brief</code> and the NameError sample do not need it</li>
</ul>

## 1. Install

Usual path — PyPI. The command is `py-harness`. The package name is
`py-harness-cli` because `py-harness` collides with another project.
Do not `pip install py-harness` or `pip install pyharness`.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install py-harness-cli
```

Activate that virtualenv in **every new terminal**
(`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` on
Windows) or the shell says `command not found: py-harness`.

From a clone (sample project, editable install, training extras):

```bash
git clone https://github.com/YauhenBichel/py-harness.git
cd py-harness
python3 scripts/run/install.py
source .venv/bin/activate
```

That creates `.venv` if you are not already in a virtualenv, then
`pip install -e .`. Already in a virtualenv: `pip install -e .` is
the same install.

## 2. Check it works

No model yet. Your own project, from that folder:

```bash
py-harness brief
```

Or `py-harness brief ~/app`. A missing folder is refused. The sample
needs a clone — `pip install` does not download `demo/orders`. Do not
`brief` the repository root.

```bash
git clone https://github.com/YauhenBichel/py-harness.git
cd py-harness/demo/orders
py-harness brief
py-harness run "find the NameError and fix it"
```

You should see about 10 files, then the `subtotl` typo bound. From a
clone root, without `cd`: `py-harness brief demo/orders`.

## 3. Download the model (once)

```bash
ollama pull llama3.1:8b
```

## 4. Use it

Still in `demo/orders`, with the virtualenv active:

```bash
py-harness ask  "what does compute_total return?"
py-harness run  "write tests for apply_discount"
py-harness run  "find the NameError and fix it"
py-harness run  "add a function total_lines and a test"
```

`ask` does not change a file. `run` writes, then runs the tests. A
failing traceback is sent back to the model once. The NameError and
`total_lines` samples on `demo/orders` do not call a model. `run` only
touches that folder and keeps a `.bak` of each file it edits.
`py-harness` with no arguments reprints this list.

On a large project: `py-harness run --scope src "write tests for apply_discount"`.

To try a change without writing: add `--dry-run`.

Every flag: [Commands]({{ '/api/' | relative_url }}).
What those four commands did on one laptop:
[What you type]({{ '/scenarios/' | relative_url }}).
A recorded session: [Live]({{ '/live/' | relative_url }}).
Measured scores: [Results]({{ '/investigations/' | relative_url }}).

## Later

- Last recorded turns: `py-harness last`
- [Add to VS Code]({{ '/vscode/' | relative_url }}) — `py-harness editors vscode`
- [Add to Cursor]({{ '/cursor/' | relative_url }}) — `py-harness editors cursor --allow-writes`
- [Folders]({{ '/tree/' | relative_url }}) — what each directory is
- Tests for this repository: `python -m unittest discover -s tests -q`
