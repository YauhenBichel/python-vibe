---
title: When a run says done and means nothing
description: A fifth of failures reported success having written nothing. Measured on one task, 5 runs in 10 claimed work they had not done; after two fixes, 0 in 10.
permalink: /investigations/false-finish/
date: 2026-08-30
type: article
---

The worst thing a run can do is not fail. It is finish, report success,
and leave the file exactly as it was. A failure costs a person nothing
but the time it took. A false finish costs them the time it took plus
the time to discover it, and the only way to discover it is to go and
look.

Counting stop reasons across 45 benchmark runs put a number on it:
**two of the nine failures reported `done`**. No stop reason catches
that shape, because the run does not think anything went wrong.

## What it looked like

The task was a single line inside an existing dict, in a 330-line file:

> in scripts/bench.py add the field stopped to the dict that run
> returns, taking its value from result.stopped

Given three times on a clean copy, it succeeded **none** of them, and
failed differently each time.

1. Twenty steps, budget spent, file byte-identical afterwards.
2. Refused, then repeated. The drafts were `Append` bodies containing a
   literal `...` placeholder, and a `Find` string that is not in the
   file. Step 3 was byte-identical to step 1.
3. **`Action: done` — `Summary: The line is already correct.`** The
   field was never added.

The third is the one worth fixing. The other two are honest.

## Two causes, and neither was a missing guard

**A guard already existed.** It refused a `done` on a change task that
changed nothing, once, with this message:

> If the file is already correct, Action: done Summary: say which line
> is already correct.

The reply was *"The line is already correct."* It names no line. It was
accepted. **The refusal handed the model the words and the model handed
them back.**

So the escape has to be shown rather than asserted: the closing summary
must copy a line that is really in the file. Copying a line is something
only a reader can do.

That alone did not work. Measured over five runs it was still 2 in 5,
because the model cleared the new bar by quoting `if __name__ ==
"__main__":`, which is in every script ever written. Reading the file is
not reading the right part of it.

What is checkable without understanding the change: **nothing can be
already correct about adding a name that is not there.** A task naming
`result.stopped`, and a file that does not contain it, cannot be
finished. Only dotted or underscored words count, so prose like "fix
app.py for Windows" is left alone and the rule stays quiet where it
cannot prove anything.

| on the task above, ten runs each | reported success having changed nothing |
| --- | --- |
| before | **5 of 10** |
| quoting a line required | 2 of 5 |
| plus the absent-name check | **0 of 10** |

A gap of five is above the four-case threshold this project treats as
noise.

## The second cause was not in the model at all

A different run answered *"already has a test for check. Tests passed."*
three times out of three, wrote nothing, and never called the model.

The harness had taken `check` — from the words *"add a **check**"* — for
a function name, then asked whether a test file already covered it with
a substring match against the whole file, comments and docstrings
included.

| in this project's own test files | count |
| --- | --- |
| contain the word `check` | **17** |
| actually call `check(` | **5** |

The run finished on English prose. And because the answer came from the
harness rather than from a model turn, the guard above never saw it:
fixing the first cause did nothing for this one, which was checked
rather than assumed.

A call, or a test named after the symbol, is the difference between a
file that mentions something and a file that exercises it. An import
alone is neither, which is a distinction this project has had to learn
once already.

## What is still wrong

With both fixed, the same task produces this and stops after twenty
steps:

```python
def reject_github_tokens_in_prompt(prompt: str) -> bool:
    return 'github_token' in prompt
```

Two things are wrong with it, and calling them the model's ceiling was
too quick. **Nothing calls it**, so the file parses and the suite stays
green because a function nobody calls cannot fail. That is now refused
at the finish — though honestly, on this task the rule never fires,
because the run never reaches `done`. And it **reinvents a check the
project already had**: the shape of a GitHub token is written down here
already, and nothing put it in front of the model. There is a rule that
stops a module being written twice under two names. There is no
equivalent for a function.

## What it cost to find

Every one of these came from giving python-vibe the same job that had
just been done by hand. None came from the test suite. The suite was
green throughout, which is the point: a function nobody calls, and a run
that changes nothing, are both invisible to a green suite.
