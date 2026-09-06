---
title: Local editor
description: Add py-harness to Cursor, VS Code, Continue, and Zed in one command. Tasks and a local MCP stay on this machine. Chat override of localhost is optional.
date: 2026-08-29
---

# Use py-harness from an editor

Three easy paths. All stay on `127.0.0.1` unless you choose otherwise.

| Path | One command | What you get |
| --- | --- | --- |
| Cursor (easiest) | `py-harness editors cursor --allow-writes` | MCP + tasks in this folder. Recorded walkthrough: [Cursor]({{ '/cursor/' | relative_url }}). |
| Editor tasks | `py-harness editors vscode` | Command Palette → Run Task → ask / run / brief. Uses the same **write limit**. Walkthrough: [VS Code]({{ '/vscode/' | relative_url }}). |
| Continue (VS Code) | `py-harness editors continue` | Chat uses local Ollama 8B. Uses the **editor’s** tools. |
| Zed | `py-harness editors zed` | Merges a `context_servers` entry into `.zed/settings.json`. Same write limit. |

`pip install py-harness-cli`, or from a clone
`python3 scripts/run/install.py` then `source .venv/bin/activate`, so
`py-harness` is on PATH (macOS often has no `pip`). Activate in every
new terminal or the shell says `command not found`. `--project`
defaults to the current folder. Files land in `.vscode/`, `.continue/`,
or `.cursor/` inside **your** app. This repo already ships
`.cursor/mcp.json`.

Drop-in sources: [`editors/`](https://github.com/YauhenBichel/py-harness/tree/HEAD/editors).

## 1. Pull the everyday brain

```bash
ollama pull llama3.1:8b
# or: ollama pull qwen2.5-coder:7b
# or: ollama pull qwen2.5-coder:14b
```

## 2. Easiest: tasks in the integrated terminal

```bash
py-harness editors vscode --project /path/to/your/app
```

Then Run Task and type a task, for example:

- `what does compute_total return?`
- `write a weekday script from argv`
- `fetch json from the HTTP API`
- `tally counts by key from a csv`
- `implement binary search`

The same `tasks.json` works in VS Code and in other editors that read `.vscode/tasks.json`.

## 3. OpenAI-compatible chat (brain only)

Ollama already exposes:

`http://127.0.0.1:11434/v1/chat/completions`

A localhost proxy that defaults to the everyday model (and warns if you pick 0.5B):

```bash
PYTHONPATH=src python scripts/run/openai_compat.py
# http://127.0.0.1:8081/v1/chat/completions
```

Or let the **write limit** apply to chat (writes off unless `--allow-writes`):

```bash
py-harness serve --project /path/to/your/app
# GET  http://127.0.0.1:8090/v1/models
# POST http://127.0.0.1:8090/v1/chat/completions
```

In the editor’s OpenAI-compatible settings:

- Base URL: `http://127.0.0.1:8081/v1` (proxy) or `http://127.0.0.1:8090/v1` (harness)
- API key: `ollama` (any non-empty string)
- Model: `llama3.1:8b`

Some hosted editors send the OpenAI request from a **remote** backend. Those cannot see `127.0.0.1`. Do not open a public tunnel to it. Use tasks or the local MCP instead.

## 4. Cursor / local MCP (write limit, no tunnel)

```bash
py-harness editors cursor --allow-writes
```

Cursor launches `python3 -m harness mcp --project ${workspaceFolder}`.
Tools: `ask` (read-only) and `run` (writes if you passed `--allow-writes`).
Stdout is JSON-RPC only. Step-by-step: [Cursor]({{ '/cursor/' | relative_url }}).

This is the editor calling py-harness. It is **not** an Action the 8B may emit.

## 5. CLI (same write limit, no editor)

```bash
py-harness run /path/to/your/app "write tests for apply_discount"
py-harness run /path/to/your/app --scope src "what does apply_source refuse?"
```

`--tiny` / `--engine mlx` is smoke only.

## What py-harness is good at

Kit skills for everyday laptop Python (stdlib, AAA tests):

| You say | Skill |
| --- | --- |
| write a weekday script / argparse / argv | `write-script` |
| fetch json / HTTP API / “like curl” | `call-http` (urllib only; never `curl\|sh`) |
| tally / group by / csv / analytics | `analyze-data` |
| binary search / stack / algorithm | `write-algorithm` |

Each write is followed by `write-tests` (`test_<unit>_<result>`, Act into `got`).

## Optional: a Hub GGUF that Ollama does not ship

OpenCoder 8B and SWE-agent-LM 7B are on Hugging Face, not in the Ollama
library. Import the Q4_K_M file, then pass `--model`:

```bash
python3 scripts/weights/import_hf_ollama.py --name opencoder
python3 scripts/weights/import_hf_ollama.py --name swe-agent-lm
py-harness --model opencoder:8b run "add a function clamp and a unit test"
```

Default stays `llama3.1:8b`. Detail:
[Hub models]({{ '/investigations/hub-models/' | relative_url }}).

## Optional: your LoRA as GGUF / Ollama

Stand-in (this week): `export_ollama.py --create` is `FROM llama3.1:8b` plus the
agent system prompt. That is **not** a trained python-vibe-8b.

After you fuse a 7B-class MLX adapter to a folder:

1. Convert with [llama.cpp](https://github.com/ggml-org/llama.cpp) `convert_hf_to_gguf.py` (not in this repo).
2. `PYTHONPATH=src python scripts/weights/export_ollama.py --from-gguf fused/everyday.gguf --create`

Do not call this everyday-ready until `scripts/measure/eval_everyday.py --live` beats
untuned 8B on Action: parse rate.
