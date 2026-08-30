---
title: Experiments
description: Small open models for daily Python. What I typed, what the file looked like, and the score. One laptop, 29–30 August 2026.
permalink: /investigations/experiments/
date: 2026-08-29
type: article
---

# Experiments

I tried to use a small open LLM for daily Python: ask, write a test, fix
a bug, add one function. One laptop. 29–30 August 2026.

**Not everyday-ready.** Everyday-ready still means beating an untuned
`llama3.1:8b` on live parse **and** a real ≥1 KB fix.

<div class="stats">
  <div class="stat"><b>0 / 4</b><span>0.5B held-out vibe</span></div>
  <div class="stat"><b>0 / 4 → 4 / 4</b><span>Four Start commands</span></div>
  <div class="stat"><b>8 / 15</b><span>8B live first Action</span></div>
  <div class="stat"><b>6–9 / 9</b><span>8B when the code must run, six runs</span></div>
</div>

The four commands as typed:
[Scenarios]({{ '/scenarios/' | relative_url }}).
The machine, and every run behind these numbers:
[Bench record]({{ '/investigations/bench-record/' | relative_url }}).
Other notes:
[Research]({{ '/investigations/' | relative_url }}).
GitHub thread:
[discussion #128](https://github.com/YauhenBichel/python-vibe/discussions/128).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#the-05b-as-daily-work">The 0.5B as daily work</a></li>
  <li><a href="#four-jobs-as-typed">Four jobs, as typed</a></li>
  <li><a href="#which-small-open-model">Which small open model</a></li>
  <li><a href="#train-more-or-not">Train more, or not</a></li>
  <li><a href="#a-larger-open-model">A larger open model</a></li>
</ol>
</nav>

## The 0.5B as daily work

**Example.** Public adapter
[YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b)
on Qwen2.5-Coder-0.5B. Ask it for a weekday-name helper, a markdown
file counter, a jsonl line, a docstring. Ask it to emit `Action:`.

**Result**

| What I asked | What I got |
| --- | --- |
| Held-out vibe (weekday, count-md, jsonl, docstring) | **0 / 4** |
| Parsed `Action:` that day | **0 / 2** |
| Walk a hundred stub files | A hundred “no issues”. Not a review |
| 400-step QLoRA | Overfit after step 100. Hub file is that checkpoint |

The 0.5B is a style prior. It is not daily work. I am not training more
0.5B steps.

Write-up: [0.5B vibe review]({{ '/research-vibe-review/' | relative_url }})
· [Everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}).

## Four jobs, as typed

**Example.** Planted tree `demo/orders`. Two NameErrors sit in the code:

```python
# src/orders.py
subtotal = compute_total(prices)
return subtotl + (subtotl * TAX_RATE)

# src/orders_controller.py
class OrdersController:
    def status(self) -> str:
        return stauts
```

**Result, first typing (evening)**

| I typed | What I got |
| --- | --- |
| `ask "what does compute_total return?"` | `"int"` |
| `run "write tests for apply_discount"` | A second test below `if __name__`. It never ran |
| `run "find the NameError and fix it"` | Three files edited |
| `run "add a function total_lines and a test"` | Opened a file. Suite red. Then it asked |

**0 / 4** I would ship without reading the diff.

**Result, after the harness did the compiler jobs first**

| I typed | What I got | Check |
| --- | --- | --- |
| same `ask` | A sentence that quotes `int` and says it sums line prices | nothing written |
| same write-tests | `already has a test`. No model | suite green |
| same NameError | `subtotl` → `subtotal` in `orders.py`. No model | `total_with_tax([10])` is `12.0` |
| same add | `def total_lines(prices)` and an AAA test. No model | `total_lines([10, 20]) == 2` |
| `run "find the NameError in src/orders_controller.py"` | Asks. Does not write `return status`. Answer `ok` → `return "ok"`. No model | `status` as an answer is refused |

Four of those five finish with **no model**. That is why they are the
same every time. Live first-Action parse the same night
(`eval_everyday.py --live`, `llama3.1:8b`): **8 / 15**. Offline fixtures
were clean. Those fifteen cases changed verdict on ten of them across
three unchanged reruns. A single parse pass is not a score.

Write-up: [First-run four]({{ '/investigations/first-run-four/' | relative_url }})
· [Scenarios]({{ '/scenarios/' | relative_url }}).

## Which small open model

**Example.** `scripts/bench.py`. A case counts only if the function
runs and does the job — not if a file appeared.

**Result**

| Model | Write a test / add / fix | Platform paths |
| --- | --- | --- |
| `llama3.1:8b` | **6–9 / 9** (six runs) | 1 / 4 |
| `qwen2.5-coder:7b` | 7 / 9 (one run) | **2 / 4** |
| 30B-class coder | timed out | **0 / 4** |
| 1B and 1.5B on disk | no `Action:` (prose or `# patch`) | — |

I did not switch the default. The 7B coder trades two of the daily jobs
for one extra platform task.

### One run is not a score

The nine cases above were run six times against unchanged code:

    9/9   6/9   8/9   7/9   8/9   7/9

Five of the nine pass every time — `clamp`, `double`, `cover-discount`,
`cover-shout`, `fix-nameerror` — and three of those five finish without
calling the model at all. The other four come and go. Over the whole
fifteen-case bench, ten of fifteen changed verdict between identical
runs, and the totals ranged from 7 to 12.

So the single figures on this page are worth reading as a rough size,
not a rank. The comparison between models rests on one run each, which
is enough to see that the 30B never finished and not enough to separate
`8b` from `coder:7b`. Anything smaller than about a four-case gap is
inside the noise.

Same eleven demo tasks against a hosted IDE agent, same wording: the
laptop column does not match. No browser, no free shell, no any-language
tree.

Write-up: [Which model]({{ '/investigations/which-model/' | relative_url }})
· [Same jobs]({{ '/investigations/same-jobs/' | relative_url }}).

## Train more, or not

**Example.** 35 short train pairs. 30 handwritten Action traces.
`train.py --everyday` is a 7B-class LoRA config. It has not been run.

**Result**

| Idea | What it would teach | Do it? |
| --- | --- | --- |
| More 0.5B steps | Tone. Already overfit | No |
| 8B LoRA on 30 traces | The first `Action:` line | No |
| 7B LoRA after ~2k oracle-clean `--record` turns | The protocol *and* a finish, if it beats the 8B | Later |

“Patch the leftover name, write a test that calls it, refuse `done`”
is a harness job. That is what moved the four Start commands from
0 / 4 to 4 / 4.

Write-up: [Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}).

## A larger open model

**Example.** The 30B already timed out on this laptop. `--engine openai`
sends only the generate call to a GPU. The write limit stays here.

**Result**

| Run | Score |
| --- | --- |
| 30B on this laptop | Timeout. 0 / 4 platform cases |
| 14B / 32B on a GPU | **No live number yet.** Must beat the laptop 8B on the same four jobs |

Write-up: [Cloud weights]({{ '/investigations/cloud-weights/' | relative_url }}).
