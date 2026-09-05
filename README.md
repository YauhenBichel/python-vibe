# python-vibe

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE)
[![CI](https://github.com/YauhenBichel/python-vibe/actions/workflows/ci.yml/badge.svg)](https://github.com/YauhenBichel/python-vibe/actions/workflows/ci.yml)

LoRA on **Qwen2.5-Coder-0.5B** (~400 MB 4-bit) for short Python vibe-coding answers,
plus a tiny `PythonVibeGuard` sidecar. The 0.5B is a **style prior**. The harness
is what decides whether a draft ships.

Weights: [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b).
Skin-health Q&A is a separate repo: [MoleCare/skincare-qa](https://github.com/MoleCare/skincare-qa).

```
client → harness :8080 → ollama qwen2.5-coder:0.5b
              ↓
     pass / revise / block
     block twice → fixed fallback
```

The harness blocks empty drafts, leaked keys, `curl|sh`, and lesion diagnosis
(wrong surface). It does not rewrite style.

Everyday local work: an 8B through the same harness. This 0.5B is for smoke
tests and short single-file drafts.

## Train (Mac / MLX 3.13)

```bash
cd ~/DevBox/python-vibe
/opt/homebrew/bin/python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python scripts/build_data.py
PYTHONPATH=src python scripts/train.py
```

## Serve

```bash
ollama pull qwen2.5-coder:0.5b
PYTHONPATH=src python scripts/serve.py
PYTHONPATH=src python -m unittest discover -s tests -q
```

```bash
curl -s localhost:8080/health
curl -s localhost:8080/v1/python-vibe \
  -H 'content-type: application/json' \
  -d '{"prompt":"jsonl reader that skips bad lines"}'
```

```bash
PYTHONPATH=src python scripts/chat.py "write a jsonl reader"
PYTHONPATH=src python scripts/vibe.py --run "weekday name for argv YYYY-MM-DD" -- 2026-08-29
```

`scripts/vibe.py` can use the step-100 LoRA on MLX (`--engine mlx`) or the
Ollama base (`--engine ollama`). `--then` runs the draft and sends the
traceback back once.

## Eval

18 held-out tasks, scored by executing the extracted script. Repeat each task
three times for pass@1 stability. `--samples 4 --temperature 0.7` is pass@k
(first draft that runs). LoRA variants need MLX.

Temperature is how randomly the next token is picked, not how smart the
model is. **0** is greedy (almost the same draft every time) — use it for
pass@1 and for a run you will trust. **0.7** is the Qwen chat default —
use it with `--samples` so the four drafts can differ. **1** is only
useful if you execute every draft and keep the one that runs; on this
0.5B it mostly invents APIs. `--samples 4` at temperature 0 is a waste.

```bash
# product default on the 0.5B: base + samples + one repair
PYTHONPATH=src python scripts/eval.py --variant base-repair --repeats 1 --samples 4 --temperature 0.7
# greedy pass@1 grid (LoRA needs MLX)
PYTHONPATH=src python scripts/eval.py --variant all --repeats 3 --temperature 0
PYTHONPATH=src python scripts/eval.py --variant all --repeats 1 --samples 4 --temperature 0.7
```

`scripts/vibe.py` defaults to the **base** 0.5B. Pass `--lora` only for style
smoke. `--then` can take a one-line hint from `llama3.1:8b` if Ollama is up.

Temperature 0 vs 1:
[Glossary](https://yauhenbichel.github.io/python-vibe/glossary/).

CI does not call a model. It checks the guard, path jail, and that each
reference script passes its own checker.

## Hugging Face

```bash
hf auth login
PYTHONPATH=src python scripts/init_hf_repos.py
PYTHONPATH=src python scripts/fuse_and_export.py python-vibe --hf
```
