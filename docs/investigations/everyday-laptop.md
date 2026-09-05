---
title: Everyday laptop
description: The 0.5B LoRA is not daily work. Comfortable explore / edit / run needs a larger local model, tool traces, and a write limit.
date: 2026-08-29
type: article
---

# Investigation: can python-vibe be everyday laptop work?

**Answer:** no — not this 0.5B LoRA. Comfortable daily explore / edit / run
needs a larger model, tool-use training, and a local editor connected to
Ollama.
Keep python-vibe-0.5b as a cheap draft + harness.

Related: [research-vibe-review](../research-vibe-review.md) ·
[local loop vs hosted agents](./local-vs-cloud.md) ·
[what to improve](./what-to-improve.md) · issues
[#8](https://github.com/YauhenBichel/python-vibe/issues/8),
[#9](https://github.com/YauhenBichel/python-vibe/issues/9).

## What everyday laptop work means

You open a repo and talk. The model explores, edits files, runs tests, and
keeps a short plan. That is comfortable daily work. The weights need to be
large enough to emit tool calls.

python-vibe today is a **400 MB style prior** plus scripts:

| Surface | What it does |
| --- | --- |
| `vibe.py` | One prompt → one small Python draft → `/run` |
| `batch_review.py` | One small file at a time, up to 100 |
| `agent.py` | Text protocol: map / plan / glob / grep / read / edit / patch / run / done |

The 0.5B model misses `Action:` lines. `agent.py` only feels daily-usable when
`--model` is something like `llama3.1:8b`.

## Measured gap

Held-out laptop tasks (LoRA + harness): weekday name, count `.md`, jsonl
reader, tiny docstring apply — **all failed** (wrong `main()`, month-as-
weekday, filtered the word `"bad"`, junk docstring). Base
`qwen2.5-coder:0.5b` failed the same class.

OpenSRE: 100 smallest first-party files (200–2500 bytes) → **100× “no
issues”**, 0 applied. That is not a review.

## What will not work

- More steps on the 0.5B run (already overfit after step 100).
- More short stdlib pairs only (issue #9: this is a style prior).
- Asking the 0.5B weights to plan a repo.

## What to do

1. **This week.** `scripts/run/agent.py` defaults to `llama3.1:8b`. Local editor:
   [local-editor.md](../local-editor.md). `scripts/run/openai_compat.py` proxies
   `/v1/chat/completions`. `scripts/weights/export_ollama.py --create` names
   `python-vibe-everyday`.
2. **Your model.** `scripts/weights/build_agent_data.py` writes seed tool traces
   (`data/agent-loop`). `scripts/weights/train.py --everyday` is the 7B-class LoRA.
   Append redacted explore / edit / run sessions before claiming 2k traces.
   Fuse/GGUF: `export_ollama.py --from-gguf`.
3. **Eval.** `scripts/measure/eval_everyday.py` (offline in CI). `--live` must beat
   untuned 8B on parse rate before anyone says everyday-ready.

0.5B stays public for download, CI, and the harness demo. It is not the
everyday brain.

## Shipped in this repo (laptop path)

- `scripts/run/agent.py` defaults to `llama3.1:8b`. `--tiny` is the sidecar.
- `scripts/run/openai_compat.py` + [local-editor.md](../local-editor.md) for a
  local OpenAI-compatible editor.
- Seed tool traces + `--record` → `data/agent-loop/extra.jsonl` (gitignored).
- `scripts/weights/train.py --everyday` (7B-class MLX). `export_ollama.py --create`
  names the stand-in; GGUF of *your* LoRA is `--from-gguf`.
- `scripts/measure/eval_everyday.py`: gold weekday + count-md `/run`, ≥1 KB NameError
  fixture, Action: parse fixtures. `--live` on this machine (29 Aug 2026):
  `llama3.1:8b` parsed **2 / 3** prompts (above the 50% floor). 5 September
  2026, same machine: harness parse **11 / 15** vs clean **0 / 15**; harness
  failed the ≥1 KB logic fix **0 / 3** (two writes were tests only). After
  #229 (same evening): parse **10 / 15** vs **0 / 15**; fix still **0 / 3**,
  writes `[]` × 3. After #238 (refuse explore): parse **11 / 15** vs
  **0 / 15**; fix still **0 / 3**, writes `[]` × 3, while a clean one-shot
  passed **3 / 3**. That is not everyday-ready. Replay:
  `PYTHONPATH=src python scripts/measure/eval_everyday_bar.py`.

Live `agent.py` + `llama3.1:8b` loops on this machine (29 Aug 2026):

1. NameError fixture copy: read → `Find: return tota` → tests OK → done (4 steps).
2. This repo: patched `scripts/run/agent.py` docstring to `python3.13`.
3. Failed: full-file `edit` wiped `tests/test_agent_tools.py` (20% length
   guard was too weak). Guard is now 2/3 of original; file restored by hand.
4. This repo: patched `resolve_project_file` to allow `.md`.
5. This repo: patched README agent example to `python3.13`.

The loop works on **scoped patch tasks**. It is comfortable daily work on
small, well-scoped jobs — not a full-repo rewrite.

## Small vs large (29 Aug 2026)

Same CLI, two briefs (no extra model):

- **Small** (≤40 first-party text files, ≤200 KB): inject the file list.
  Questions → read → `Action: done`. Bugs → patch → run. This is the
  everyday laptop path.
- **Large**: inject top-level counts, require `Action: map`, `--scope`,
  and truncated grep. Do not ask the 8B to read the whole tree.

`PYTHONPATH=src python3.13 scripts/run/agent.py --project /path/to/app --brief`
prints the mode without calling Ollama.
