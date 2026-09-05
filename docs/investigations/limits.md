---
title: What the harness cannot fix
description: Seven measurements from one week. A refusal calibrated 0 for 5, a pointer the model ignored 3 times out of 3, platform work at three of four on stock weights, a fine-tune that scored 0 of 4, a week of real work that produced no training data at all, and an excerpt that cut out the very lines the task named.
permalink: /investigations/limits/
date: 2026-09-04
type: article
---

Most of the work on this harness has been finding gaps a refusal or an
oracle can close, and most of them can be closed. These seven could not,
and each says something different about where the line is.

## A refusal that was right and useless

The tool refuses a bot's pull request when the first version number
changes, because a major bump is where breaking changes live and the
title never says so. Five such bumps were merged anyway.

| Bump | Merged | Broken |
| --- | --- | --- |
| actions/checkout 6 to 7 | yes | no |
| actions/github-script 7.1.0 to 9.0.0 | yes | no |
| actions/deploy-pages 4 to 5 | yes | no |
| actions/configure-pages 5 to 6 | yes | no |
| actions/upload-pages-artifact 4 to 5 | yes | no |

Every workflow was green afterwards. **Nought for five.**

The rule's job is "a person should read this", not "this will break", and
by that standard it worked. But five refusals for no finding is friction
that gets a check switched off, and the check that would have been right
was one search. github-script v9 breaks `require('@actions/github')`;
this project never calls it. That was knowable before merging and took a
second to establish.

The same search settled a sixth bump the other way round. A Python
dependency going from 0 to 1 is the shape that should worry somebody, so
the version was installed and every call the project makes was checked
against it: all present, all arguments accepted, both modules importing,
the whole suite passing. Safe, and demonstrably so rather than
hopefully.

A refusal should cost something to earn, and this one now does.

What a pull request's own runs prove is that the workflows they ran
still work. So a major bump is answered with that evidence: if every
workflow using the bumped action ran green on this very pull request,
the thing that would break has already been exercised. Where it has not
— `Pages` is skipped on a pull request, `Celebrate merge` only runs on
merge — the refusal stays and names the workflow nobody ran, which is a
reason someone can act on.

Judged again on the same six bumps, two are allowed and four refused,
each saying what was not proved. Not a clean sweep, and the four are
honest: those workflows genuinely were not run.

The trap in writing it is the one worth remembering. An empty list of
unexercised workflows means every workflow using the action passed. No
workflow using it at all is a different thing entirely, and the first
version returned the same empty list for both — so it waved a Python
dependency going from 0 to 1 straight through, on the grounds that
nothing it touches failed, when nothing it touches had been looked at.
**A rule that silently approves whatever it cannot see is worse than
one that refuses everything.**

## Telling the model does not make it act

A run asked to check a prompt for a leaked credential wrote its own
copy of a check that was already in the tree, three files away, looking
for a variable name instead of the shape of a credential and called by
nothing. The words the task used were in the project already. The
twelve-thousand-character preamble named neither the file nor the
function, so the harness looked for them itself and said where they
were:

```
This project already has something for what the task names:
  "github token" is already in src/harness/secrets.py:21
  "prompt contains" is already in src/harness/model/outbound.py:55
```

The pointer is correct and reaches the model. Three runs out of three
then spent the whole step budget and wrote nothing at all, where before
they wrote the bad function.

So the missing information was real, and supplying it changed the
failure without fixing it. That is worth writing down because it is the
opposite of the usual result here: nearly every other gap closed when
the harness stopped guessing and started checking. This one closed and
nothing followed.

## The domain a specialist model was wanted for

The idea was a model trained only on Python and platform work, small
enough to run on a laptop. Two measurements bear on it.

Narrowing the subject does not make a model smaller. Size is parameter
count, an architecture choice made up front, so "small enough to run
locally" is an input to that plan rather than something the narrowing
buys. The real proposal is to specialise a small model that already
exists.

And the domain in question is already most of the way there without new
weights. Tier 6 is platform and operations work — paths, environment,
configuration, retries — on stock `llama3.1:8b`:

```
env-flag       YY  2/2      6 of 8 over two passes
venv-python    YY  2/2      passed every pass: 2
read-env-file  .Y  1/2      changed verdict: 2
retry          Y.  1/2
```

Around three of four, up from roughly half before the harness work, with
the same weights throughout. The gain came from refusals and oracles.

