---
title: Hub models for python-vibe
description: Hugging Face weights this laptop can run, plus first-Action probes on the 1.5B and 1B already on disk. Default stays 8B.
permalink: /investigations/hub-models/
date: 2026-08-29
type: article
---

# Hub models for python-vibe

**Question.** Which Hugging Face models should python-vibe run, and which
weights are worth a later LoRA?

**Answer.** Keep `llama3.1:8b` for daily work. Keep the 0.5B sidecar for
demos only. Do not train more 0.5B. The 1.5B and 1B already on this
laptop **do not parse `Action:`**. The only later LoRA base in-tree is
`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, after ~2k clean traces.
Pull `qwen2.5-coder:7b` only to measure it against the 8B log.

Related: [fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }})
· [model lanes]({{ '/investigations/model-lanes/' | relative_url }})
· [everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#on-this-laptop-today">On this laptop today</a></li>
  <li><a href="#first-action-probes-29-aug-2026">First Action probes, 29 Aug 2026</a></li>
  <li><a href="#hub-ids-that-fit-this-repo">Hub ids that fit this repo</a></li>
  <li><a href="#later-lora-bases">Later LoRA bases</a></li>
  <li><a href="#do-not">Do not</a></li>
</ol>
</nav>

## On this laptop today

| Ollama / Hub id | Size | Role |
| --- | --- | --- |
| `llama3.1:8b` → [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | 4.9 GB | Everyday default. Gated Llama 3.1 licence. |
| `qwen2.5-coder:0.5b` → [Qwen/Qwen2.5-Coder-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct) | 397 MB | Smoke / `--tiny`. Apache-2.0. |
| [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b) | adapters | Style prior on the 0.5B. Apache-2.0. |
| `qwen2.5-coder:1.5b` → [Qwen/Qwen2.5-Coder-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct) | 986 MB | On disk. **No `Action:` parse** in the probes below. |
| `llama3.2:1b` → [meta-llama/Llama-3.2-1B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct) | 1.3 GB | On disk. **No `Action:` parse.** |
| `qwen3coder` 30B-class | 18 GB | Already timed out at the 180s Ollama cap. |
| `qwen2.5-coder:7b` | — | **Not pulled.** Optional write specialist after a live compare. |

Hub lifetime downloads (overview, 29 Aug 2026) are not a quality score for
this harness. Qwen2.5-Coder-0.5B-Instruct has 14.2M downloads and still
failed held-out vibe 0/4 here. Llama-3.1-8B-Instruct has 180M downloads
and is already the everyday brain via Ollama.

## First Action probes, 29 Aug 2026

Same builder as the real loop (`scripts/measure/skill_probe.py`), fixture
`eval/fixtures/add_feature_pkg`. A score of 1 means the first parsed
Action was the intended one (`done` on a question, `patch` + `Append:`
on add).

| Task | 0.5B (earlier) | 1B `llama3.2` | 1.5B coder | 8B |
| --- | --- | --- | --- | --- |
| `what does add return?` | 0 (echo / no Action) | 0 — prose answer, no `Action:` | 0 — prose answer, no `Action:` | 1 on the older listen_addr set |
| add `multiply` + test | 0 | 0 — wrote `patch pkg/mathy.py` without `Action:` | 0 — wrote `# patch`, not `Action: patch` | 1 (`patch` + `Append:`) |

The 1.5B *knew* the file and the missing function. It did not speak the
protocol. That is why it cannot be the default, and why a LoRA on 30
seed rows is the wrong next spend: the small models fail the first line.

## Hub ids that fit this repo

| Lane | Hub id | How to run | Do it? |
| --- | --- | --- | --- |
| Everyday | [meta-llama/Llama-3.1-8B-Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | `ollama pull llama3.1:8b` | Keep |
| Sidecar | [Qwen/Qwen2.5-Coder-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct) + [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b) | `--tiny` / `serve.py` | Demos only |
| Measure next | [Qwen/Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) (21.4M downloads, Apache-2.0) | `ollama pull qwen2.5-coder:7b` then `scripts/run/demo.py --model qwen2.5-coder:7b` | Keep only if independent file checks beat the 8B log |
| On disk, unusable as default | [Qwen/Qwen2.5-Coder-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct) | already pulled | Do not switch the default |
| Optional later probe | [microsoft/Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct) (3.84B, MIT, 8.8M downloads) | not pulled | Different tokenizer. Measure before any LoRA |

## Later LoRA bases

| Hub id | Why it is the one in-tree | Tune now? |
| --- | --- | --- |
| [mlx-community/Qwen2.5-Coder-7B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit) | `configs/python-vibe-8b.yaml`. Apache-2.0. Same family as the published 0.5B. | **Later.** After ~2k `--record` turns the oracles already accept. |
| [mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit) | Current `train.py` base | **No.** Overfit after step 100. |
| [mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit) | Mid sidecar if it ever parses `Action:` | **No** until a probe returns `Action:`. Today it does not. |

Publish kit adapters on Qwen2.5-Coder (Apache-2.0). Running Llama 3.1 8B
through Ollama is fine. Do not publish a Llama-derived LoRA as the
official python-vibe weight without following the Llama 3.1 licence.

## Do not

- Train more 0.5B for agency.
- Run `train.py --everyday` on the 30 seed rows.
- Make `qwen2.5-coder:1.5b` or `llama3.2:1b` the default — they answer in
  prose or drop the `Action:` verb.
- Pull the 30B for daily writes. It already lost on latency.
- Use [bigcode/starcoder2-3b](https://huggingface.co/bigcode/starcoder2-3b)
  as a kit LoRA base (completion model, OpenRAIL).
- Name other editors or chat products in public notes.

Order of work: oracles on the 8B this week; optional 7B compare when you
want a download; a 14B–70B only through [cloud weights]({{ '/investigations/cloud-weights/' | relative_url }});
7B LoRA only after clean traces.
