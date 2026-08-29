---
title: Scenarios
description: What you type, and what happened on demo/orders. Four everyday commands, each checked after the run.
permalink: /scenarios/
date: 2026-08-29
---

# Scenarios

29 August 2026, one laptop, `llama3.1:8b` through Ollama. Each command ran
against a **fresh copy** of `demo/orders`, so no job could see another's
files.

Read the **Checked** column, not the summary. It is a separate test
run after the command finished, because the summary has been wrong in
both directions: one run reported `stopped after 8 steps` on a bug it
had fixed, and an earlier one asked a clarifying question after it had
already written code that broke the project's tests.

## The four commands on Start

| You type | What happened | Checked | Time |
| --- | --- | --- | --- |
| `python-vibe brief` | Listed 10 files, 2.9 KB. No model. | — | instant |
| `python-vibe ask "what does compute_total return?"` | Answered `"int", computing the sum of line prices of one order`. The bare type on its own is sent back. | nothing written | 2–9 s |
| `python-vibe run "write tests for apply_discount"` | Saw the test was already there and declined to add a second. No model. | nothing written, suite green | 0.1 s |
| `python-vibe run "find the NameError and fix it"` | Bound `subtotl` → `subtotal` in `src/orders.py`. No model. | fixed, and `total_with_tax([10])` is `12.0` | 0.1 s |
| `python-vibe run "add a function total_lines and a test"` | Added `def total_lines(prices)` and an AAA test. No model. An earlier run the same evening opened a file and left the suite red. | `total_lines([10, 20]) == 2`, suite green | 0.1 s |

Four of the five finished **without calling the model**. That is why
they are fast and why they are the same every time. `ask` is the one
that needs it, and the model is held to an answer that says what the
function computes rather than reading its annotation back.

The add job used to guess a file-line counter. The harness now matches the
new function to the usual neighbor argument (`prices`) and refuses `open(`.

```python
def total_lines(prices: list[int]) -> int:
    return len(prices)
```

## The same jobs, said more precisely

| You type | What happened | Checked | Time |
| --- | --- | --- | --- |
| `python-vibe run "find a real NameError in src/orders.py and fix it"` | Bound `subtotl` → `subtotal`. No model. | passed | 0.1 s |
| `python-vibe run "add a function total_lines(prices) that counts the prices, and a unit test"` | Same result as the short wording, by the same mechanical route. No model. | passed | 0.1 s |
| `python-vibe run "write tests for OrderService in src/orders_service.py"` | Six steps. New file `tests/test_OrderService.py`. The summary was the single word `done`. | passed | 23 s |
| `python-vibe run "find the NameError in src/orders_controller.py and fix it"` | `stauts` reads as `status`, which is the method's own name and not in scope in its body. The harness asks what was meant. Answering `ok` writes `return "ok"`. Answering `status` is still refused. With `--dry-run`, or through `ask`, it reports what it would write and changes nothing. No model. | question until you answer; then the literal you gave | instant |

The short `add` command now matches the precise one: both write
`total_lines(prices)` and a test. The controller NameError still has no
safe mechanical bind; the harness asks instead of guessing `return "ok"`.
If you answer, that answer is written without loading the model.

## What the harness will not guess

`demo/orders` has two planted `NameError`s: `subtotl` in
`total_with_tax`, and `stauts` in `OrdersController.status`.

The first is repaired without a model, because exactly one name in scope is
one edit away. The second is not, and the reason is worth stating: the
nearest name to `stauts` is `status`, which is the **method's own name**.
It is not in scope inside the method body, so binding to it would produce
`return status` — code that still raises, from a repair that takes a tenth
of a second and reports success. The harness asks what it should return.
A given answer is written as that value. `status` as the answer is still
refused.

## Reproduce

```bash
ollama pull llama3.1:8b
pip install -e .
python scripts/demo.py --case brief --case question --case write-tests \
  --case bugfix --case add-feature --case cover-service --case controller-bug
```

The demo runner uses the precise wording. The loose wording in the first
table is what someone actually types, which is why it is on this page.

Write-up of the same evening:
[First-run four jobs]({{ '/investigations/first-run-four/' | relative_url }}).
Every measured run:
[Experiments]({{ '/investigations/experiments/' | relative_url }}).

The older eleven-case table, including review and dry-run, is on
[Demo]({{ '/demo/' | relative_url }}).
