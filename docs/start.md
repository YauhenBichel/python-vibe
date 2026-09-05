---
title: Start
description: Install python-vibe. Four commands in your project folder. Python 3.11+, Ollama, no graphics card.
permalink: /start/
date: 2026-08-29
---

# Start

Four steps. Most of the time is one download. No graphics card.

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
```

That creates `.venv` when you are not already in one, then
`pip install -e .`. Activate it (`source .venv/bin/activate`, or
`.venv\Scripts\Activate.ps1` on Windows) so `python-vibe` is on PATH.
Already in a venv: `pip install -e .` is the same install.

## 2. Check it works

No model yet. From **your** project folder:

```bash
python-vibe brief
```

You should see the project's size and a list of files.

## 3. Download the model (once)

```bash
ollama pull llama3.1:8b
```

## 4. Use it

```bash
python-vibe ask  "what does compute_total return?"
python-vibe run  "write tests for apply_discount"
python-vibe run  "find the NameError and fix it"
python-vibe run  "add a function total_lines and a test"
```

`ask` never changes a file. Daily `run` writes, then runs the suite; a
failing traceback is sent back to the model once. `find the NameError`
and `add a function total_lines` are harness demos on `demo/orders` —
unique typo and a template add, no model. `run` only touches that folder
and keeps a `.bak` of anything it edits. `python-vibe` with no arguments
reprints this list.

On a large project: `python-vibe run --scope src "write tests for apply_discount"`.

A GitHub PR-review CLI from one prompt aims at `list` and `show` on the
first `run`. Comment, pagination, and a config file are a later command,
not a higher `--steps`:

```bash
python-vibe run "add the comment subcommand and a mocked test"
```

After `scripts/run/install.py`, `python-vibe` is the command. From a
source checkout without that install: `PYTHONPATH=src python3 -m harness`.
One overflow prompt at a time, against the CLI project folder (not this
repo).

To try a change without writing: add `--dry-run`.

What those four commands did on one laptop:
[What you type]({{ '/scenarios/' | relative_url }}).
A typed session, with the real replies:
[Live]({{ '/live/' | relative_url }}).
The map of every score:
[Results]({{ '/investigations/' | relative_url }}).

## Later

- Last recorded turns: `python-vibe last`
- [Add to Cursor]({{ '/cursor/' | relative_url }}) — `python-vibe editors cursor --allow-writes`
- [Skills]({{ '/skills/' | relative_url }}) — picked from the wording of your task
- Tests for this repo: `python -m unittest discover -s tests -q`
- Tiny 0.5B sidecar (not daily work): see [research]({{ '/research-vibe-review/' | relative_url }})
