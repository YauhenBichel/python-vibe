---
title: Bench record
description: The machine, the models, and every benchmark run behind the numbers on this site. One laptop, 29–30 August 2026.
permalink: /investigations/bench-record/
date: 2026-08-30
type: article
---

# Bench record

Every number quoted elsewhere on this site comes from the runs below, on
the machine below. It is one laptop, so treat the figures as the size of
a thing rather than a rank.

Summary and conclusions: [Experiments]({{ '/investigations/experiments/' | relative_url }}).

## The machine

| | |
| --- | --- |
| Chip | Apple M3 Pro, 11 cores (5 performance, 6 efficiency), 14 GPU cores |
| Memory | **18 GB unified**, shared between macOS, the editor and the model |
| macOS | 26.5.2 |
| Runtime | Ollama 0.33.2, Python 3.13.2 |
| Storage | 44 GB free at the time of the runs |

The memory number is the one that decides what can be tried. It is
unified, so the GPU has no separate pool: a model competes with
everything else running.

## What actually fits

Weights are 4-bit (Q4_K_M) unless stated. "Fits" means the run completes
without the machine paging to disk.

| Model | On disk | Fits in 18 GB | Measured |
| --- | --- | --- | --- |
| `qwen2.5-coder:0.5b` | 0.4 GB | yes | yes |
| `qwen2.5-coder:1.5b` | 1.0 GB | yes | yes |
| `llama3.1:8b` | 4.9 GB | yes, comfortably | yes, the default |
| `qwen2.5-coder:7b` | 4.7 GB | yes, comfortably | yes |
| `qwen2.5-coder:14b` | 9.0 GB | on paper | **no — see below** |
| `qwen3-coder-30b-a3b` | 18.6 GB | no | no, times out |

The practical ceiling is not 18 GB. Weights are only part of it: the
key-value cache grows with context, and macOS and an editor want several
gigabytes. On this machine the usable budget is about **11–12 GB**.

The 14B is the interesting case because on paper it clears that. It does
not. Starting a benchmark against it put the machine into 12–13 GB of
swap and no single fifteen-case run finished in the time an 8B run takes
four times over. The failure is paging, not the model.

That was written down as a risk before the run, in the same note that
said a result under those conditions would be void. It was.

## The benchmark

`scripts/bench.py`. Fifteen cases in six tiers. A case counts only if
the function runs and does the job afterwards — not if a file appeared,
and not if the agent reported success.

Six full runs of `llama3.1:8b`, same code, same machine.

| Case | What it asks for | Passed |
| --- | --- | --- |
| `double` | one small component | `YYYYYY` **6/6** |
| `initials` | one small component | `Y·Y·Y·` **3/6** |
| `largest` | one small component | `YY·Y·Y` **4/6** |
| `average` | a component and its test | `Y·YYYY` **5/6** |
| `clamp` | a component and its test | `YYYYYY` **6/6** |
| `slugify` | a new module | `·Y··Y·` **2/6** |
| `wordcount` | a new module | `Y··Y··` **2/6** |
| `cover-discount` | a test for code already there | `YYYYYY` **6/6** |
| `cover-shout` | a test for code already there | `YYYYYY` **6/6** |
| `fix-nameerror` | a bug already in the code | `YYYYYY` **6/6** |
| `fix-offbyone` | a bug already in the code | `Y·Y·Y·` **3/6** |
| `env-flag` | paths, env, config, retries | `Y·····` **1/6** |
| `read-env-file` | paths, env, config, retries | `···Y··` **1/6** |
| `retry` | paths, env, config, retries | `YYY·Y·` **4/6** |
| `venv-python` | paths, env, config, retries | `··YYY·` **3/6** |

Totals per run: **12, 8, 10, 10, 11, 7** of 15.

- Everyday work (a component, a test, a bug fix): **9, 6, 8, 7, 8, 7** of 9
- Platform work (paths, environment, config, retries): **2, 1, 2, 2, 2, 0** of 4
- Model time per run: 75–126 seconds

## What the repeats show

Five cases pass every single time: `double`, `clamp`,
`cover-discount`, `cover-shout`, `fix-nameerror`. Three of those five
finish with **no model call at all** — the harness repairs them
mechanically, in about a tenth of a second.

Ten of the fifteen changed verdict between identical runs.

So a single run cannot show a gain or a regression here. The spread on
the everyday group alone is three cases wide. Anything smaller than
about four cases is inside the noise, which is why the model comparison
below is quoted as a size and not a ranking.

## Comparing models

One run each, on the same fifteen cases. Enough to see that a model
never finished; not enough to separate two that did.

| Model | Everyday | Platform | Note |
| --- | --- | --- | --- |
| `llama3.1:8b` | 6–9 / 9 over six runs | 0–2 / 4 | the default |
| `qwen2.5-coder:7b` | 7 / 9, one run | 2 / 4 | better at ops, worse elsewhere |
| `qwen2.5-coder:14b` | not measurable | not measurable | pages to disk on 18 GB |
| 30B-class MoE | 0 / 4 | 0 / 4 | timed out, four of four |
| 1B and 1.5B | — | — | never emitted `Action:` |

## Reproducing this

```bash
ollama pull llama3.1:8b
pip install -e .
python scripts/bench.py --model llama3.1:8b
```

Run it more than once. One run of this benchmark is a sample, not a
score.

A model too large for the machine can be reached without buying
hardware, through an OpenAI-compatible host:

```bash
export PYTHON_VIBE_BASE_URL=…  PYTHON_VIBE_API_KEY=…
python scripts/bench.py --engine openai --model <a model that host serves>
```

The prompt carries the code the harness read, so point that at a host
you would show your code to. See
[cloud weights]({{ '/investigations/cloud-weights/' | relative_url }}).
