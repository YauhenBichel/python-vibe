---
title: Fine-tune or harness
description: When a small coding model needs new weights, and when the loop should stay deterministic. Measured on this laptop plus two 2026 papers.
permalink: /investigations/fine-tune-or-harness/
date: 2026-08-29
type: article
---

# Fine-tune or harness

**Question.** python-vibe’s everyday brain is an untuned 8B. The published
adapter is a 0.5B style prior. Should we fine-tune again to make the loop
behave like a bigger coding agent?

**Answer.** Not yet. Fine-tune **after** the harness already refuses a lie,
and only on traces recorded **inside this harness**. Thirty seed rows and
another 0.5B run will not buy agency. That is what this laptop measured,
and it is what the 2026 small-model agent papers say when they separate
the harness effect from the weight effect.

Related: [small models, classic development]({{ '/investigations/small-llm-harness/' | relative_url }})
· [what to improve]({{ '/investigations/what-to-improve/' | relative_url }})
· [hub models]({{ '/investigations/hub-models/' | relative_url }})
· [everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#what-is-on-disk">What is on disk</a></li>
  <li><a href="#what-this-laptop-already-measured">What this laptop already measured</a></li>
  <li><a href="#what-the-papers-measure">What the papers measure</a></li>
  <li><a href="#map-their-grid-onto-this-repo">Map their grid onto this repo</a></li>
  <li><a href="#decision">Decision</a></li>
  <li><a href="#how-to-fine-tune-later-without-wasting-a-week">How to fine-tune later without wasting a week</a></li>
  <li><a href="#save-money-next-steps">Save money: next steps</a></li>
</ol>
</nav>

## What is on disk

| Artifact | Rows / steps | Role |
| --- | --- | --- |
| `data/python-vibe/train.jsonl` | 35 chat pairs | 0.5B QLoRA style prior |
| `data/python-vibe/valid.jsonl` + `test.jsonl` | 5 + 5 | Same style, held-out wording |
| Hub `YauhenBichel/python-vibe-0.5b` | step 100 of 400 | Public download. Val ~0.91 then overfit |
| `data/agent-loop/train.jsonl` | 30 Action traces | Seed for a 7B-class LoRA |
| `configs/python-vibe-8b.yaml` | 200 iters, not run | `train.py --everyday`. No adapters on disk |
| `eval/action_prompts.jsonl` | 12 prompts | Live parse. Not training data |

A LoRA on 35 short pairs teaches **tone**. A LoRA on 30 Action traces
teaches **the first line of the protocol**. Neither teaches “patch the
leftover name, then write a test that calls it, then refuse `done`.”
That last sentence is a harness job.

## What this laptop already measured

29 Aug 2026, one machine, Ollama `llama3.1:8b` unless noted.

| Measurement | Result | What a new LoRA would change |
| --- | --- | --- |
| 0.5B held-out vibe (weekday, count-md, jsonl, docstring) | 0 / 4 | Already tried. Base 0.5B failed the same class |
| 0.5B parsed `Action:` that day | 0 / 2 | Misses the protocol. More 0.5B steps overfit |
| 8B first Action on three scoped tasks | 3 / 3 | Start is often right without a LoRA |
| 8B live Action parse | 2 / 3 early; 7 / 10 later the same day | The prompt and the file opened first, not the weights |
| `scripts/demo.py` on `demo/orders` | Agent said done; independent check 1 / 4 file jobs | **Finish is a lie.** Oracles, not SFT |
| 7B-class everyday LoRA | Config only | Nothing to compare until traces exist |
| 30B coder on disk | Timeout at 180s | Bigger local weight is not the everyday path |

The failure that looks like “the model is too small” is usually “the
loop accepted `done`.” Live 8B left `subtotl` in `src/orders.py` after a
green suite that never called `total_with_tax`. It wrote `def test_`
into the implementation file. It renamed `calc` and left a `NameError`.
Those are compiler-shaped bugs. They are now refuses
(`refuse_undefined_draft`, `refuse_test_in_impl`, `refuse_done_oracle`).
A fine-tune that still emits `Action: done` after those mistakes would
lose to the current harness.

## What the papers measure

Two 2026 results separate **harness** from **fine-tune**. They are not
this repo. They are the comparison.

**Specialized small-model subagents** (Ranjan, 2026-06-11,
[slm-agents white paper](https://github.com/IshaanAyaan/slm-agents/blob/main/slm_harness/paper/white_paper.md)).
A 2×3 grid: {large, small, small fine-tuned} × {generic harness, custom
harness}. File-navigation on held-out real repos. No paid API.

| Cell | What they saw |
| --- | --- |
| Large + generic (C1) | 72B succeeds 95.5% |
| Small + generic (C2) | Naive 3B swap: 48.0% success, **worse cost-per-success** than 72B |
| Small + custom harness (C3) | Harness alone can **underperform** the naive small model |
| Small fine-tuned + generic (C4) | Fine-tune alone can **hurt**. 1.5B scored **1.0%** |
| Small fine-tuned + custom (C5) | 3B succeeds 94.5% (indistinguishable from 72B), **84.8%** lower cost-per-success |

Only the **pair** wins. The 1.5B fine-tune scored **1.0% in the generic
harness and 93.5% in the co-designed one**. A custom harness around a
model that cannot follow it, or a LoRA that speaks `Action:` with no
write limit, both lose. The 8B everyday brain is already capable enough that
harness adaptation (oracles, pinned `Path:`) is the Better-Harnesses
regime — not the 1.5B “C3 underperforms C2” regime.

**Better harnesses, smaller models** (arXiv:2607.08938). Seven routine
agent tasks, three SLM families. An adapted harness (instructions,
tools, anti-loop checks) improved **16 of 21** task–model pairs. Seven
pairs closed the SLM–frontier gap. Best reported recovery: **89.7%** of
frontier performance at **4%** of the cost. Adaptation worked when the
workflow repeated and the base model was already capable enough.

**SWE-smith / SWE-agent training.** They fine-tune on **resolved**
expert trajectories generated **inside the same scaffold** they evaluate.
They do not train on thirty handwritten “Action: grep” lines and call
the model a software engineer.

None of those papers argue for another 0.5B QLoRA on 35 stdlib pairs.

## Map their grid onto this repo

| Their cell | python-vibe today | What “win” looks like |
| --- | --- | --- |
| C1 large + generic | A hosted IDE agent | Out of scope. Different product |
| C2 small + generic | 0.5B or 8B with no write limit | Already measured: 0.5B 0/4 vibe; 8B says done with `subtotl` |
| C3 small + custom harness | **Everyday path now.** 8B is capable enough; oracles close finish | Finish the known demo fails without a new weight |
| C4 small fine-tuned + generic | `train.py --everyday` on 30 rows, then drop the write limit | Do not do this |
| C5 small fine-tuned + custom | 7B/8B LoRA on ~2k **verifier-clean** `--record` turns | Later. Same Action schema the harness already parses |

C3 is the work that moved this week: opening the right file before the
model's first turn, pinning the `Path:` inside a skill, refusing a test
that does not set up its inputs, checking for names that are used but
never defined, and refusing paths that only work on one platform.
C5 is a real later lever — **only** after C3 stops accepting a green
suite that never called the bug.

The Ranjan C4 cell is the warning for `python-vibe-8b.yaml`: a LoRA that
speaks `Action:` in a plain chat window, with no file opened for it and
no checks around it,
can be worse than the untuned 8B you already run.

## Decision

| Proposal | Do it? | Why |
| --- | --- | --- |
| More 0.5B train steps | No | Overfit after step 100. Held-out vibe 0/4 |
| Train `python-vibe-8b` on the 30 seed rows | No | Memorizes the protocol line. Does not finish a change |
| Raise `--steps` instead of oracles | No | Burns tokens. Live add-feature already hit the budget |
| Add bash / browser as 8B tools | No | The write limit is the product. Papers that use bash use a container and a frontier model |
| Keep refusing `done` until the compiler is quiet | Yes | Matches C3. Matches the demo misses |
| `--record` only turns the oracles already accept | Yes | Future C5 data. Gitignored `data/agent-loop/extra.jsonl` |
| 7B-class LoRA after ~2k clean traces | Later | C5. Distill from a hosted agent **or** from a passing 8B loop in *this* schema |

Fine-tuning is required **once** the harness is the bottleneck — when
the first Action is wrong on a task where the harness had already opened
the right file, after
the oracles are quiet, at a rate an 8B cannot close. That is not where
this laptop is. The bottleneck is still **finish**.

## How to fine-tune later without wasting a week

1. Keep the Action schema stable. A LoRA trained on today’s `Action:
   patch` / `Find:` / `Append:` is worthless if next month the protocol
   becomes JSON tool calls.
2. Record only turns that passed the oracles: `ast.parse`, no new
   undefined names, tests not in the impl file, unittest that calls the
   change, design scan clean when the task asked for structure.
3. Redact hostnames and home paths. Do not commit `extra.jsonl`.
4. Distill from a larger model **in this harness** (same opening step, same
   refuses), not from a generic chat transcript. A 14B–70B that timed out
   on the laptop is reached with `--engine openai` or `OLLAMA_HOST`; the
   write limit does not move. See [cloud weights]({{ '/investigations/cloud-weights/' | relative_url }}).
5. Evaluate with `scripts/eval_everyday.py --live` and
   `scripts/demo.py`. Everyday-ready still means: beat the untuned 8B
   on parse **and** pass the independent file checks, including the
   planted NameError that the existing suite misses.
6. If a 7B LoRA loses to untuned 8B + current harness on those checks,
   delete the adapter. The papers already showed C4 can score 1%.

That is the investigation: **behavior improvement is still harness
work.** Fine-tuning is the second half of a co-designed pair, not a
shortcut around classic development.

## Save money: next steps

The cheap path is local 8B and this write limit. A hosted IDE agent costs a usage
pool. You only save that money when python-vibe **finishes** the job so
you do not reopen the paid tool to clean up.

Use python-vibe when the tree is small and the job is one of: a typed
question, add a function and a test, fix a NameError, rename, a pathlib /
venv helper, a script, an HTTP client, a tally, an algorithm. Those are
free once they finish.

Keep the paid tool for a large tree, extra servers, a browser, another
language, or a hundred-file review. Those are not this product.

Order of work, cheapest first:

1. **This week.** A unique NameError typo and a typed rename are
   mechanical. The harness writes them, runs the suite, and ends
   without a model when tests are already green. Live-retest
   `write-tests` (still a model job) and any task that is *not* a
   unique typo. A passing suite that never called the change is still
   not a finish.
2. **This month.** Use it on your own small Python trees. `--record` only
   turns the oracles already accept. Each finished job is money you did
   not spend.
3. **Not this month.** Do not train more 0.5B. Do not train
   `python-vibe-8b` on 30 rows. A bad LoRA is a week of electricity that
   still sends you back to the paid tool.
4. **Later.** If the first Action is still wrong after the oracles are
   quiet, then a 7B LoRA on ~2k clean traces (C5). That is how the papers
   got 72B-class success at a fraction of the cost — not by skipping the
   write limit.
