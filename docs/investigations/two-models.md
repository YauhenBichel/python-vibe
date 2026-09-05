---
title: Two models, one wall
description: llama3.1:8b and qwen2.5-coder:7b score 51 and 50 out of 75 on the same benchmark, and fail in opposite ways. The per-tier differences that suggested routing needed ten passes, and one of them vanished.
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

## And different tiers — one of which was noise

The five-pass run split like this:

| Tier | `llama3.1:8b` | `qwen2.5-coder:7b` |
| --- | --- | --- |
| 1 one small component | 4 | 6 |
| 3 a new module with a test | 5 | 8 of 10 |
| 5 fix a bug already there | 4 | 0 |
| 6 platform and operations | 11 of 20 | 10 |

Four failures against nought on the bugfix tier looked like a real
difference, and it was the reason to consider sending some tasks to one
model and some to the other. Each tier holds two to four cases, so five
passes is a handful of runs, and it was worth checking before building
anything on it.

Ten passes on the two tiers with the largest apparent gap:

| Ten passes, two cases each | `llama3.1:8b` | `qwen2.5-coder:7b` |
| --- | --- | --- |
| 5 fix a bug already there | **18 of 20** | **18 of 20** |
| 3 a new module with a test | **13 of 20** | **7 of 20** |

**The bugfix advantage was not there.** Identical at ten passes; the
gap came from one case, `fix-offbyone`, in a five-run sample.

**The tier-3 gap is real, and larger than five passes suggested.** Six
cases apart on twenty runs. `llama3.1` is better at "create a new module
and a test for it" — the task type a coder model would be expected to
win.

## What it changes

**A model swap is not the fix.** Two models score the same overall, so
nothing is gained by preferring one outright.

**The bar for a fine-tune moved.** The stated target was the sixty-seven
per cent that writes plausible wrong code, and `qwen2.5-coder` shows
that number can be cut without any gain in work done — the failures
simply change shape. A fine-tune has to raise the count of runs that
work, not improve the manner of failing.

**Routing between these two would gain nothing.** That was the plan this
page originally argued for, and checking it removed the reason: the one
tier where `qwen2.5-coder` looked stronger came out level, and the tier
where it looked weaker came out weaker still. There is no task type to
send it. `llama3.1:8b` is the better default and the apparent
complementarity was an artefact of the sample size.

**Five passes is not enough to compare two models here.** It is enough
to compare a change against itself, which is what it was calibrated for
— ten of fifteen cases change verdict between identical runs. A per-tier
split cuts the same runs into groups of ten, and a difference that size
needs ten passes before it means anything. The first table on this page
is left in place because it is what five passes says, and the second is
what the same question answers when asked properly.

## Reproducing this

```bash
python scripts/measure/bench.py --repeat 5
python scripts/measure/bench.py --model qwen2.5-coder:7b --repeat 5

# and the per-tier numbers, which need ten passes to mean anything
python scripts/measure/bench.py --tier 5 --repeat 10
python scripts/measure/bench.py --tier 5 --model qwen2.5-coder:7b --repeat 10
```

Both print a row per run with what was written and why it failed. The
tables above are those rows counted, nothing else.
