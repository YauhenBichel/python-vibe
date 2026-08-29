# I measured a local coding loop for a week. The model was rarely the thing that fixed it.

*Draft for Medium. Kept out of `docs/` so the site does not publish a
second copy. Paste this file as one post. The numbers live on the
project site; this is the article.*

I wanted four jobs on a laptop: ask a question, write a test, fix a
one-line bug, add one small function. No account. Only the folder I
point at.

The public weight is a 0.5B adapter. Daily work is an 8B local model
plus a write jail. I published the four commands, typed them, and then
kept a table of every run that produced a number.

All of the scores below are from one machine, 29–30 August 2026. The
full table is on the site:
[Experiments](https://yauhenbichel.github.io/python-vibe/investigations/experiments/).

## The 0.5B is a style prior

Held-out vibe tasks (weekday name, count markdown files, a jsonl line,
a docstring): **0 / 4**. Parsed `Action:` that day: **0 / 2**. A
hundred-file stub walk returned no issues — that is not a review. The
QLoRA overfit after step 100; the public Hub file is that checkpoint.

I will not train more 0.5B steps and call that agency.

Site: [0.5B vibe review](https://yauhenbichel.github.io/python-vibe/research-vibe-review/).

## The four commands, as a person types them

Against a planted tree, `demo/orders`, the first evening:

| I typed | What I got |
| --- | --- |
| `ask "what does compute_total return?"` | `"int"` |
| `run "write tests for apply_discount"` | A second test below `if __name__`. It never ran |
| `run "find the NameError and fix it"` | Three files edited |
| `run "add a function total_lines and a test"` | Opened a file. Suite red. Then it asked |

That is **0 / 4** I would ship without reading the diff. Tighter wording
the same evening worked. The gap was the harness.

After the compiler jobs moved in front of the model: **4 / 4** on that
tree. Three of them finish with no model call. A leftover NameError
(`stauts` inside `def status`) asks what to return. It does not invent
`return "ok"`. If I answer `ok`, that literal is written and the model
still does not load.

Live first-Action parse the same night (`eval_everyday.py --live`,
`llama3.1:8b`): **8 / 15**. Offline fixtures were clean. That is above
the 50% floor and **not** everyday-ready. Everyday-ready still means
beating an untuned 8B on parse **and** a real ≥1 KB fix.

The fifteen parse cases changed verdict on ten of them across three
unchanged reruns. I will not treat one pass as a win. The rows that
hold still are the ones that never call the model.

Site: [First-run four jobs](https://yauhenbichel.github.io/python-vibe/investigations/first-run-four/)
· [Live scenarios](https://yauhenbichel.github.io/python-vibe/scenarios/).

## Same jobs, three local weights

`scripts/bench.py` only counts a case when the code runs and does the
job.

| Model | Write a test / add / fix | Platform paths |
| --- | --- | --- |
| `llama3.1:8b` | **9 / 9** | 1 / 4 |
| `qwen2.5-coder:7b` | 7 / 9 | **2 / 4** |
| 30B-class coder | not run (timeout) | **0 / 4**, every case timed out |

I did not switch the default. A 1B and a 1.5B already on disk do not
speak `Action:` at all.

The same eleven demo tasks against a hosted IDE agent, same wording,
same evening: the laptop column does not match. That gap is
intentional. No browser, no free shell, no any-language tree.

Site: [Which model](https://yauhenbichel.github.io/python-vibe/investigations/which-model/)
· [Same jobs](https://yauhenbichel.github.io/python-vibe/investigations/same-jobs/).

## Fine-tune later. Not on thirty rows.

A LoRA on 35 short pairs teaches tone. A LoRA on 30 Action traces
teaches the first line of the protocol. Neither teaches “patch the
leftover name, then write a test that calls it, then refuse `done`.”
That last sentence is a harness job.

I will not run `train.py --everyday` on those thirty rows. A later 7B
LoRA waits for about two thousand oracle-clean recorded turns, then
has to beat the untuned 8B or the adapter is deleted.

## A larger model is a URL, not a new product

A 30B timed out on this laptop. The generate call can move to a GPU
box. The jail stays here. `--engine openai` is that path. There is
**no live 14B/32B score yet**. When there is one, it has to beat the
laptop 8B on the same `demo/orders` checks.

Site: [Cloud weights](https://yauhenbichel.github.io/python-vibe/investigations/cloud-weights/).

## What I will say in public

python-vibe is a cheap loop for a small Python folder when I can name
the symbol, or when the job is one of the mechanical cases. It is not
a hosted IDE agent. It is not everyday-ready. The 0.5B adapter is not
a coding agent.

The table of every run:
[Experiments](https://yauhenbichel.github.io/python-vibe/investigations/experiments/).

Source: [github.com/YauhenBichel/python-vibe](https://github.com/YauhenBichel/python-vibe).
Weights: [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b).
