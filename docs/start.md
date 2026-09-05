---
title: Start
description: Install python-vibe. Four commands in your project folder. Python 3.11+, Ollama. You do not need a GPU.
permalink: /start/
date: 2026-09-06
---

# Start

Install the tool, then run four commands in a project folder. You do
not need a GPU.

## You need

<ul class="need">
  <li>Python 3.11 or newer, on macOS, Linux or Windows</li>
  <li><a href="https://ollama.com" rel="noreferrer">Ollama</a>, free, plus about 5 GB of disk for the model</li>
  <li>A Python project of your own</li>
</ul>

## 1. Install

```bash
git clone https://github.com/YauhenBichel/python-vibe.git
cd python-vibe
python3 scripts/run/install.py
source .venv/bin/activate
```

That creates `.venv` if you are not already in a virtualenv, then
`pip install -e .`. Activate it in **every new terminal**
(`source .venv/bin/activate`, or `.venv\Scripts\Activate.ps1` on
Windows) or the shell says `command not found: python-vibe`.
Already in a virtualenv: `pip install -e .` is the same install.

## 2. Check it works

No model yet. `demo/orders` is the sample project. Do not run `brief`
on the python-vibe repository root — that scans the whole tree.

```bash
cd demo/orders
python-vibe brief
```

From the repository root, without `cd`: `python-vibe brief demo/orders`.
You should see about 10 files and 2.9 KB.

## 3. Download the model (once)

```bash
ollama pull llama3.1:8b
```

## 4. Use it

Still in `demo/orders`, with the virtualenv active:

```bash
python-vibe ask  "what does compute_total return?"
python-vibe run  "write tests for apply_discount"
python-vibe run  "find the NameError and fix it"
python-vibe run  "add a function total_lines and a test"
```

`ask` does not change a file. `run` writes, then runs the tests. A
failing traceback is sent back to the model once. The NameError and
`total_lines` samples on `demo/orders` do not call a model. `run` only
touches that folder and keeps a `.bak` of each file it edits.
`python-vibe` with no arguments reprints this list.

On a large project: `python-vibe run --scope src "write tests for apply_discount"`.

To try a change without writing: add `--dry-run`.

Every flag: [Commands]({{ '/api/' | relative_url }}).
What those four commands did on one laptop:
[What you type]({{ '/scenarios/' | relative_url }}).
A recorded session: [Live]({{ '/live/' | relative_url }}).
Measured scores: [Results]({{ '/investigations/' | relative_url }}).

## Later

- Last recorded turns: `python-vibe last`
- [Add to VS Code]({{ '/vscode/' | relative_url }}) — `python-vibe editors vscode`
- [Add to Cursor]({{ '/cursor/' | relative_url }}) — `python-vibe editors cursor --allow-writes`
- [Folders]({{ '/tree/' | relative_url }}) — what each directory is
- Tests for this repository: `python -m unittest discover -s tests -q`
