# Four jobs on a laptop (and what the harness had to do)

*Draft for Medium. Kept out of `docs/` so the site does not publish a
second copy of an article meant to be posted elsewhere.*

I wanted a cheap everyday loop for small Python: ask a question, write a
test, fix a one-line bug, add one small function. On my machine. Only
the folder I point at.

The public 0.5B adapter is a style prior. It misses tool lines. Daily
work is an 8B local model plus a write jail. I published the four
commands on the Start page and then typed them against a tiny planted
project, `demo/orders`.

This is what happened. The numbers are from one laptop, 29 August 2026.

## The first evening, as written on Start

| I typed | What I got |
| --- | --- |
| `python-vibe ask "what does compute_total return?"` | `"int"` |
| `python-vibe run "write tests for apply_discount"` | A second test pasted *below* `if __name__`. The suite still ran the original two. The new one never ran. |
| `python-vibe run "find the NameError and fix it"` | Three files edited. The unique typo was fixed. Extra mess stayed. |
| `python-vibe run "add a function total_lines and a test"` | A function that opened a file. The suite went red. Then it asked what I had meant. |

That is 0/4 I would ship without reading the diff.

Tighter wording the same evening worked: name the file, name the
argument list. So the gap was the harness, not “need a bigger model.”

## What we changed (no new weights)

The harness now does the compiler jobs *before* the model speaks.

- A thin `"int"` is sent back until the answer quotes the type **and**
  says what the function computes.
- If a test already names the function, the run ends. It does not append
  a dead copy.
- A unique NameError typo (`subtotl` next to `subtotal =`) is bound
  across the tree when I do not name a file.
- `add a function total_lines` next to neighbors that take `prices`
  becomes `return len(prices)`. `open(` on that job is refused.
- `stauts` inside `def status` has no unique bind. Binding to the method
  name still raises. The run **asks** what it should return. It does not
  guess `return "ok"`, and it does not spend twenty patches. If I answer
  `ok`, that literal is written and the model still does not load —
  unless I asked read-only, in which case it tells me what it would
  have written.

Re-measured the same night: all four Start commands finished correctly.
The controller NameError stopped on a question. `return stauts` was
unchanged.

## Does it make sense every day?

For a **small Python folder**, when I can name the symbol or the job is
one of those mechanical cases: **yes**.

Write tests: **yes**, for one named function or class. Not for “cover
this package.”

Find bugs and smells: **yes**, for a unique typo and a named rename.
**No** for a logic bug that still parses, a whole-repo walk, or a typo
with no unique nearby name.

It does not replace a hosted IDE agent. No browser, no free shell, no
any-language tree. That gap is intentional.

## The score I will not inflate

`eval_everyday.py --live` on `llama3.1:8b` that night: **8 / 15** first
Actions parsed as the fixture wanted. Offline fixtures were clean. I
still will not call the project everyday-ready until live parse **and**
a real ≥1 KB fix beat an untuned 8B on this machine.

I will not train more 0.5B steps. I will not train an 8B LoRA on thirty
rows and call that agency.

## Links

Site: [yauhenbichel.github.io/python-vibe](https://yauhenbichel.github.io/python-vibe/)

The measured first-run write-up:
[First-run four jobs]({{ '/investigations/first-run-four/' | relative_url }}).

The command-by-command table, including misses:
[Live scenarios]({{ '/scenarios/' | relative_url }}).

Source: [github.com/YauhenBichel/python-vibe](https://github.com/YauhenBichel/python-vibe).
