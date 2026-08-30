---
title: Small steps, measured
description: Splitting one task into a chain of easy ones did not help an 8B, and took twice as long. The loop was already a chain; splitting it into separate runs threw away the memory that made it one.
permalink: /investigations/small-steps/
date: 2026-08-30
type: article
---

The idea under test: local models are not very good, so give them a
chain of very easy tasks instead of one hard one, and build the answer
out of the replies.

It is a reasonable idea and it is worth measuring rather than arguing
about, because the arithmetic cuts both ways. Easier steps should each
succeed more often. But a chain fails if any link fails, so three steps
at 85% is 61%, and the split has to buy more than it costs.

## The measurement

One benchmark case, `word_count`, on the benchmark's own small fixture.
It is tier 3 and genuinely composite: create a module, write a function,
write a test for it. Three arms, eight runs each, `llama3.1:8b`, same
project and same success check throughout. Success means the function
actually runs and returns 3 for `'a b c'`.

**A.** One instruction: *create a new module with a function
word_count(text) that counts words, and a unit test for it.*

**B.** The same work split in two and sent blind: make the module and
the function, then write the test.

**C.** The same split, but each step checked before the next one starts,
retried once with the failure named, and the second step skipped when
the first never produced anything to test.

| | function works | with a test | average |
|---|---|---|---|
| A one instruction | **5 of 8** | 5 of 8 | 20s |
| B split, sent blind | 4 of 8 | 4 of 8 | 46s |
| C split, checked and retried | 4 of 8 | 4 of 8 | 42s |

A gap of one on eight runs is noise here — ten of the fifteen benchmark
cases change verdict between identical runs. So the honest reading is
that splitting bought **nothing**, and cost about twice the wall clock.

Checking each step and retrying it did not rescue the split either. C
scored the same as B.

## Why it did not help

Because the loop was already doing it.

A run is not one request. It is up to twenty turns, each one a single
action — look for a file, read it, change it, run the tests — with a
refusal and a next instruction after each. That is already a chain of
very small steps. Splitting the task from outside does not add
decomposition. It adds a second copy of it.

And it takes something away. `Conversation` is built inside the run:

```python
def _work_with_the_model(self, run: RunState) -> AgentResult:
    memory = Conversation(budget_tokens=CONTEXT_TOKENS, ...)
```

One per run, so two runs are two memories. Every step in arms B and C
started from nothing: the file the harness located, the opening turn
that carries the code, the refusals already earned — all discarded and
paid for again. The part of the idea that says *build on the replies*
is exactly the part a chain of separate runs cannot do.

That also explains the clock. B and C are slower because they redo the
opening work, not because they think harder.

## What the idea is right about

Memory is the load-bearing piece, and it is already treated that way.
`Conversation` keeps the opening turn whatever else goes, because that
is the only turn carrying the code, and drops the middle, where a model
has already been told it used the wrong verb four times. Before that
existed, Ollama's own 4096-token default silently dropped the oldest
message — the opening — and the run lost the part it had done work to
assemble and said nothing.

So the instinct is sound. It is just already spent here.

## What would actually be worth trying

Not this. What was measured is splitting a task across separate runs,
and that is the version that throws the memory away. The untested
version is decomposition **inside** one run: the harness naming
sub-goals for itself and carrying each result into the next turn, with
one memory throughout.

That is a different change and this page does not claim anything about
it. It would need the loop to hold a goal it can finish part of, which
nothing in the harness does today.

## What this does not show

One task, one model, eight runs an arm. It shows that splitting this
task into separate runs did not help, and why the reason is structural
rather than accidental. It does not show that no decomposition helps,
and a bigger gap on a harder task would change the answer.
