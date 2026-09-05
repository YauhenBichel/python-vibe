---
title: Live demo
description: A real asciinema recording of python-vibe on demo/orders, plus a same-day 8B daily run on a logic bug. 5 September 2026.
permalink: /live/
date: 2026-09-05
---

# Live demo

A real shell recording. 5 September 2026. One laptop. A fresh copy of
`demo/orders`. Daily model: Ollama `llama3.1:8b`. Only **ask** called
it. The two writes are **harness demos** — a unique typo and a template
add, no model. They stay on the recording because they are the same
every time. Daily `run` is 8B: write, run the suite, send a failing
traceback back once.

![python-vibe on demo/orders — brief, layout, ask, fix, add]({{ '/media/live-demo.gif' | relative_url }})

Recorded with asciinema. The GIF loops; the log below is the same
session, static. Replay the cast:

```bash
asciinema play docs/media/live-demo.cast
```

Re-record it (needs Ollama `llama3.1:8b`):

```bash
PYTHONPATH=src python scripts/measure/record_live.py
```

The same jobs from **Tasks: Run Task** are on
[VS Code]({{ '/vscode/' | relative_url }})
(`docs/media/vscode-demo.gif`).
From Cursor chat or Tasks: [Cursor]({{ '/cursor/' | relative_url }})
(`docs/media/cursor-demo.gif`).

Type the same thing after [Start]({{ '/start/' | relative_url }}):

```bash
source .venv/bin/activate
cd demo/orders
python-vibe brief
python-vibe layout
python-vibe ask  "what does compute_total return?"
python-vibe run  "find the NameError and fix it"
python-vibe run  "add a function total_lines and a test"
```

If the shell says `command not found: python-vibe`, the venv is not
active. Activate it in every new terminal.

A second recording, same day, is a **daily** `run`: an 8B write on a
logic bug, then the suite. That is not a harness demo.

![python-vibe daily run — fix compute_total]({{ '/media/daily-run.gif' | relative_url }})

```
$ python-vibe run "fix compute_total in src/app.py so it sums the rows"
Action: patch Path: src/app.py Find: return 0 Replace: return sum(rows)
Action: done
I fixed the compute_total function in src/app.py to return the sum of
the rows instead of always returning 0.
```

Replay: `asciinema play docs/media/daily-run.cast`.
Re-record: `PYTHONPATH=src python scripts/measure/record_daily.py`.

The eleven-case table, including misses, is still on
[Demo]({{ '/demo/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#size-the-folder">Size the folder</a></li>
  <li><a href="#what-is-tangled">What is tangled</a></li>
  <li><a href="#ask-a-question">Ask a question</a></li>
  <li><a href="#fix-the-nameerror">Fix the NameError</a></li>
  <li><a href="#add-a-function">Add a function</a></li>
  <li><a href="#daily-run">Daily run</a></li>
</ol>
</nav>

## Size the folder

No model. 0.2 s.

```
$ python-vibe brief

10 Python and Markdown files, 2.9 KB in total.
Small enough that python-vibe can read all of it, so you can ask about any part.

Files:
  README.md  685 B
  src/__init__.py  68 B
  src/orders.py  467 B
  src/orders_controller.py  568 B
  src/orders_service.py  285 B
  src/render.py  193 B
  src/report.py  155 B
  src/util.py  67 B
  tests/__init__.py  0 B
  tests/test_orders.py  511 B

python-vibe has 23 skills it can apply. It picks them from the wording of
your task; you do not choose them.
```

## What is tangled

No model. 0.1 s.

```
$ python-vibe layout

layout: 1 finding(s), worst first.
  [cycle] src/render.py and src/report.py import each other

Next move (do only this one): Move what they share into a new module both
import.
```

## Ask a question

`llama3.1:8b`. The first draft was only `"int"`. The harness sent that
back. The second draft named what the function computes.

```
$ python-vibe ask "what does compute_total return?"
ollama:llama3.1:8b  project /tmp/orders  mode small

--- step 1 ---
Action: done
Summary: "int"

too thin. Action: done Summary: quote int and say in a sentence what it
computes, from the code you read.

--- step 2 ---
Action: done
Summary: "int", which computes the sum of the line prices of one order.

"int", which computes the sum of the line prices of one order.
```

Nothing was written.

## Fix the NameError

Harness demo. No model. 0.2 s. `src/orders.py` had `subtotl` on the tax
line. A unique in-scope name is bound without calling weights. That is
not daily work.

```
$ python-vibe run "find the NameError and fix it"

bound unique NameError typo (subtotl → subtotal) in src/orders.py. Tests passed.
```

After:

```python
def total_with_tax(prices: list[int]) -> float:
    """Order total including tax."""
    subtotal = compute_total(prices)
    return subtotal + (subtotal * TAX_RATE)
```

A `.bak` of the file sits next to it.

## Add a function

Harness demo. No model. 0.2 s. A template wrote `total_lines` next to
`prices`. Daily add-a-function goes through the 8B and the suite.

```
$ python-vibe run "add a function total_lines and a test"

added def total_lines(prices) in src/orders.py. Tests passed.
```

What landed:

```python
def total_lines(prices: list[int]) -> int:
    return len(prices)
```

```python
def test_total_lines_returns_the_expected_result(self) -> None:
    prices = [10, 20]
    got = total_lines(prices)
    self.assertEqual(got, 2)
```

The suite stayed green. `ask` is the slow step because it is the one
that talks to weights. The two writes are harness demos, which is why
they look instant on [Start]({{ '/start/' | relative_url }}). Daily
`run` is write, then the suite, then one repair.

## Daily run

5 September 2026. Ollama `llama3.1:8b`. A fresh copy of
`eval/fixtures/daily_logic`: `compute_total` returned `0`, the test
wanted the sum. Not a unique typo.

```
$ python-vibe run "fix compute_total in src/app.py so it sums the rows"
ollama:llama3.1:8b  project /tmp/daily  mode small

--- step 1 ---
Action: patch
Path: src/app.py
Find: return 0
Replace: return sum(rows)

--- step 2 ---
Action: done
Summary: I fixed the compute_total function in src/app.py to return the
sum of the rows instead of always returning 0.
```

The harness ran the suite after the write. The suite was green, so the
next turn was `done`. That is the daily loop.
