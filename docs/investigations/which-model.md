---
title: Which model
description: Three local models measured on the same eleven jobs. The 8B wins the work this is built for, the 7B coder loses it, and the 30B does not finish at all.
permalink: /investigations/which-model/
date: 2026-09-05
---

# Which model

**Keep `llama3.1:8b`.** A 7B trained on code is a little better at
operations work and a little worse at the jobs this tool is for: write
a test, add a small function, fix a bug. A 30B does not finish a single
task on this laptop.

Related: [model lanes](./model-lanes.md) ·
[fine-tune or harness](./fine-tune-or-harness.md) ·
[two models, one wall](./two-models.md) ·
[Hub models](./hub-models.md).

## How this was measured

`scripts/measure/bench.py` runs tasks in six tiers and then **runs the code it
wrote**. A case counts as working when the function does the job — not when
a file appears.

| Tier | The job |
| --- | --- |
| 1 | a small component in a file that already exists |
| 2 | a component and a test for it |
| 3 | a new module with a component and a test |
| 4 | write a test for something already there |
| 5 | fix a bug that is already in the code |
| 6 | platform work: paths, environment, config, retries |

Tiers 1, 2, 4 and 5 are the jobs this project is built for: write a test,
add a small component, fix a bug.

## The result

Measured on one laptop, 29 August 2026, through Ollama.

| Model | Tiers 1, 2, 4, 5 | Tier 6 |
| --- | --- | --- |
| `llama3.1:8b` | **6–9 / 9** (six runs) | 1 / 4 |
| `qwen2.5-coder:7b` | 7 / 9 | **2 / 4** |
| `qwen3coder` (30B) | not run | **0 / 4, every case timed out** |

The 30B result is not a score. Every case ended in a timeout, so the model
never produced a usable turn at all.

## Same-night daily jobs, 5 September 2026

`scripts/measure/eval_daily.py`. Write a test, add `clamp`, fix a sum.
Three repeats. Twelve steps.

| Model | Write tests | Add clamp | Logic bug | Passed |
| --- | --- | --- | --- | --- |
| `llama3.1:8b` | 3 / 3 | 3 / 3 | 3 / 3 | **9 / 9** |
| `qwen2.5-coder:7b` | 3 / 3 | 1 / 3 | 3 / 3 | **7 / 9** |
| `deepseek-coder:6.7b` | 3 / 3 (compiler) | 1 pass, 1 `steps`, 180s timeout | not run | incomplete |
| `deepseek-coder:6.7b` (empty VRAM) | 3 / 3 (compiler) | **1 pass** (`steps`), then 180s | not run | incomplete |
| `starcoder2:7b` | 3 / 3 (compiler) | 180s timeout | not run | incomplete |
| `codellama:7b-python` | 3 / 3 (compiler) | 180s timeout | not run | incomplete |
| `opencoder:8b` | 3 / 3 (compiler) | 180s timeout | not run | incomplete |
| `swe-agent-lm:7b` | 3 / 3 (compiler) | 180s timeout | not run | incomplete |
| `swe-agent-lm:7b` (empty VRAM) | 3 / 3 (compiler) | 180s timeout | not run | incomplete |

The 7B coder stopped twice to ask where `clamp` should go. The logic-bug
3 / 3 on the 8B and 7B coder is a compiler `return 0` bind, not the
model writing the sum. A two-case gap is noise.

