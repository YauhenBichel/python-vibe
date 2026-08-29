---
title: First-run four jobs
description: The four advertised commands on demo/orders. First they failed. Then the harness finished three, then four, without a model. 29–30 Aug 2026.
permalink: /investigations/first-run-four/
date: 2026-08-29
type: article
---

# First-run four jobs

**Question.** Do the four commands on [Start]({{ '/start/' | relative_url }})
work as a daily user would type them?

**Answer.** After the same-evening harness work: **yes, on `demo/orders`**,
for ask / already-covered tests / a unique NameError / add a count next
to `prices`. A named leftover NameError (`stauts` in `def status`) asks
what to return. It does not invent `return "ok"`.

Related: [Live scenarios]({{ '/scenarios/' | relative_url }}) ·
[Everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}) ·
[Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}) ·
[What to improve]({{ '/investigations/what-to-improve/' | relative_url }}).

## The four commands: first fail, then mechanical pass

Same laptop, `llama3.1:8b`, fresh copies of `demo/orders`.

| Command | First run (evening) | After the harness |
| --- | --- | --- |
| `ask "what does compute_total return?"` | `"int"` | A sentence that quotes `int` and says it sums the line prices |
| `run "write tests for apply_discount"` | Duplicate test below `if __name__`; suite still ran the old two | `already has a test`. Nothing written. Suite green |
| `run "find the NameError and fix it"` | Model edited three files | `subtotl → subtotal` in `orders.py`. No model |
| `run "add a function total_lines and a test"` | Opened a file, suite red, then asked | `def total_lines(prices)` + AAA test. No model |

A later re-measure (same night) confirmed all four still green, and
`find the NameError in src/orders_controller.py` stopped on a question
instead of twenty patches.

## Write tests

**Yes**, when the task names a function or class.

- Already covered: the run ends. No dead append.
- Uncovered and callable with simple args: one AAA method, import fixed,
  suite run. `write tests for OrderService` created a new test file and
  the check passed.
- No symbol, or fixtures / files / HTTP: the 8B invents a path. Do not
  use this job for “add coverage to the package.”

## Bugs and smells

**Yes**, for a short list.

- Unique NameError typo (`subtotl` next to `subtotal =`). Named file or
  a tree scan when the task names no file.
- Named rename (`rename calc to multiply in src/util.py`).
- Named-file review quotes compiler findings and does not edit.

**No**, for a real review.

- `stauts` inside `def status`: the method name is not in scope. Binding
  it still raises. The harness asks what to return.
- Logic bugs that still parse.
- A hundred-file walk (once: a hundred “no issues”).
- “Find code smells” with no symbol. The 8B has invented names that were
  not in the file.

## What the harness closed vs what training will not

The four Start commands went from 0/4 shippable to 4/4 working on this
tree **without new weights**. Three of the four finish with no model call
at all, which is why they take a tenth of a second and give the same
answer every time; `ask` still calls the model, and is held to an answer
that says what the function computes. The leftover controller job became
a question, not a guessed literal.

Read those four as four commands, not as a score. Running the fifteen
benchmark cases three times on unchanged code changed the verdict on ten
of them, so a single pass cannot separate a real gain from a rerun. The
rows that hold still between runs are the ones that never call the
model, and three of these four are those.

Live parse the same night (`eval_everyday.py --live`, `llama3.1:8b`):
**8 / 15** first Actions. Offline fixtures were 11/11 parse, 2/2 gold
`/run`, 1 KB bugfix fixture ready. That is above the 50% floor and
**not** everyday-ready. Everyday-ready still means beating an untuned 8B
on parse **and** a real ≥1 KB fix.

Do not train more 0.5B steps. Do not train an 8B LoRA on thirty seed
rows. See [fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}).

A copy-paste article from these measurements is kept in `drafts/` in
the repository, so it is not published here as well.
