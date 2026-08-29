---
title: Which model
description: Three local models measured on the same eleven jobs. The 8B wins the work this is built for, the 7B coder loses it, and the 30B does not finish at all.
permalink: /investigations/which-model/
date: 2026-08-29
---

# Which model

**Answer:** keep `llama3.1:8b`. A code-specialised 7B is better at operations
work and worse at everything this project is actually used for. A 30B does
not finish a single task on this laptop.

Related: [model lanes](./model-lanes.md) ·
[fine-tune or harness](./fine-tune-or-harness.md).

## How this was measured

`scripts/bench.py` runs tasks in six tiers and then **runs the code it
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
