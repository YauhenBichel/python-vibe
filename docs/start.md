---
title: Start
description: Install python-vibe on macOS, Linux or Windows. Everyday path is Ollama llama3.1:8b and the python-vibe command. Tests run with no GPU.
permalink: /start/
date: 2026-08-29
---

# Start

Four steps, about ten minutes, mostly waiting for one download.

There are two pieces. **Ollama** runs the AI model on your own machine; it
is free, and nothing you type leaves your computer. **python-vibe** is this
project: it reads your code, decides what the model is allowed to do, and
makes the changes safely.

You do not need a graphics card.

## You need

<ul class="need">
  <li>Python 3.11 or newer, on macOS, Linux or Windows</li>
  <li><a href="https://ollama.com" rel="noreferrer">Ollama</a>, free, plus about 5 GB of disk for the model it downloads</li>
  <li>A Python project of your own to try it on</li>
</ul>

## 1. Install

The same three commands on macOS, Linux and Windows. Nothing is compiled,
because python-vibe itself uses only what comes with Python.

```bash
git clone https://github.com/YauhenBichel/python-vibe.git
cd python-vibe
pip install -e .
```

## 2. Check it works

This needs no AI model at all, so you can run it straight away. Point it at
any Python project and it prints a summary:

```bash
python-vibe brief /path/to/your/project
```

You should see the project's size and a list of its files. If you see that,
the install worked.

## 3. Download the model

One download of about 5 GB. It only happens once.

```bash
ollama pull llama3.1:8b
```

## 4. Ask it something

```bash
python-vibe ask /path/to/your/project "what does compute_total return?"
```

`ask` never changes a file. When you are ready to let it make a change:

```bash
python-vibe run /path/to/your/project "find the NameError and fix it"
```

It only touches files inside the folder you named, and it keeps a copy of
anything it edits next to the original, ending in `.bak`. Add `--dry-run`
to see what it would do without letting it do anything.

On a large project, add `--scope src` so it works in one folder instead of
trying to read everything.

`python -m harness ...` does the same thing without the installed command.
`scripts/agent.py` still works from a source checkout, with `PYTHONPATH=src`
on macOS and Linux.

Training on Apple Silicon needs MLX, which does not install on Linux or
Windows, so it is a separate extra: `pip install -e ".[train]"`.

`--tiny` is the 0.5B sidecar. Do not use it for daily work.

The agent loads kit [skills]({{ '/skills/' | relative_url }}) from the wording
of the task (`add-feature`, `write-tests`, `answer-question`, and the rest),
or you pass `--skill`. `--brief` prints the pick with no model.

Add the same jail to Cursor in one command (defaults to this folder):

```bash
python-vibe editors cursor --allow-writes
```

Then reload the window and enable `python-vibe` under Customize → MCP.
Details: [Cursor]({{ '/cursor/' | relative_url }}) ·
[local editor]({{ '/local-editor/' | relative_url }}) ·
[IDE plugins]({{ '/ide-plugins/' | relative_url }}).

## Tests (no model)

After `pip install -e .`, on any platform:

```bash
python -m unittest discover -s tests -q
python scripts/validate.py
```

`validate.py` is what CI runs: the unit tests, the smoke check, then the
offline everyday gate. CI runs it on macOS, Linux and Windows across
Python 3.11 to 3.13.

Do not call the project everyday-ready until `scripts/eval_everyday.py --live` beats an untuned 8B on Action parse rate and a real ≥1 KB fix.

## GitHub account (co-author)

When python-vibe commits, **you** stay the author. The harness adds a
`Co-authored-by` trailer for the [python-vibe](https://github.com/python-vibe)
GitHub user so that account appears on the commit. Create it once (a person
has to sign up; the harness cannot):

1. Open [github.com/signup](https://github.com/signup).
2. Username: `python-vibe` (still unused as of 29 Aug 2026).
3. Use a mailbox you control. Verify the email.
4. Settings → Emails → keep the noreply address
   `python-vibe@users.noreply.github.com`.
5. Bio: point at [YauhenBichel/python-vibe](https://github.com/YauhenBichel/python-vibe).
   Do not give this user write access to other people’s repos. It is only
   for attribution.

Until that user exists, GitHub still stores the trailer but does not show
an avatar.

## Tiny sidecar (not daily work)

```bash
hf download YauhenBichel/python-vibe-0.5b --local-dir adapters/python-vibe
PYTHONPATH=src python3.13 scripts/vibe.py
```

Linux without MLX: `ollama pull qwen2.5-coder:0.5b` then `scripts/serve.py`. That path is the base coder plus the harness, not the LoRA.
