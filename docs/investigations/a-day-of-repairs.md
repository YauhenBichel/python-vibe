---
title: A day of repairs, measured
description: Nine harness and instrument fixes in one day took the benchmark from 51 of 75 to 64 of 75. Two of them moved nothing and are kept anyway, and the reason why is the useful part.
permalink: /investigations/a-day-of-repairs/
date: 2026-09-06
type: article
---

Six September was spent fixing the tool rather than asking anything of a
model. The benchmark moved from **51 of 75 to 64 of 75** — fifteen
cases, five passes, `llama3.1:8b`, the same fifteen cases both times.

| tier | | |
| --- | --- | --- |
| 1 one small component | 15/15 | |
| 2 a component and a test | 10/10 | |
| 3 a new module | 8/10 | `wordcount` 3/5 |
| 4 a test for existing code | 10/10 | |
| 5 fix a bug already there | 7/10 | `fix-offbyone` 2/5 |
| 6 platform and operations | 14/20 | `env-flag` 2/5 |

## What was actually wrong

Almost none of it was the model.

**The benchmark punished asking a question**, because nobody was there to
answer, so a run that asked scored a failure whatever it asked.

**The parser fed markdown to Python.** Local weights do not fence their
code; every hosted model does. A hosted 32B scored 1 of 10 and, with
four backticks stripped, 9 of 10. Probing for more of that class then
found five further draft shapes that parsed to nothing — a bold label, a
list marker, a word of explanation after the verb.

**The harness answered a task itself, wrongly.** Asked for
`word_count(text)`, a mechanical path copied the neighbouring function's
argument and wrote `def word_count(prices): return len(prices)` — then
wrote the test to match, so the suite agreed and the run reported "Tests
passed" without consulting the model once. Ten runs of ten.

**A suite that ran nothing counted as a suite that passed.** `unittest
discover` exits 0 when it collected no tests, so a run could finish on
it.

**The model was answered with advice about the wrong field.** Asked to
write tests it appends a test *method*, indented, with no class around
it. That is `unexpected indent` and no file written — and the reply
talked about `Find:`, which the draft did not contain. There was nothing
in it to act on, so the same draft came back, eleven times in a
twelve-step run.

| the reported reproduction, eight runs an arm | before | after |
| --- | --- | --- |
| wrote something | 3/8 | **8/8** |
| the suite ran a test | 2/8 | **8/8** |
| median steps | 12 | 8 |

**The step log named the wrong file.** When an action raised, the
recorded path stayed on the previous step's file. Two things read that
field: the log a person reads, and the repair prompt that tells the
model which file to fix.

**A failed import was reported as a missing function.** `load()` skipped
a module that would not import, so a file that defined the wanted
function and had one bad import said `not found in any module` — which
sends the reader looking for the wrong thing.

## The two that moved nothing

Worth keeping separate from the rest, because a fix that does not move
the score is the normal case here and pretending otherwise would be the
easy lie.

**Keeping the function you were sent to fix.** Asked to fix the bug in
`last_price`, runs were rewriting the file *without* it. Nothing failed
afterwards — the file imported, the suite passed, there was nothing left
to fail.

| twelve runs of `fix-offbyone` | `last_price` ended up missing |
| --- | --- |
| before | 4 of 12 |
| after | **0 of 12** |

The pass rate did not move: 11 of 16 against 10 of 16, one case on a
spread of one. It converts *deleted the function* into *did not fix the
bug*. The same score, and a file left intact rather than damaged.

**Saying which module failed to import.** Across thirty runs after the
change, no failure turned out to be the broken-import kind. The
ambiguity is real and proved in a test; what it buys is a message that
can be trusted next time, not a number.

## What the day was really about

Every one of these is the same shape: **the tool reported something
other than what happened**, and each was invisible until something
outside its assumptions was plugged in. Two instrument faults cost two
days of model comparisons that said nothing about any model. Probing
deliberately for the third found five more in minutes.

The benchmark now prints the gap a sample can actually resolve, so a
difference inside the noise cannot be written up as a result:

```
This sample resolves a gap of 2 case(s) or more. Identical code scored
1-2 across 10 passes, so a difference of 1 or fewer is noise and must
not be reported as a result.
```

Two habits came out of it, both cheap and both from reading numbers that
were already being printed:

- **Read the variance, not only the mean.** A flat line across passes of
  a benchmark that changes verdict two thirds of the time means
  something stopped being decided by the model.
- **Count the runs that used no model steps.** They went from none to
  ten when a mechanical path started answering wrongly. On the current
  suite, fifteen of seventy-five runs use no model, and all fifteen are
  correct.

## Reproducing this

```bash
python scripts/measure/bench.py --model llama3.1:8b --repeat 5
```
