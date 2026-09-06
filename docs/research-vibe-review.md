---
title: 0.5B vibe review
description: Held-out laptop vibe tasks failed. A 100-file stub walk returned no issues. The 0.5B LoRA is a style prior, not a reviewer.
date: 2026-08-29
type: article
---

# Research: can a 0.5B LoRA vibe-code and review a real repo?

**Weights:** [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b)
(step-100 adapters, public). **Code:** this repo. Related issues:
[#8](https://github.com/YauhenBichel/py-harness/issues/8) (guard evasion),
[#9](https://github.com/YauhenBichel/py-harness/issues/9) (45 pairs vs style prior),
discussion [eval protocol](https://github.com/YauhenBichel/py-harness/discussions/13).

The harness stays deterministic. This note is measurement and product shape,
not a second LLM on the serve path.

## What we trained

- Base: `Qwen2.5-Coder-0.5B-Instruct` (4-bit MLX), ~45 short (user, assistant) pairs.
- A 400-iter QLoRA run **overfit after ~step 100** (val ~0.91, then worse at 400).
- Hub `adapters.safetensors` **is step 100**, not the last checkpoint.
- `PythonVibeGuard` only blocks empty drafts, leaked key prefixes, `curl|sh`,
  lesion text, and >8000 chars. It does not fix wrong Python.

## Held-out laptop vibe coding

`scripts/run/vibe.py` generates through the guard, writes `scratch/last.py`, `/run`
executes it, `--then` sends the traceback back once.

| Task | Result |
| --- | --- |
| Weekday name for `2026-08-29` | Called missing `main()`, or used **month** as a weekday index |
| Count `.md` files | Missing `main()` / missing `Path` import / `rglob(".md")` instead of `*.md` |
| Same jsonl prompt as training | Filtered the word `"bad"`, not `json.loads` |
| Tiny `greet()` docstring apply | Wrote `"""hi {name}"""` — applied, but junk |

Ollama `qwen2.5-coder:0.5b` (no LoRA) failed the same class of bugs. The adapter
is a thin style prior, not a pair that finishes a new script in one shot.

## Reviewing a real project (OpenSRE)

A large first-party Python repo (thousands of files) does not fit. The 0.5B
window holds **one small `.py` file** (~200–2500 bytes).

- `scripts/measure/review.py` — one file, review-only by default; `--fix` writes a `.bak`.
- `scripts/run/vibe.py --project DIR --file path.py --review` — same, interactive `/apply`.
- Safety: writes stay under `--project`; skip `.git` / `.venv`; refuse a rewrite
  shorter than ~20% of the original.

A review of `tools/system/fleet_monitoring/provider_ids.py` returned **no issues**
(that file is clean). Nothing was written.

A naive “smallest 100 files” scan hit empty `__init__.py` and `config/.venv`
packages. `list_small_py_files` now skips `.venv` / `site-packages` and files
under 200 bytes. That yields **100 first-party files** in the 200–2500 byte band.

## Batch: 100 files without reloading MLX

`scripts/measure/batch_review.py` loads the LoRA **once**, then walks `--limit` files
(default 100):

1. Review each file (no rewrite).
2. If `--fix` and the review is not `no issues`, request a full-file rewrite
   and `apply_source` (or skip on a missing fence / tiny overwrite).
3. Append one JSON line per file to `scratch/batch-review.jsonl`.

This is a loop, not a repo agent. A 100-file `--fix` on OpenSRE **will invent
edits**. Run review first; read the report; then `--fix` only if you accept that.

```bash
PYTHONPATH=src python scripts/measure/batch_review.py \
  --project /path/to/your/app \
  --limit 100
```

## What we shipped in code (this change set)

- Public Hub adapters + `hf download` / `ensure_adapters` (no login to pull).
- `scripts/run/vibe.py` — REPL, `/run`, `--then`, `--project` / `--file` / `--apply` / `--review`.
- `scripts/measure/review.py` — one-file OpenSRE-oriented entry.
- `scripts/measure/batch_review.py` + `harness/project_scan.py` + `harness/engine.py`
  (one load, many files).
- `harness/code.py` — extract fence, run, path check, `.bak`, tiny-overwrite guard.
- Contributor kit (templates, SECURITY, CoC) and tests for extract / scan / Hub card.

## What we did not claim

- The LoRA is not a drop-in OpenSRE reviewer or a full-repo daily agent.
- Serve-on-AWS / GGUF of the LoRA is still a separate path (Linux serve today is
  Ollama **base** + harness).
- We did not run a 100-file `--fix` against OpenSRE.

## Useful next measurements

- Held-out `/run` pass rate at 20 / 100 / 400 iters vs base Ollama (issue #9).
- Guard precision/recall on paraphrases (issue #8).
- After more complete `__main__` training pairs: repeat the weekday / count-md /
  OpenSRE one-file apply tasks and publish the jsonl.