Against that, this project's own fine-tune scored **0 of 4** on held-out
tasks and 0 of 2 on parsing an action — worse than the base model it
came from. The published grid says the same thing more sharply: a small
fine-tuned model inside a harness built for it matches a 72B at 94.5%,
and the same fine-tune in a generic harness scores 1.0%.

The idea is right in one specific form and the sequencing is the whole
of it. The harness comes first. A fine-tune done alone is not a smaller
win, it is a loss.


## The measurement that could not be taken

The question behind all of this is whether to train a model of your own:
Python and platform work only, small enough to run on a laptop. Deciding
it needs a fine-tune measured against the harness-only baseline, and
that measurement could not be taken, for a reason worth writing down.

```
data/agent-loop/train.jsonl     30 rows
data/python-vibe/train.jsonl    35 rows
```

Sixty-five rows. Not because the data is hard to come by — the harness
records every turn of every run — but because recording was behind a
flag, and nobody passes a flag they have to remember. A week of real
work on this repository, doing exactly the jobs the tool is for,
produced none of it.

A trace not written is not recoverable. The run happened, the model
answered, the file changed, and the record of it is gone.

Recording is on by default now. Measured on a copy of this project, one
run leaves twenty rows and two runs leave forty — **more than the
project had accumulated in its whole life.**

So the answer to the question is not "no". It is that the input does not
exist yet, and the reason it does not exist was a default. At a few
thousand traces the experiment is cheap and decisive: train a LoRA, run
it against the harness-only baseline on tier 6 at `--repeat 5`, and
believe a gap only if it is bigger than four cases.

Until then, the honest position is the one the other three measurements
above point at. The weights have not been the constraint.


## A model failure that was not one

Issue #159 recorded a run asked to add one field to a dict in a long
file. It drafted a `Find:` line that is not in that file at all, was
refused, and sent the same line again. Every failing run of that task
went from `grep` straight to `patch`, so the reading was that the model
guessed instead of looking.

The harness had looked. It located the file and put it in the opening
turn. But the file is 13,476 characters and too long to send whole, so
it went as its first 3,500 and its last 800, middle dropped:

```
is the whole file in the preamble?          True
is the dict the task means in the preamble? False
```

The model was asked to match a line it had never been shown. It was not
guessing out of laziness; it was guessing because the part it needed was
the part that had been cut.

The excerpt is centred on the task's subject now — the longest dotted
name in it, because `result.stopped` says where in a file the work is
while `scripts/bench.py` only says which file. A test proves the dict
arrives.

**And the outcome did not move.** Five runs each side of a task of the
same shape landed it nought times out of five. The defect was real, the
fix is real, and the run still does not finish the job.

The first attempt to measure this was worthless, which is worth saying.
It asked for a field an earlier change had already added, so the check
was true before any run and both sides scored four out of four. Eight
runs measuring nothing, caught only because a task recorded as failing
had suddenly become perfect.


## A rule the model could not see

The architecture test here refuses a function over eighty lines, so the
rule existed. It existed only as a merge gate: the design review the
model reads while working never mentioned length, so nothing told it
until the merge was refused.

The review reports it now, at forty lines rather than eighty — the point
where a function stops being one thing rather than the point where it
cannot be read at all. A warning that fires where the refusal fires is
not a warning. Forty is measured: it flags seven per cent of the
functions here, against sixteen per cent at twenty-five.

Two passes each side of the benchmark: twenty-one of thirty before and
twenty-one of thirty after. **No regression and no gain**, which by now
is the expected shape.

## What these have in common

Six of the seven are cases where the harness knew something, or was
fixed so that it knew something, and it made no difference. A refusal
nobody needed. A pointer nobody used. An excerpt that had been cutting
out the lines the task named, corrected, with the task failing exactly
as often afterwards. A length rule the model could finally see, and the
same score either side. Weights that were never the constraint. And a
week of real work that recorded nothing, because the flag that would
have kept it was off.

The one that worked, worked by running something: a dependency's major
bump was cleared by installing the version, calling every function the
project uses against it, and running the suite.

The seventh has since become useful, and it is worth saying how. The
refusal on a major bump stopped guessing from a version number and
started reading what the pull request's own runs had already proved.
That is the same move: not knowing more, but checking.

What closes a gap is an oracle — something that runs and comes back true
or false. What does not close a gap is telling the model more.
