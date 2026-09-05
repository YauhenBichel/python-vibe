---
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-0.5B-Instruct
library_name: mlx
pipeline_tag: text-generation
tags:
  - mlx
  - lora
  - qwen2.5-coder
  - python
language:
  - en
---

# python-vibe-0.5b

LoRA adapters (step 100) on **Qwen2.5-Coder-0.5B-Instruct**, 4-bit MLX, for
short Python drafts. Hub repo:
[YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b).

**These weights are a style prior, not a coding agent.** They shape a short
note plus a fenced script. They do not plan, search a repository, or use tools.

The harness lives in
[github.com/YauhenBichel/python-vibe](https://github.com/YauhenBichel/python-vibe):
`PythonVibeGuard` (empty / leaked keys / `curl|sh` / wrong-surface diagnosis),
then one retry, then a fixed fallback. Optional local loop: extract a Python
block, write it, run it, send the traceback back once (`scripts/vibe.py --then`).

## What is in the adapters

- 45 hand-written pairs (35 / 5 / 5). Validation was best near step 100.
- LoRA on `self_attn.q_proj` and `self_attn.v_proj`, rank 8, scale 20, 12 layers.
- `adapters.safetensors` **is** step 100, not the last step. A longer run overfit.
- **Frozen.** Do not add train pairs for the 18 held-out scripts. The 5 Sep 2026
  pass@4 run lost to the untuned base (2/18 vs 6/18).

## Use (Mac / MLX)

```bash
hf download YauhenBichel/python-vibe-0.5b --local-dir adapters/python-vibe
```

```python
from mlx_lm import load, generate

model, tokenizer = load(
    "mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit",
    adapter_path="adapters/python-vibe",
)
```

Or from the git repo:

```bash
PYTHONPATH=src python scripts/vibe.py --engine mlx "weekday name for argv YYYY-MM-DD"
```

Linux / Windows without MLX: `ollama pull qwen2.5-coder:0.5b` and
`PYTHONPATH=src python scripts/serve.py` — that is the **base** coder plus the
harness, not these adapters.

For everyday work on a laptop, run an 8B (for example `llama3.1:8b`) through
the same harness. Keep this 0.5B for smoke tests and style.

## Eval

Held-out scripts, scored by running them (not HumanEval). Temperature 0
is greedy (pass@1). Temperature 0.7 with `--samples 4` is pass@k. On this
0.5B do not use temperature 1 unless every draft is executed.

```bash
PYTHONPATH=src python scripts/eval.py --variant base --repeats 3
PYTHONPATH=src python scripts/eval.py --variant all --repeats 3   # LoRA needs MLX
PYTHONPATH=src python scripts/eval.py --variant all --repeats 1 --samples 4 --temperature 0.7
```

Base weights: `Qwen/Qwen2.5-Coder-0.5B-Instruct` (Apache-2.0).
