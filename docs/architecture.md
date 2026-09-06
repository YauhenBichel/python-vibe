---
title: Architecture
description: Bottom-up harness layers for py-harness. A module may import only a strictly lower layer. The merge gate enforces the rule.
date: 2026-08-29
---

# Architecture

The folders in this repository are listed on
[Folders]({{ '/tree/' | relative_url }}). This page is only `src/harness/`.

`src/harness/` is ordered bottom-up. **A module may import a layer strictly
below it, never one above or beside it.** That rule is enforced by
`tests/whole/test_architecture.py`, so a refactor that rots fails the merge gate
rather than the next reader.

```
cli.py       commands                    run, serve, mcp, editors
server.py    HTTP on 127.0.0.1           /v1/ask, /v1/chat/completions
mcp_stdio    editor child process        JSON-RPC on stdin/stdout
observe/     what a run leaves behind    trace_record, report_md, eval_gate
locate.py    find the symbol before acting
act/         intent becomes a change     parse, tools, gate, patch_fix, code
skillkit/    the skill kit               catalog, target, refuse_change, refuse_finish
scan/        facts about a tree          project_brief, repo_map, layout
guard/       what ships, what is refused python_vibe, run, types
editor_kit   copy drop-in editor files
task.py      what the user asked for     (leaf)
paths.py     where this repo is on disk  (leaf)
model/       talking to weights          engine, ollama_generate, openai_compat
ship/        git and PR helpers          git_ship
```

Read a layer top-down and you learn what the harness does. Read it
bottom-up and you learn what it refuses. The kit skills `skillkit/` loads
are listed on [Skills]({{ '/skills/' | relative_url }}).

## What a run remembers

`memory/` is one component with one job: decide what a request carries.

It was a bare list on the generate function. Every turn appended the
prompt and the reply, nothing was ever removed, and the request grew by
about 130 tokens a turn on top of an opening usually over a thousand.
Nobody decided where that stopped: the harness sent no context size, so
Ollama applied its own default of 4096 tokens — for weights that accept
131072 — and dropped the oldest messages once a run passed it.

The oldest message is the opening, which carries the file the harness
located and the instruction about it. A long run lost exactly the part
the harness had done work to assemble, and nothing said so.

`Conversation` decides instead. The opening is kept for the whole run.
Recent turns are kept, because that is where the run is. What goes is
the middle, which is where a model has already been told four times that
it used the wrong verb, and it is counted rather than silently dropped.
The context size is now stated in the request.

It belongs to the harness, not the model package: what is worth
remembering is a harness decision. `make_generate` is handed something
that answers `messages(prompt)` and never imports it.

## Three rings

An agent is a harness around a model. That is the shape the code keeps.

{% include diagram-rings.html %}

Nearly all of the behaviour is the middle ring, which is the point of the
project: what the model gets wrong, the harness catches.

The outer ring does not reach into the inner one. The command line and
the server used to import `harness.model` directly, so the model package
could not change shape without changing them. They go through the
harness now, and a test refuses the direct import.

`openai_api` used to sit in the model package. It knows what an
OpenAI-style chat request looks like and nothing about weights, so it
belongs beside the server that speaks that format. The model package is
now only the code that talks to a model, and a test keeps it that way.

What one run does before it loads a model:

{% include diagram-run.html %}

One place asks for a generator, `agent/loop.py`, and a test checks that
too. If a second appeared, there would be two answers to "which model is
this run using".

## Why `task.py` is the bottom

Every layer needs to know whether the user asked a question or asked for a
change. Before, whichever module needed a predicate first owned it, so
`project_brief`, `skills`, and `style` imported each other in a circle,
broken only by function-local imports that hid the cycle from every reader.

Pulling the predicates into one leaf removed all three cycles. One rule
holds the set together: **a question is never a write** — every
`looks_like_*` writer predicate returns `False` for a question.

## Why `guard/` cannot import `act/`

`guard/` is the safety boundary. If it could import a layer that writes
files, a refusal could be routed around by whatever it imported. The rule
is a test (`test_the_guard_layer_cannot_write`), not a convention.

## Why nothing counts `parents[N]`

A module that resolves the repo root by counting parent directories breaks
silently the moment it moves into a layer. `harness/paths.py` resolves it
once; `test_no_module_counts_its_own_depth` keeps it that way.

## The same check, pointed at your project

`Action: layout` runs `harness/scan/layout.py` against the tree in front of
the agent and reports the same four things, worst first, then names **one**
move:

| Finding | What it means |
| --- | --- |
| `cycle` | two modules import each other; neither can be read alone |
| `flat` | one package holding many modules with no grouping |
| `god` | one module far larger than its neighbours |
| `no-tests` | code with no `test_*.py` anywhere |

```bash
PYTHONPATH=src python3.13 scripts/run/agent.py --project /path/to/your/app \
  --skill readable-layout "why is this project hard to follow?"
```

One move per turn is deliberate. Handed four findings an 8B rewrites the
tree; handed one it does the one.
