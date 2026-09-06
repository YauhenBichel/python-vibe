---
title: The wall two local models share
description: Tier six is where two 7-8B models stop together. A hosted 32B on the identical harness scores 18 of 20 against their 8 and 11. The two local models are not distinguishable from each other, and the gap to the larger one is.
permalink: /investigations/the-wall/
date: 2026-09-06
type: article
---

Tier six is platform and operations work: environment flags, virtualenv
paths, `KEY=VALUE` files, retries. Two models of different lineage were
reported to stop at the same place, and the natural reading was that a
wall two unrelated models hit together is a wall in the *tool*.

Once the benchmark was
[repaired]({{ '/investigations/the-fence/' | relative_url }}), that
became testable. Same harness, same four cases, five passes each.

## The measurement

| tier six, twenty runs each | worked |
| --- | --- |
| `Qwen2.5-Coder-32B-Instruct` (hosted) | **18 of 20** |
| `qwen2.5-coder:7b` (local) | 11 of 20 |
| `llama3.1:8b` (local, the default) | 8 of 20 |

| case | 32B | qwen 7b | llama 8b |
| --- | --- | --- | --- |
| `env-flag` | 4/5 | 3/5 | 0/5 |
| `venv-python` | 5/5 | 1/5 | 2/5 |
| `read-env-file` | 5/5 | 2/5 | 2/5 |
| `retry` | 4/5 | 5/5 | 4/5 |

Nothing about the harness differs between these columns. Same cases,
same prompts, same refusals, same answerer, same step budget. The only
variable is the weights behind it.

## What the numbers support, and what they do not

This project treats a gap under about four cases as noise. Applying its
own rule:

- **32B against either local model** — seven and ten cases. Real.
- **The two local models against each other** — three cases. Noise.

So the honest reading is that the two local models are *not*
distinguishable on this tier, which is what
[two models, one wall]({{ '/investigations/two-models/' | relative_url }})
said in the first place, and that the larger model clears a wall they
share.

The temptation was to read the per-case rows instead. `env-flag` is 0 of
5 for the default and 3 of 5 for the 7B coder, which looks like a finding
and is five runs against five. At the halfway point that cell stood at
3 of 3 and looked like a much bigger one. It is a hint about where to
look next, not a result.

## What it overturns

[Asking a bigger model]({{ '/investigations/asking-a-bigger-model/' | relative_url }})
argued for a narrow trigger partly on this ground:

> Seven of the nine failures were tier 6 — paths, environment,
> configuration, retries. That tier went from 37% to 70% on earlier work
> through harness fixes alone, with the same model. Those are gaps in
> the tool, not gaps in the model's knowledge, and sending them to a
> bigger model would hide them instead of fixing them.

The first sentence stands: harness work really did move that tier a long
way without touching the model. The conclusion does not. If tier six
were only a gap in the tool, a different model driving the same tool
would score alike. It does not — it scores more than twice as well.

So tier six is both. Harness fixes closed part of it, and a capability
gap sits underneath what they reached, out of reach of another rule or
another refusal, because the tool holding the model is already the same
tool.

That inverts which stuck moments are worth a remote call. Tier six was
the tier to keep local, on the argument that sending it away would hide
tool gaps. It is the tier where the local ceiling is lowest and the
remote advantage largest.

## How wrong the first look kept being

Four times in one night a confident reading dissolved on a fuller
sample:

- A partial 3 of 9 read as a regression caused by a change that was, for
  local weights, a no-op. It finished 10 of 20 against a control of
  10 of 20.
- A published "three runs out of three" turned out to be guaranteed by
  the instrument rather than measured.
- This table read as a story about size, until a 7B was put beside the
  8B and beat it.
- Then that reading collapsed too, when the 7B's twenty runs came in and
  its lead turned out to be three cases, which is noise.

The common cause is sample size. Tier three is two cases; tier six is
four. At five passes that is ten or twenty runs, and the spread is wide
enough that the first look is usually wrong and the second often is too.
The rule was already written down. The discipline is to wait for the
last column before writing the sentence, and to apply the rule to the
comparison you actually want to make rather than to the one that reads
best.

## What it does not say

It does not say to change the default. The two local models are level
here, and `llama3.1:8b` wins the daily jobs 9 of 9 against the coder's
7 of 9.

It does not say to run a bigger model locally either. A 14B already
times out three times out of three in 18 GB, so the 32B column was
bought with credits rather than electricity.

It does sharpen the fine-tune question. The thing worth learning is
whatever the larger model knows about flags, paths and env files that
neither local model does — a narrower target than "be a better agent",
and a narrow target is what a small adapter can carry.

## Reproducing this

```bash
HF_TOKEN=… python scripts/measure/bench.py --tier 6 --engine openai \
  --model Qwen/Qwen2.5-Coder-32B-Instruct --repeat 5
python scripts/measure/bench.py --tier 6 --model llama3.1:8b --repeat 5
python scripts/measure/bench.py --tier 6 --model qwen2.5-coder:7b --repeat 5
```

Tier 5 for the same hosted model, for context: 8 of 10, with
`fix-nameerror` 5 of 5 and `fix-offbyone` 3 of 5.
