---
title: This checkout
description: Three folders to open first. The rest of the tree is the tool, the site, or later work. Do not brief the checkout root.
permalink: /tree/
date: 2026-09-05
---

# This checkout

This repository is two things in one tree: a **small demo app** and the
**helper** that works on it. Open the demo. Do not run `brief` on the
checkout root — that briefs hundreds of files.

## Open these

| Path | What it is |
| --- | --- |
| `demo/orders` | Planted app. `brief` / `ask` / `run` go here. |
| `scripts/run/install.py` | Puts `python-vibe` on PATH. Then `source .venv/bin/activate`. |
| `docs/` | The site. Start, live recording, scores. |

```bash
source .venv/bin/activate
cd demo/orders
python-vibe brief
```

## The helper

| Path | What it is |
| --- | --- |
| `src/harness/` | The tool. Layers, bottom-up. See [Architecture]({{ '/architecture/' | relative_url }}). |
| `tests/` | Merge gate. No GPU. |
| `skills/` | Copy-paste `Action:` blocks the 8B can follow. |
| `editors/` | Drop-in tasks and MCP files. |

A module in `src/harness/` may import a layer below it, never one
above or beside it.

## Later

| Path | When you need it |
| --- | --- |
| `scripts/measure/` | Recordings, benches, `validate.py`. |
| `scripts/weights/` | Train / export. Apple Silicon. |
| `src/finetune/` | Specs and the Hub card. Not daily work. |
| `data/` · `eval/` | Train pairs and fixtures. |
| `adapters/` | Optional 0.5B files. Do not commit weights. |
| `docs/investigations/` | Every measured score. |

[Start]({{ '/start/' | relative_url }}) ·
[Architecture]({{ '/architecture/' | relative_url }}) ·
[Using]({{ '/api/' | relative_url }}).
