---
title: Folders
description: What each directory in this repository is. Start in demo/orders. Do not run brief on the repository root.
permalink: /tree/
date: 2026-09-06
---

# Folders

This repository is two things: a **sample project** and the **tool**
that works on it. Open the sample project first. Do not run `brief` on the
repository root — that scans hundreds of files.

## Start here

| Path | What it is |
| --- | --- |
| `demo/orders` | Sample app. Run `brief` / `ask` / `run` here. |
| `scripts/run/install.py` | Puts `python-vibe` on PATH. Then `source .venv/bin/activate`. |
| `docs/` | This site. |

```bash
source .venv/bin/activate
cd demo/orders
python-vibe brief
```

## The tool

| Path | What it is |
| --- | --- |
| `src/harness/` | The program. Layers, bottom-up. See [Architecture]({{ '/architecture/' | relative_url }}). |
| `tests/` | Unit tests. No GPU. |
| `skills/` | Short `Action:` templates the model can follow. |
| `editors/` | Task files for VS Code and Cursor. |

A module in `src/harness/` may import a layer below it, never one
above or beside it.

## Later

| Path | When you need it |
| --- | --- |
| `scripts/measure/` | Recordings, benches, `validate.py`. |
| `scripts/weights/` | Train and export. Apple Silicon. |
| `src/finetune/` | Training specs. Not daily work. |
| `data/` · `eval/` | Train pairs and test fixtures. |
| `adapters/` | Optional small-model files. Do not commit weights. |
| `docs/investigations/` | Every measured score. |

[Start]({{ '/start/' | relative_url }}) ·
[Architecture]({{ '/architecture/' | relative_url }}) ·
[Commands]({{ '/api/' | relative_url }}).
