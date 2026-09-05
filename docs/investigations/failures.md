---
title: Where the failures are
description: Seventy-five runs, classified. A third fail, two thirds of those wrote the wrong code, none of them claimed success having written nothing, and a quarter of every run is the harness saying no.
permalink: /investigations/failures/
date: 2026-09-05
type: article
---

Seven harness changes were measured over one week and six of them moved
nothing. That is a strange result to keep collecting without asking the
obvious question: **what is actually failing?**

Two measurements answer it. Seventy-five runs — fifteen benchmark cases,
five passes — classified by what the run left behind. And eight hundred
and thirty-six model turns from the recorded traces, classified by what
the model was sent.

## A third of runs fail

| | runs |
| --- | --- |
| worked | 51 |
| failed | **24 of 75 (32%)** |

## Two thirds of the failures are wrong code

| Why it failed | Share |
| --- | --- |
| wrote something, but not the thing asked for | **42%** |
| wrote nothing at all | 33% |
| wrote something, it did not do the job | 25% |

Sixty-seven per cent of failures are a file that changed and a job that
did not get done. That matters more than the headline rate, because it
says what kind of fix could help.

A refusal catches a draft that is *recognisably* wrong: a name that says
nothing, a `Find:` line copied from memory, a module written twice. It
cannot catch a draft that is plausible and wrong, because nothing
deterministic can tell those apart. Only running the code can, and the
harness already does — the suite runs, and a red suite is one of the
verdicts above.

So the remaining two thirds are not waiting for another rule.

## Nothing claims success having done nothing

Of the twenty-four failures, eight ended by saying `done`. Every one of
them had written a file:

```
env-flag      writes=2  AssertionError: 0
venv-python   writes=1  venv_python not found in any module
initials      writes=2  AssertionError: A L
```

**Nought of eight wrote nothing.** That was the commonest and worst
shape a week ago — a run reporting success with the file untouched, at
two of nine failures — and it is gone at seventy-five runs. The rule
that closed it asks a run to quote a line from the file it says was
already correct, and to prove that a name it was asked to add is
actually there.

That is the one measured gain of the week, and it is worth being precise
about what it gained: not a higher pass rate, but no lies about it.

## Where the failures sit

| Tier | Failed |
| --- | --- |
| 1 one small component | 4 of 15 |
| 3 a new module with a test | 5 of 10 |
| 5 fix a bug already there | 4 of 10 |
| 6 platform and operations | **11 of 20** |

Platform work is still the hardest, at a little over half.

## A quarter of every run is the harness saying no

Eight hundred and thirty-six turns over seventy runs — about twelve
turns a run.

| What the model is sent | Share |
| --- | --- |
| a tool result | 67% |
| **a refusal or a nudge** | **23%** |
| the opening turn | 8% |
| the draft did not parse | 1% |

What it is told, most often:

```
58  run the tests before finishing
36  read the file before patching it
32  that is the wrong file
11  the draft did not parse
10  too late to ask, files are changed
10  you already ran that skill
```

The second line is worth a note. When that rule was added, the write-up
called it "narrower than it sounds", reasoning that a task naming a file
gets that file located and so the rule would rarely fire. The reasoning
about the mechanism was right and the guess about the frequency was
wrong: it is the second most common thing the harness says, because
models reach for a *second* file far more often than expected.

## What this changes

The seven measurements that moved nothing now have an explanation rather
than a shrug. Two thirds of what still fails is the model writing
plausible, wrong code, and no deterministic rule separates plausible and
wrong from plausible and right. The harness has taken the failures it
can take.

That is an argument for the weights, and it is the first one on this
site that comes from measuring the failures rather than from hoping.
It also sets the bar: a fine-tune has to move the sixty-seven per cent,
not the honesty, because the honesty is already fixed.

## Reproducing this

```bash
python scripts/measure/bench.py --repeat 5
python scripts/weights/collect_traces.py --passes 4
```

The first prints a row per run with what it wrote and why it failed. The
second gathers the turns; both sets of numbers here come from reading
those two files and nothing else.
