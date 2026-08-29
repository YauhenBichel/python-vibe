---
title: Cloud weights
description: How to try a larger model or a later LoRA without leaving the python-vibe jail. Inference moves to a GPU box. The harness stays on the laptop.
permalink: /investigations/cloud-weights/
date: 2026-08-29
type: article
---

# Cloud weights

**Question.** The laptop 8B is the everyday brain. A 30B timed out here.
How do we experiment with a stronger model, or a later fine-tune, without
dropping the jail or training the 0.5B again?

**Answer.** Keep the harness on the laptop. Move **only the generate
call** to a GPU you rent. Same `Action:` schema, same oracles, same
`demo/orders` checks. Do not train on the 30 seed traces, locally or in
the cloud. Publish new adapters only on [YauhenBichel](https://huggingface.co/YauhenBichel).

Related: [Experiments]({{ '/investigations/experiments/' | relative_url }})
· [fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }})
· [which model]({{ '/investigations/which-model/' | relative_url }})
· [hub models]({{ '/investigations/hub-models/' | relative_url }})
· [local loop vs hosted agents]({{ '/investigations/local-vs-cloud/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#what-stays-local">What stays local</a></li>
  <li><a href="#two-ways-to-reach-a-gpu">Two ways to reach a GPU</a></li>
  <li><a href="#the-experiment">The experiment</a></li>
  <li><a href="#fine-tune-later-on-that-same-gpu">Fine-tune later, on that same GPU</a></li>
  <li><a href="#do-not">Do not</a></li>
</ol>
</nav>

## What stays local

`python-vibe` still reads and writes only inside `--project`. `serve.py`
still binds **127.0.0.1**. Every file the run writes is written here, by
this machine.

What does travel is the prompt, and the prompt contains code. The harness
opens the file the task names and puts it in the first turn, and a later
`read` or `grep` sends what it found. Asked to fix
`src/billing.py`, the first request carried the whole of that file —
constants, comments and all. The cloud box is not given the working tree,
but it is given whatever the run reads out of it. Point it at a host you
would show that code to.

A bigger remote model does not become a hosted IDE agent. There is still
no browser Action and no free shell. See [local loop vs hosted agents]({{ '/investigations/local-vs-cloud/' | relative_url }}).

## Two ways to reach a GPU

**Ollama on a box you rent.** The client is already written.
`OLLAMA_HOST` points at that box. `--engine` stays `ollama`.

```bash
export OLLAMA_HOST=https://gpu.example:11434
python-vibe --model qwen2.5-coder:32b run "find the NameError and fix it"
```

**OpenAI-compatible HTTP.** Hugging Face Inference, vLLM, or any other
`/v1/chat/completions` host. `--engine openai`. The token is an
environment variable. It is never written into a trace.

```bash
export HF_TOKEN=…          # or PYTHON_VIBE_API_KEY
export PYTHON_VIBE_BASE_URL=https://router.huggingface.co/v1
python-vibe --engine openai \
  --model Qwen/Qwen2.5-Coder-32B-Instruct \
  run "find the NameError and fix it"
```

If `HF_TOKEN` is set and `PYTHON_VIBE_BASE_URL` is not, the harness uses
the Hugging Face router. `PYTHON_VIBE_TIMEOUT` defaults to 180 seconds.

The 0.5B sidecar and the laptop 8B stay the defaults. A remote model is
an experiment flag, not a new everyday brain, until it **beats** untuned
`llama3.1:8b` on the checks below.

## The experiment

Same wording, same fresh `demo/orders` copy, same independent file
checks as [live scenarios]({{ '/scenarios/' | relative_url }}). The only
changed cell is the generate backend.

| Cell | Engine | Weight | Where |
| --- | --- | --- | --- |
| A | `ollama` | `llama3.1:8b` | this laptop (already measured) |
| B | `openai` | `Qwen/Qwen2.5-Coder-14B-Instruct` or `32B` | Hugging Face Inference or a rented GPU |
| C | `openai` | a 70B-class instruct model | rented GPU only |

Score is the same as the laptop tables: would a daily user ship the
diff, and does the planted `NameError` stay gone. First-Action parse
from `scripts/eval_everyday.py --live` is a second number. It flips
between runs; do not treat one pass as a win.

Everyday-ready still means: beat cell A on parse **and** on a real
≥1 KB fix. A faster 32B that still says `done` with `subtotl` in the
file is not a win. The oracles stay on.

This page has **no live B/C numbers yet**. Fill them in after a run.
Until then the laptop 8B column on [which model]({{ '/investigations/which-model/' | relative_url }})
is the only score.

## Fine-tune later, on that same GPU

The in-tree later LoRA is still
`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` via
`configs/python-vibe-8b.yaml`. On a CUDA box the same recipe is a
Hugging Face `Qwen/Qwen2.5-Coder-7B-Instruct` LoRA. The data rule does
not change with the cloud bill:

1. Record only turns the oracles already accept
   (`--record`, gitignored `data/agent-loop/extra.jsonl`).
2. Wait until that file is on the order of **~2k** clean turns, not 30.
3. Train on the rented GPU. Publish the adapter as a
   [YauhenBichel](https://huggingface.co/YauhenBichel) repo. Official
   weights stay on that account.
4. Serve the adapter with vLLM or Ollama on the same box. The laptop
   uses `--engine openai` (or `OLLAMA_HOST`) against that URL.
5. Evaluate with `scripts/eval_everyday.py --live` and
   `scripts/demo.py`. If the LoRA loses to cell A, delete the adapter.

`train.py --everyday` on the thirty seed rows is still a no, including
when someone else is paying for the GPU. That is the C4 cell in
[fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}).

## Do not

- Train more 0.5B steps because a GPU is cheap this week.
- Change `serve.py` to bind `0.0.0.0`. The sidecar stays loopback.
- Put tokens, hostnames, or adapter folders in git.
- Call a remote 32B everyday-ready from one parse pass.
- Drop `PythonVibeGuard` because the model is larger. The jail is the
  product.

Order of spend: measure cell B on the four Start commands and the
controller leftover bind. Only then rent a bigger box. Only then train.
