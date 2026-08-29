---
title: Live scenarios
description: A laptop run of the four everyday commands against demo/orders, with a separate check on each result. Includes the one that writes broken code.
permalink: /scenarios/
date: 2026-08-29
---

# Live scenarios

29 August 2026, one laptop, `llama3.1:8b` through Ollama. Each command ran
against a **fresh copy** of `demo/orders`, so no job could see another's
files.

Read the **Checked** column, not the summary. It is a separate test run
after the command finished. One run below reported a question and had
already written code that broke the project's tests.

## The four commands on Start

| You type | What happened | Checked | Time |
| --- | --- | --- | --- |
| `python-vibe brief` | Listed 10 files, 2.9 KB. No model. | — | instant |
| `python-vibe ask "what does compute_total return?"` | Answered `"int"`. That is the annotation. It did not say the function sums the line prices. | nothing written | 3 s |
| `python-vibe run "write tests for apply_discount"` | Saw the test was already there and declined to add a second. No model. | nothing written, suite green | 0.1 s |
| `python-vibe run "find the NameError and fix it"` | Bound `subtotl` → `subtotal` in `src/orders.py`. No model. | fixed, and `total_with_tax([10])` is `12.0` | 0.1 s |
| `python-vibe run "add a function total_lines and a test"` | Wrote a function, wrote a test, left the suite red, then asked what was meant. Exit code 1. | **failed** | 16 s |

Three of those four finished **without calling the model at all**. That is
why they are fast and why they are the same every time.

The fifth is the one that needed the model to decide what the words meant,
and it is the one that went wrong.

## The one that went wrong

```bash
python-vibe run "add a function total_lines and a test"
```

`total_lines` is ambiguous in an orders module: lines of a file, or a count
of the order lines. The run picked the first, wrote it, wrote a test for it,
and then asked which was meant.

```python
def total_lines(file: str) -> int:
    with open(file, 'r', encoding="utf-8") as f:
        return sum(1 for line in f)
```

```python
    def test_total_lines_returns_the_correct_count(self) -> None:
            file = 'path_to_test_file.txt'
            got = total_lines(file)
            self.assertEqual(got, 10)
```

The test names a file that does not exist and expects a number nobody
measured. Before the command, the project's suite was green with two tests.
After it, three tests and one error.

The run ended with `Action: ask` and exit code 1, so the exit code is
honest. The files had already been written by then.

A second run of the same command wrote both files again and finished by
repeating the skill's own template text back as its question:

```
one short question, when the task could mean two different things
  1. the first reading
  2. the second reading
```

Same command, same model, two different endings. Neither produced code
worth keeping.

## The same jobs, said more precisely

| You type | What happened | Checked | Time |
| --- | --- | --- | --- |
| `python-vibe run "find a real NameError in src/orders.py and fix it"` | Bound `subtotl` → `subtotal`. No model. | passed | 0.1 s |
| `python-vibe run "add a function total_lines(prices) that counts the prices, and a unit test"` | Seven steps. Wrote `total_lines` and a test. | passed | 14 s |
| `python-vibe run "write tests for OrderService in src/orders_service.py"` | Six steps. New file `tests/test_OrderService.py`. The summary was the single word `done`. | passed | 23 s |
| `python-vibe run "find the NameError in src/orders_controller.py and fix it"` | Eight steps. Refused three times for trying to edit `src/orders.py` instead of the named file. Ran out of steps and reported `stopped after 8 steps`. | **passed** — the fix was real | 22 s |

Naming the file, and naming the argument, is the difference between the
first table's failure and the second table's pass.

The last row is worth reading twice. The command reported that it had run
out of steps, and the separate check found the bug fixed. The summary is
not the result. That is the whole reason for the Checked column.

## What the harness will not guess

`demo/orders` has two planted `NameError`s: `subtotl` in
`total_with_tax`, and `stauts` in `OrdersController.status`.

The first is repaired without a model, because exactly one name in scope is
one edit away. The second is not, and the reason is worth stating: the
nearest name to `stauts` is `status`, which is the **method's own name**.
It is not in scope inside the method body, so binding to it would produce
`return status` — code that still raises, from a repair that takes a tenth
of a second and reports success. The harness leaves that one to the model.

## Reproduce

```bash
ollama pull llama3.1:8b
pip install -e .
python scripts/demo.py --case brief --case question --case write-tests \
  --case bugfix --case add-feature --case cover-service --case controller-bug
```

The demo runner uses the precise wording. The loose wording in the first
table is what someone actually types, which is why it is on this page.

The older eleven-case table, including review and dry-run, is on
[Demo]({{ '/demo/' | relative_url }}).
