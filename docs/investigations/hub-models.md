---
title: Hub models for py-harness
description: Hugging Face weights this laptop can run, including GGUFs that are not in the Ollama library. Default stays 8B.
permalink: /investigations/hub-models/
date: 2026-09-05
type: article
---

# Hub models for py-harness

**Question.** Which Hugging Face models should py-harness run, and which
weights are worth a later LoRA?

**Answer.** Keep `llama3.1:8b` for daily work. Keep the 0.5B sidecar for
demos only. Do not train more 0.5B. The 1.5B and 1B already on this
laptop **do not parse `Action:`**. OpenCoder 8B and SWE-agent-LM 7B are
not `ollama pull` tags; import the Q4_K_M GGUF, then measure. The only
later LoRA base in-tree is
`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit`, after ~2k clean traces.
Pull `qwen2.5-coder:7b` only to measure it against the 8B log.

Related: [fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }})
· [model lanes]({{ '/investigations/model-lanes/' | relative_url }})
· [everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#on-this-laptop-today">On this laptop today</a></li>
  <li><a href="#hub-weights-that-are-not-an-ollama-tag">Hub weights that are not an Ollama tag</a></li>
  <li><a href="#what-else-fits-this-laptop">What else fits this laptop</a></li>
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
| `qwen2.5-coder:7b` | 4.7 GB | On disk. Same-night daily **7 / 9**. Do not switch. |
| `deepseek-coder:6.7b` | 3.8 GB | On disk. Empty VRAM daily: first clamp **passed**, second 180s. Incomplete. |
| `starcoder2:7b` | 4.0 GB | On disk. One-word generate hit 180s. Completion-style. |
| `codellama:7b-python` | 3.8 GB | On disk. One-word generate hit 180s. |
| `opencoder:8b` | 4.7 GB | On disk. One-word generate hit 180s. |
| `swe-agent-lm:7b` | 4.7 GB | On disk. One daily clamp: 12 steps, no `clamp`, **464 s**. |

## Hub weights that are not an Ollama tag

**Example.** 5 September 2026. Two small code models this laptop can
hold, that `ollama pull` cannot see. Q4_K_M is about 4.7 GB each, inside
the 11–12 GB this machine leaves for a model.

| Local tag | Source | GGUF | Licence |
| --- | --- | --- | --- |
| `opencoder:8b` | [infly/OpenCoder-8B-Instruct](https://huggingface.co/infly/OpenCoder-8B-Instruct) | [bartowski/OpenCoder-8B-Instruct-GGUF](https://huggingface.co/bartowski/OpenCoder-8B-Instruct-GGUF) `Q4_K_M` | INF |
| `swe-agent-lm:7b` | [SWE-bench/SWE-agent-LM-7B](https://huggingface.co/SWE-bench/SWE-agent-LM-7B) | [mradermacher/SWE-agent-LM-7B-GGUF](https://huggingface.co/mradermacher/SWE-agent-LM-7B-GGUF) `Q4_K_M` | Apache-2.0 |

OpenCoder is a code-instruct 8B. SWE-agent-LM is Qwen2.5-Coder-7B-Instruct
plus about 5k traces from **their** agent. Neither weight speaks
py-harness `Action:` / `Find:`. Importing them does not make them the
default. It makes `--model` work so a later daily table can score them.

```bash
python3 scripts/weights/import_hf_ollama.py --list
python3 scripts/weights/import_hf_ollama.py --name opencoder
python3 scripts/weights/import_hf_ollama.py --name swe-agent-lm
py-harness --model opencoder:8b run "add a function clamp and a unit test"
```

`--all` downloads both. `--no-create` stops after the GGUF. The script
writes `FROM` the file and calls `ollama create`. The harness still
sends the agent system prompt on each turn; the Modelfile does not
repeat it.

**Result.** Both tags are on this laptop: `opencoder:8b` and
`swe-agent-lm:7b`. A clean cold first turn on SWE-agent-LM was 38 s.
Empty VRAM daily still hit 180s on the first clamp generate. A
follow-up `ok` while `/api/ps` listed the tag hit 60s. After
`/api/ps` was empty again, the same prompt finished in 6.8 s. The
real first helper chat then finished in 14.5 s; daily first clamp
on that loaded tag hit 180s. Two copies of the Agent body (no
`keep_alive`) hit 180s; one copy with `keep_alive` finished in
115.7 s. A remasure of two `keep_alive` POSTs from empty VRAM:
first 180s (`/api/ps` empty), second 44.8 s. A concurrent
`bench.py --tier 3` on the 8B was holding `/api/chat`. That is
why the 8B was loaded again. That 8B bench ended; the same rerun
then loaded `qwen2.5-coder:7b`. An idle local remasure (empty
VRAM, no client on 11434): first Agent chat 180s, then SWE
listed; second 2.15 s. A new `bench.py --tier 6` then held the
8B and started the 7B coder. A later idle first chat with a
300s client cap still timed out and `/api/ps` stayed empty.
After that a new `bench.py --tier 3` on the 8B held `/api/chat`
again. Once that ended, an idle one-word generate finished in
7.42 s (load 5.09 s). A later helper-sized Agent chat while the
8B was listed finished in 36.69 s. A second helper chat while
SWE was still listed finished in 74.83 s (load 0.02 s, 1,700
eval tokens). Later an 8B client held `/api/chat`; a second
local client then held the 8B again. After that an empty-VRAM
helper chat finished in 43.45 s. One daily clamp job then ran
12 steps in 464 s with no `def clamp`. OpenCoder still misses a
one-word generate.
Write-tests was 3 / 3 with no model (harness AAA bind). That is not
a score. Do not switch the default.

## What else fits this laptop

This machine is an Apple M3 Pro with 18 GB unified memory. About
11–12 GB is left for a model. A 7B–8B Q4_K_M file is about 4–5 GB
and runs. A 14B already caused swap. A 30B timed out at 180 seconds.
Do not pull those two.

Looked up on Hugging Face, 5 September 2026. Downloads are not a
score for this helper.

### Already on the measure list

These write Python. None of them were trained on py-harness
`Action:` / `Find:`.

| Weight | Size class | How to run | Notes |
| --- | --- | --- | --- |
| [Qwen/Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) | 7B, Apache-2.0 | `ollama pull qwen2.5-coder:7b` | Daily **7 / 9**. Official GGUF also exists. |
| [deepseek-ai/deepseek-coder-6.7b-instruct](https://huggingface.co/deepseek-ai/deepseek-coder-6.7b-instruct) | 6.7B | `ollama pull deepseek-coder:6.7b` | On disk. Daily not in yet. |
| [bigcode/starcoder2-7b](https://huggingface.co/bigcode/starcoder2-7b) | 7B, OpenRAIL | `ollama pull starcoder2:7b` | On disk. One-word generate hit 180s. Completion-style. |
| [codellama/CodeLlama-7b-Python-hf](https://huggingface.co/codellama/CodeLlama-7b-Python-hf) | 7B | `ollama pull codellama:7b-python` | On disk. One-word generate hit 180s. |
| [infly/OpenCoder-8B-Instruct](https://huggingface.co/infly/OpenCoder-8B-Instruct) | 8B, INF | `import_hf_ollama.py --name opencoder` | On disk as `opencoder:8b`. One-word generate hit 180s. |
| [SWE-bench/SWE-agent-LM-7B](https://huggingface.co/SWE-bench/SWE-agent-LM-7B) | 7B, Apache-2.0 | `import_hf_ollama.py --name swe-agent-lm` | On disk as `swe-agent-lm:7b`. One daily clamp: 12 steps, no `clamp`, 464 s. |

### Fits, measure later

Do not download these until the table above has scores. A 9B Q4 is
about 5.5 GB — tight, but inside 12 GB.

| Weight | Why it is interesting | Why wait |
| --- | --- | --- |
| [OpenHands/openhands-lm-7b-v0.1](https://huggingface.co/OpenHands/openhands-lm-7b-v0.1) (MIT). GGUF: [bartowski/all-hands_openhands-lm-7b-v0.1-GGUF](https://huggingface.co/bartowski/all-hands_openhands-lm-7b-v0.1-GGUF) | Same 7B coder family, trained on SWE-Gym for **their** agent. | Same warning as SWE-agent-LM. Import after that one has a daily score. |
| [ByteDance-Seed/Seed-Coder-8B-Instruct](https://huggingface.co/ByteDance-Seed/Seed-Coder-8B-Instruct) (MIT). GGUF: [unsloth/Seed-Coder-8B-Instruct-GGUF](https://huggingface.co/unsloth/Seed-Coder-8B-Instruct-GGUF) | New code-instruct 8B. | No Ollama library tag. Same import path as OpenCoder. Not measured. |
| [ibm-granite/granite-8b-code-instruct-4k](https://huggingface.co/ibm-granite/granite-8b-code-instruct-4k) (Apache-2.0). GGUF: [ibm-granite/granite-8b-code-instruct-4k-GGUF](https://huggingface.co/ibm-granite/granite-8b-code-instruct-4k-GGUF) | Code + commits. Official GGUF. | Older 4k context. Measure only if the 7B/8B table is still a tie. |
| [01-ai/Yi-Coder-9B-Chat](https://huggingface.co/01-ai/Yi-Coder-9B-Chat) (Apache-2.0). GGUF: [bartowski/Yi-Coder-9B-Chat-GGUF](https://huggingface.co/bartowski/Yi-Coder-9B-Chat-GGUF) | Strong code chat. Q4 about 5.5 GB. | Larger than the 7B pack. Last, not first. |

### Do not pull for this laptop

| Weight | Why not |
| --- | --- |
| `qwen2.5-coder:14b` (already on disk, 9 GB) | Caused swap here. |
| `qwen3coder` / 30B-class (18 GB) | Timed out at 180 seconds. |
| DeepSeek-Coder-V2-Lite (~16B), Codestral 22B, Qwen2.5-Coder-32B | Over the 11–12 GB room. Use [cloud weights]({{ '/investigations/cloud-weights/' | relative_url }}). |
| Random 0-download “function calling” LoRAs | Wrong schema. Not this `Action:` line. |

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
| Measure, Hub GGUF | [infly/OpenCoder-8B-Instruct](https://huggingface.co/infly/OpenCoder-8B-Instruct) | `import_hf_ollama.py --name opencoder` then `--model opencoder:8b` | Import. Do not switch until a daily table beats 8B |
| Measure, Hub GGUF | [SWE-bench/SWE-agent-LM-7B](https://huggingface.co/SWE-bench/SWE-agent-LM-7B) | `import_hf_ollama.py --name swe-agent-lm` then `--model swe-agent-lm:7b` | Import. Their agent traces, not this loop |

## Later LoRA bases

| Hub id | Why it is the one in-tree | Tune now? |
| --- | --- | --- |
| [mlx-community/Qwen2.5-Coder-7B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit) | `configs/python-vibe-8b.yaml`. Apache-2.0. Same family as the published 0.5B. | **Later.** After ~2k `--record` turns the oracles already accept. |
| [mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit) | Current `train.py` base | **No.** Overfit after step 100. |
| [mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit) | Mid sidecar if it ever parses `Action:` | **No** until a probe returns `Action:`. Today it does not. |

Publish kit adapters on Qwen2.5-Coder (Apache-2.0). Running Llama 3.1 8B
through Ollama is fine. Do not publish a Llama-derived LoRA as the
official py-harness weight without following the Llama 3.1 licence.

## Do not

- Train more 0.5B for agency.
- Run `train.py --everyday` on the 30 seed rows.
- Make `qwen2.5-coder:1.5b` or `llama3.2:1b` the default — they answer in
  prose or drop the `Action:` verb.
- Pull the 30B for daily writes. It already lost on latency.
- Use [bigcode/starcoder2-3b](https://huggingface.co/bigcode/starcoder2-3b)
  as a kit LoRA base (completion model, OpenRAIL).
- Make `opencoder:8b` or `swe-agent-lm:7b` the default before a daily
  table. Import is not a score.
- Name other editors or chat products in public notes.

Order of work: oracles on the 8B this week; import the two Hub GGUFs when
you want a download that `ollama pull` cannot see; optional 7B compare;
a 14B–70B only through [cloud weights]({{ '/investigations/cloud-weights/' | relative_url }});
7B LoRA only after clean traces.
