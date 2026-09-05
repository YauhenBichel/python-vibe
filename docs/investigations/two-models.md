---
title: Two models, one wall
description: llama3.1:8b and qwen2.5-coder:7b score 51 and 50 out of 75 on the same benchmark. The same wall, and almost opposite failures — one writes wrong code, the other writes nothing.
permalink: /investigations/two-models/
date: 2026-09-05
type: article
---

A third of runs fail, and two thirds of those failures are plausible
wrong code. The obvious question before training anything is whether the
base model is the constraint. It is a cheap question: the benchmark
takes a model name.

Seventy-five runs each — fifteen cases, five passes — same commit, same
machine, same harness, only the weights changed.

## The same score

| | Worked | Failed |
| --- | --- | --- |
| `llama3.1:8b` | 51 of 75 | 24 (32%) |
| `qwen2.5-coder:7b` | 50 of 75 | 25 (33%) |

One case apart, which is noise on a benchmark where four cases is the
threshold. Two models of different lineage, one trained for code, meet
the same wall on the same tasks.

That is worth more than either number alone. A single model failing says
something about that model. Two unrelated models failing identically
says something about the size.

## Almost opposite failures

| How it failed | `llama3.1:8b` | `qwen2.5-coder:7b` |
| --- | --- | --- |
| wrote nothing at all | 8 | **18** |
| wrote something, not the thing asked for | **10** | 3 |
| wrote something, it did not do the job | 6 | 4 |
| **claimed success having written nothing** | **0** | **0** |

`llama3.1` fails by writing the wrong thing. `qwen2.5-coder` fails by
writing nothing at all. Wrong-code failures fall from sixteen of
twenty-four to seven of twenty-five, and the runs that would have
produced them give up instead.

For a tool somebody is watching, that is the better failure: nothing
broken is written and the run says plainly that it stopped. Neither
model ever reported success with the file untouched, which is the
guarantee added earlier this week holding across two models rather than
one.

## And different tiers

| Tier | `llama3.1:8b` | `qwen2.5-coder:7b` |
| --- | --- | --- |
| 1 one small component | 4 | 6 |
| 3 a new module with a test | 5 | **8 of 10** |
| 5 fix a bug already there | 4 | 0 |
| 6 platform and operations | **11 of 20** | 10 |

They are not the same tool at different accuracies. `llama3.1` is worst
at platform work; `qwen2.5-coder` is worst at creating a new module with
a test, and does not fail the bugfix tier at all.

## What it changes

**A model swap is not the fix.** Two models score the same, so nothing
is gained by preferring one outright.

**The bar for a fine-tune moved.** The stated target was the sixty-seven
per cent that writes plausible wrong code, and `qwen2.5-coder` shows
that number can be cut without any gain in work done — the failures
simply change shape. A fine-tune has to raise the count of runs that
work, not improve the manner of failing.

**And the two failure sets barely overlap.** One is better at platform
work, the other does not fail bugfixes. The harness already picks a lane
per task and then asks the same model every time. Choosing the model per
tier is a change to about ten lines, needs no training, and is the first
thing measured this week with a reason to expect the number to move.

## Reproducing this

```bash
python scripts/measure/bench.py --repeat 5
python scripts/measure/bench.py --model qwen2.5-coder:7b --repeat 5
```

Both print a row per run with what was written and why it failed. The
tables above are those rows counted, nothing else.
