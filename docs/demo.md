---
title: Demo
description: python-vibe run over eleven everyday tasks on one small project. Real output, including the cases it does not finish.
permalink: /demo/
date: 2026-08-29
---

# Demo

Every case below was run against `demo/orders`, a small project with a few deliberate problems in it, using `llama3.1:8b` through Ollama on one laptop. Each case started from a fresh copy, so no case could see another one's changes.

Reproduce it:

```bash
ollama pull llama3.1:8b
python scripts/run/demo.py --markdown docs/demo.md
```

Two columns matter. **Agent says** is whether it reported that it had finished. **Checked** is a separate test run against the files afterwards. The two do not always agree. In one run the bug was fixed correctly, and the report described writing a test that was never written.

The model does not give the same answer twice. Rebuilding this page changes which cases pass. `write-tests` and `rename` have each both passed and failed on different runs, while `bugfix`, `dry-run` and `vague` have not yet failed. Read the table as one run, not as a score.

Four results do not depend on the model. The first two cases need no model at all. `dry-run` changes nothing, because every change is refused before it happens. `vague` stops and asks which file to work on. `review` reports without editing.

## Summary

| Case | Task | Agent says | Checked | Steps | Files changed |
| --- | --- | --- | --- | --- | --- |
| [brief](#brief) | Size up an unfamiliar repo | no model needed | — | — | none |
| [layout](#layout) | Find out why a tree is hard to read | no model needed | — | — | none |
| [question](#question) | Ask what a function does | yes | not checked | 1 | none |
| [bugfix](#bugfix) | Fix a bug no test covers | yes | passed | 0 | `src/orders.py` |
| [add-feature](#add-feature) | Add a function and a test | no (steps) | passed | 8 | `src/orders.py`, `tests/test_orders.py`, `pkg/orders_concern.py` |
| [write-tests](#write-tests) | Cover something that has no test | no (steps) | failed | 8 | none |
| [rename](#rename) | Give an opaque name a real one | yes | passed | 0 | `src/util.py` |
| [review](#review) | Review one file without changing it | no (steps) | passed | 8 | none |
| [dry-run](#dry-run) | See what it would do, change nothing | no (steps) | passed | 8 | none |
| [vague](#vague) | Give it a task that says nothing | no (question) | passed | 0 | none |
| [scoped](#scoped) | Stay inside one folder on a bigger tree | yes | not checked | 1 | none |

## brief

**Size up an unfamiliar repo.** How big the project is, which files are in it, and which skills
would apply. No model is called.

```
Mode: small  files=8  size=1.7 KB
Small project — explore, edit, and run on this laptop.
You can read every listed file. Prefer Action: patch for one-line fixes.
Questions: if you see # auto-read, Action: done. Else read one file, then done. Do not edit.
Files:
  README.md  491 B
  src/__init__.py  68 B
  src/orders.py  467 B
  src/render.py  193 B
  src/report.py  155 B
  src/util.py  67 B
  tests/__init__.py  0 B
  tests/test_orders.py  311 B
```

Skills available: `add-feature`, `analyze-data`, `answer-question`, `ask-when-unclear`, `call-http`, `fix-smell`, `merge-pr`, `new-package`, `open-pr`, `read-issue`, `readable-layout`, `refactor-split`, `review-code`, `review-design`, `stay-scoped`, `write-algorithm`, `write-paths`, `write-script`, `write-tests`

## layout

**Find out why a tree is hard to read.** Two files importing each other, a folder with too many files in
it, one file much larger than the rest, and missing tests.

```
layout: 1 finding(s), worst first.
  [cycle] render.py and report.py import each other

Next move (do only this one): Move what they share into a new module both import. Action: grep Query: def .*  Path: render.py
```

## question

**Ask what a function does.** The function is found and read for the model before its first turn.

```
python-vibe run ./orders "what does apply_discount return?"
```

Skills loaded: `answer-question`

Actions: `done`

What it reported (done, 12.0s):

```
int
```

## bugfix

**Fix a bug no test covers.** Naming a file in the task opens that file, and no other file may
then be changed.

```
python-vibe run ./orders "find a real NameError in src/orders.py and fix it"
```

Actions: 

Changed: `src/orders.py`

Files differing from the checked-in project:

- `~ src/orders.py`

Separate check: **passed**

What it reported (done, 0.1s):

```
bound unique NameError typo (subtotl → subtotal) in src/orders.py. Tests passed.
```

## add-feature

**Add a function and a test.** The function is added, then a test for it, then the tests are run.

```
python-vibe run ./orders "add a function total_lines(prices) that counts the prices, and a unit test"
```

Skills loaded: `add-feature`, `write-tests`

Actions: `patch` → `patch` → `run` → `patch` → `edit` → `edit` → `patch` → `patch`

Changed: `src/orders.py`, `tests/test_orders.py`, `pkg/orders_concern.py`

Files differing from the checked-in project:

- `+ pkg/orders_concern.py (new file)`
- `~ src/orders.py`
- `~ tests/test_orders.py`

Separate check: **passed**

What it reported (steps, 19.7s):

```
stopped after 8 steps
```

## write-tests

**Cover something that has no test.** One test is added that sets up its inputs, calls the function, and
checks the result. The import line is corrected automatically.

```
python-vibe run ./orders "write tests for apply_discount in src/orders.py"
```

Skills loaded: `write-tests`

Actions: `locate` → `patch` → `unparsed` → `patch` → `edit` → `patch` → `unparsed` → `patch`

Refused by the harness:

- unparsed
- unparsed

Separate check: **failed** — AssertionError: no test names apply_discount

What it reported (steps, 7.7s):

```
stopped after 8 steps
```

## rename

**Give an opaque name a real one.** The new name is written where the function is defined, not in the
first file that mentions it.

```
python-vibe run ./orders "rename calc to multiply in src/util.py"
```

Skills loaded: `fix-smell`

Actions: 

Changed: `src/util.py`

Files differing from the checked-in project:

- `~ src/util.py`

Separate check: **passed**

What it reported (done, 0.1s):

```
renamed def calc → def multiply in src/util.py. Tests passed.
```

## review

**Review one file without changing it.** A review reports what it finds. Any attempt to edit is refused.

```
python-vibe run ./orders "review src/orders.py for bugs"
```

Skills loaded: `review-code`

Actions: `review-design` → `review-design` → `done` → `edit` → `done` → `edit` → `done` → `edit`

Refused by the harness:

- not done. Structure findings remain. Action: edit Path: pkg/<new_concern>.py with one function. Then the harness will re-scan.
- Reviews do not edit. Action: done Summary: name the defect and quote the line it is on.
- not done. Structure findings remain. Action: edit Path: pkg/<new_concern>.py with one function. Then the harness will re-scan.
- Reviews do not edit. Action: done Summary: name the defect and quote the line it is on.
- not done. Structure findings remain. Action: edit Path: pkg/<new_concern>.py with one function. Then the harness will re-scan.
- Reviews do not edit. Action: done Summary: name the defect and quote the line it is on.

Separate check: **passed**

What it reported (steps, 15.9s):

```
stopped after 8 steps
```

## dry-run

**See what it would do, change nothing.** With writes turned off, every change is refused before it happens.

```
python-vibe run ./orders "fix the NameError in src/orders.py"
```

Actions: `patch` → `done` → `patch` → `done` → `patch` → `done` → `patch` → `done`

Refused by the harness:

- This run is read-only. Do not patch, edit, or run. Action: done Summary: say what you would change and why.
- Nothing was changed. Action: patch Path: src/orders.py with a Find: line copied whole from the file and a Replace:. If the file is already correct, Action: done Summary: say which line is already correct.
- This run is read-only. Do not patch, edit, or run. Action: done Summary: say what you would change and why.
- undefined name subtotl in src/orders.py. Action: patch Path: src/orders.py Find: subtotl Replace: the name you assigned.
- This run is read-only. Do not patch, edit, or run. Action: done Summary: say what you would change and why.
- undefined name subtotl in src/orders.py. Action: patch Path: src/orders.py Find: subtotl Replace: the name you assigned.
- This run is read-only. Do not patch, edit, or run. Action: done Summary: say what you would change and why.
- undefined name subtotl in src/orders.py. Action: patch Path: src/orders.py Find: subtotl Replace: the name you assigned.

Separate check: **passed**

What it reported (steps, 18.5s):

```
stopped after 8 steps
```

## vague

**Give it a task that says nothing.** The task names no file and no function, so it asks instead of
guessing.

```
python-vibe run ./orders "clean this up"
```

Skills loaded: `ask-when-unclear`

Actions: 

Separate check: **passed**

What it reported (question, 0.0s):

```
"clean this up" does not name a file or a function. Which file should I work on?
  1. src/orders.py
  2. tests/test_orders.py
```

## scoped

**Stay inside one folder on a bigger tree.** Searching and listing stay inside the folder given by --scope.

```
python-vibe run ./orders "what does render_line return?"
```

Skills loaded: `answer-question`

Actions: `done`

What it reported (done, 6.0s):

```
"str"
```