Write-tests 3 / 3 on the extra tags does not call the model. Clamp is
the first generate. A cold load plus one reply burned the 180s Ollama
cap. A second pass warmed each tag first (`keep_alive` 30 minutes) and
finished. OpenCoder and StarCoder2: warmup got 0 bytes in 300s.
SWE-agent-LM was in memory and still timed out on clamp. CodeLlama's
warmup returned, then clamp still hit 180s. DeepSeek got one clamp
through, then the same cap. A one-word generate (`Reply with the
single word ok.`) finished on the 8B (3.9 s), 7B coder (11.5 s),
DeepSeek (3.8 s), and SWE-agent-LM (19.6 s). StarCoder2, CodeLlama,
and OpenCoder hit 180s. The same four then finished the daily clamp
*text* (no helper prompt) in 22–40 s. The real first helper chat is
about 1,700 tokens and finished in 12–39 s on those four. A clean
cold first turn (unload, then that chat) was 17 s on the 8B, 54 s
on DeepSeek, and 38 s on SWE-agent-LM. `keep_alive` 0 did not evict
the 7B coder. `ollama stop` did: DeepSeek first clamp **passed**
(`steps`), second hit 180s. SWE-agent-LM from empty VRAM still hit
180s on the first clamp generate (the tag was loaded after). A
follow-up `ok` generate while it was still listed hit 60s. After
`/api/ps` was empty again, the same prompt finished in 6.8 s. The
real first helper chat then finished in 14.5 s; daily first clamp
on that loaded tag hit 180s. Two copies of the Agent body (no
`keep_alive`) then hit 180s; one copy with `keep_alive` finished
in 115.7 s. A remasure of two `keep_alive` POSTs from empty VRAM:
first 180s, second 44.8 s. A concurrent `bench.py --tier 3` on
the 8B was holding `/api/chat` during those walls. That 8B bench
ended; the same rerun then loaded `qwen2.5-coder:7b`. An idle
local remasure (empty VRAM, no client on 11434): first Agent
chat 180s, then SWE listed; second 2.15 s. A new
`bench.py --tier 6` then held the 8B and started the 7B coder.
A later idle first chat with a 300s client cap still timed
out and `/api/ps` stayed empty. A reply is not a daily score.
**Do not switch.**
See [Hub models](./hub-models.md).

## One run is not a score

After this comparison was published the same nine cases were run six
times against unchanged code:

    9/9   6/9   8/9   7/9   8/9   7/9

Five of the nine pass every time, and three of those five finish without
calling the model. Across the whole fifteen-case bench, ten of fifteen
changed verdict between identical runs and the totals ranged from 7 to
12. Each model above was measured once, which is enough to show that the
30B never finished and not enough to separate `llama3.1:8b` from
`qwen2.5-coder:7b`. Treat a gap smaller than about four cases as noise.

## What that means

**Do not switch.** The 7B coder trades two of the four jobs you do most for
one extra operations task. That is a bad trade whichever way the variance
falls.

**Do not read too much into single runs.** The same model on the same task
gives a different answer between runs. One case failed on spacing, `"A L"`
where `"AL"` was wanted; another took nineteen minutes. Where this page
gives a number, it is one run, and the direction matters more than the
digit.

## The finding underneath

Across the six tiers, the cases that pass reliably are the ones the harness
finishes **without asking the model at all**:

```
cover-discount   yes   steps=0   0.2s
cover-shout      yes   steps=0   0.2s
fix-nameerror    yes   steps=0   0.1s
```

A misspelled name next to the right one, a missing import for a well-known
module, a test that needs adding to a file that already has one — these are
compiler jobs. Done deterministically, they cannot be got wrong, and they
do not vary between runs.

Everything that still fails is the model reasoning badly rather than
formatting badly: a flag reader that does not treat `"0"` as false, a file
reader that returns `None`, a retry that never calls what it was given.

That is the case against reaching for training first. Fine-tuning on tool
traces teaches a model to emit the protocol. The protocol is not where
these runs fail.

## Do not

- Do not quote a tier score as a capability. It is one run of a model that
  varies.
- Do not pull the 30B expecting the numbers to improve. It times out.
- Do not train on synthetic traces to fix reasoning errors. Record real
  ones first and look at what they actually contain.
- Do not switch to `opencoder:8b` or `swe-agent-lm:7b` until a daily
  table exists. They are not `ollama pull` tags; import them with
  `scripts/weights/import_hf_ollama.py`. See
  [Hub models](./hub-models.md).
