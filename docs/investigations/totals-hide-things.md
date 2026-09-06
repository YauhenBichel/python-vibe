---
title: What the totals were hiding
description: A change scored 9 of 20 against 10 of 20 and looked like noise. Underneath were two opposite deterministic effects, one of them the harness writing a wrong function with no model at all. Fixing that took tier three to 19 of 20.
permalink: /investigations/totals-hide-things/
date: 2026-09-06
type: article
---

A change to how the harness reads the subject of a task was measured
twice and looked, both times, like nothing.

| tier 3, twenty runs an arm | worked |
| --- | --- |
| before | 9 of 20 |
| after | 10 of 20 |

One case. Inside the noise floor. The obvious write-up was "the penalty
this change was rejected for does not reproduce, and the change is
neutral". That would have been wrong, and the reason is worth keeping.

## The giveaway was the variance, not the total

Per pass, the second arm scored **1, 1, 1, 1, 1, 1, 1, 1, 1, 1**.

Ten passes of a benchmark that changes verdict on two thirds of its
cases between identical runs do not produce a flat line. Something in
that arm was not being decided by a model.

Splitting the total by case showed two large effects pointing opposite
ways and cancelling:

| | before | after |
| --- | --- | --- |
| `slugify` | 6 of 10 | **10 of 10** |
| `wordcount` | 3 of 10 | **0 of 10** |

## The harness was answering, and answering wrongly

All ten `wordcount` runs finished in **zero model steps**. The file they
left behind:

```python
def word_count(prices: list[int]) -> int:
    return len(prices)
```

The task was *"create a new module with a function `word_count(text)`
that counts words"*. What landed counts list items. The same path wrote
the test for it, so the suite agreed, and the run reported:

```
added def word_count(prices) in src/orders.py. Tests passed.
```

Confident, self-consistent, wrong, and the model was never asked. That
is the [false finish]({{ '/investigations/false-finish/' | relative_url }})
shape, arriving from the harness itself rather than from a model.

## Where it came from

`apply_add_function` adds a counter by copying the argument its
neighbours use. In an orders module that argument is `prices`, and for
*"add a function total_lines"* — the case it was built for — that is the
right guess.

It had not been firing on `word_count` for an accidental reason: the
harness used to read the subject of that task as `module`, a noun out of
the instruction. Fixing the subject removed the accident, and the latent
bug came out. **The change did not introduce it. It uncovered it.**

## The fix, and what it was worth

A task that spells `word_count(text)` has already answered the question
that code was guessing at, so when the spelled argument disagrees with
the neighbours there is nothing to add mechanically and the model should
do the work.

| tier 3, twenty runs | worked |
| --- | --- |
| before | 9 of 20 |
| subject fixed, bug exposed | 10 of 20 |
| subject fixed **and** guarded | **19 of 20** |

Ten cases, against a floor of two. The benchmark now prints that floor
itself:

```
This sample resolves a gap of 2 case(s) or more. Identical code scored
1-2 across 10 passes, so a difference of 1 or fewer is noise and must
not be reported as a result.
```

## What to take from it

A total is a sum of things that can move in opposite directions, and the
noise rule this project relies on is a rule about totals. It says when a
difference is too small to believe. It does not say the parts are small.

Two cheap checks would have caught this without the insight:

- **Look at the variance, not only the mean.** A flat line across passes
  of a noisy benchmark means something stopped being decided by the
  model.
- **Count the runs that used no model steps.** They went from none to
  ten, and a run that writes a file without asking the model is either a
  repair the harness is certain of or a bug that looks exactly like one.

The benchmark records both numbers already. Neither was being read.
