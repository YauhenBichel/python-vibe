---
title: Experiments
description: Small open models for daily Python. What I typed, what the file looked like, and the score. One laptop, 29–30 August and 5 September 2026.
permalink: /investigations/experiments/
date: 2026-09-05
type: article
---

# Experiments

I tried to use a small open LLM for daily Python: ask, write a test, fix
a bug, add one function. One laptop. 29–30 August and 5 September 2026.

**Not everyday-ready.** Everyday-ready still means beating an untuned
`llama3.1:8b` on live parse **and** a real ≥1 KB fix.

<div class="stats">
  <div class="stat"><b>12 / 18</b><span>0.5B four drafts + later loop</span></div>
  <div class="stat"><b>0 / 54</b><span>greedy 0.5B LoRA</span></div>
  <div class="stat"><b>8 / 15</b><span>8B live first Action</span></div>
  <div class="stat"><b>8 / 9</b><span>8B daily jobs, 5 Sep 2026</span></div>
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
  <li><a href="#exact-stdout-on-the-05b">Exact stdout on the 0.5B</a></li>
  <li><a href="#sample-four-drafts-then-greedy">Sample four drafts, then greedy</a></li>
  <li><a href="#8b-daily-jobs">8B daily jobs</a></li>
  <li><a href="#8b-greenfield-cli">8B greenfield CLI</a></li>
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

## Exact stdout on the 0.5B

**Example.** Eighteen held-out scripts. None of the 45 train prompts.
Extract the Python block, run it, demand an exact line. Repeat each
task three times. Then send the traceback back once.

**Result, 5 September 2026**, Ollama `qwen2.5-coder:0.5b`:

| Variant | Passed |
| --- | --- |
| base | **7 / 54** |
| one traceback repair | **12 / 54** |

24 of 54 base runs crashed (often `sys` used, never imported). 23 printed
the right number with extra words (`Clamped value: 10`). Eleven of
eighteen tasks never passed. LoRA was not measured (`mlx-lm` missing).
Unit tests for the checkers passed.

Write-up: [0.5B exact-stdout eval]({{ '/investigations/held-out-exec-eval/' | relative_url }}).
Cite: [Cite]({{ '/cite/' | relative_url }}).

## Sample four drafts, then greedy

**Example.** Same 18 scripts on MLX Qwen2.5-Coder-0.5B-Instruct-4bit.
First, up to four independent drafts at temperature 0.7. Then one
greedy draft, three repeats, with and without the step-100 LoRA.

**Result, 5 September 2026**

| Variant | Four drafts / 18 | Greedy unique / 18 | Greedy runs / 54 |
| --- | --- | --- | --- |
| base | **6** | **2** | 6 |
| one traceback repair | **9** | **3** | 9 |
| LoRA | **2** | **0** | 0 |
| LoRA + repair | **6** | **0** | 0 |

Sampling found a different set, not a superset. Only one of the +3
from 6 to 9 is a traceback fix; the rest is a new draw. Greedy LoRA
printed style notes, not scripts. A later loop (prepend `datetime`,
say when stdout is wrong, one 8B hint) scored **12 / 18**. Zero of
those twelve were a hint-repair. Stop spending hours on this board.

Write-up: [0.5B sample-and-run]({{ '/investigations/sample-and-run/' | relative_url }}).

## 8B daily jobs

**Example.** 5 September 2026. Ollama `llama3.1:8b`. Three jobs that
are not planted NameErrors, each three times, after the harness started
running the suite following a write.

| Job | What I asked | Passed |
| --- | --- | --- |
| Write tests | `write tests for apply_discount in src/app.py` | **3 / 3** (harness wrote the AAA test) |
| Add a function | `add a function clamp(value, lo, hi) … and a unit test` | **3 / 3** (8B) |
| Logic bug | `fix compute_total in src/app.py so it sums the rows` | **2 / 3** (one hit the step budget) |

**8 / 9.** The miss was a logic-bug run that spent twelve steps without
a green suite. Replay one of the wins:
[Live demo]({{ '/live/' | relative_url }}) (daily recording).

Everyday-ready is still the older bar: beat a clean 8B on parse **and**
a real ≥1 KB fix. This table is the daily loop on small fixtures, not
that bar.

## 8B greenfield CLI

**Example.** 5 September 2026. Ollama `llama3.1:8b`. Empty folder.
Typed: `design and develop a small cli app for reviewing github PRs`.

Before the app checklist the 8B treated it as a ship job:

| Check | Result |
| --- | --- |
| First Action | `locate` `open-pr` |
| Files written | none |
| Suite | never ran |
| Stop | `ask` |

After scaffold + checklist (init, urllib and an env token, list, show,
mocked tests), three repeats at the default twenty steps. Comment,
pagination, and `Path.home()` config are overflow — a later typed
`run`, not `--steps`.

| Repeat | First Action | Files | Checklist | Suite | Stop |
| --- | --- | --- | --- | --- | --- |
| 1 | `patch` weekday test | `pkg/pr_review.py` (list + show via `get_prs`), tests | `mocked_tests` (wanted `list_pulls`) | never ran | steps |
| 2 | `write-script`, then `edit` `pkg/pr_review.py` | `list_pulls` + `show_pull` + mock test | list / show ready | red (`GITHUB_TOKEN`, then `os`) | steps |
| 3 | `edit` tests first | stub `pkg/pr_review.py` (37 B) | http, list, show, tests missing | — | steps |

**1 / 3** list/show checklist. **0 / 3** suite green. **0 / 3** `done`.

Then three repeats at twelve steps, same budget as the daily jobs,
after the harness started scaffolding `pkg/` and refusing locate /
ask:

| Repeat | list + show + mocks | Stopped | What it wrote |
| --- | --- | --- | --- |
| 1 | yes | steps | `pkg/pr_review.py`, `pkg.py`, tests |
| 2 | yes | steps | `pkg/pr_review.py`, tests |
| 3 | no (`show`, `mocked_tests`) | steps | `pkg/pr_review.py`, `pkg/pull_viewer.py` |

**2 / 3.** The miss spent the budget on a second module.

Later the same day, after #206 (refuse locate until list and show
exist), twelve steps again:

| Repeat | list + show + mocks | Stopped | What it wrote |
| --- | --- | --- | --- |
| 1 | yes | steps | `pkg/pr_review.py`, tests |
| 2 | yes | steps | `pkg/pr_review.py`, tests |
| 3 | yes | steps | `pkg/pr_review.py`, tests |

**3 / 3** on the checklist. **0 / 3** said `done`. Every run hit the
step cap with the files already on disk. Replay:
`python scripts/measure/eval_cli_app.py` (twelve steps; pass
`--steps 20` for the first cell).

Finish was the gap: the files were on disk and the model kept
writing. Once list and show exist, the harness now writes the mocked
`urlopen` test (token via `patch.dict`) and runs the suite — the same
idea as the add-feature cover test. Overflow (comment / pagination /
config) is a later typed `run`, not more `--steps`.

Same prompt, twelve steps, after that mock-test write (#214). 5
September 2026. Ollama `llama3.1:8b`.

| Repeat | Checklist | Suite | Stopped | Wrote |
| --- | --- | --- | --- | --- |
| 1 | no (`mocked_tests`) | red | steps | `pkg/pr_review.py` × 4 |
| 2 | no (`show`, `mocked_tests`) | red | steps | `pkg/pr_review.py` |
| 3 | yes | green | `done` | `pkg/pr_review.py`, tests |

**1 / 3** checklist. **1 / 3** suite green. **1 / 3** `done`. Two of
three stayed red after one repair, so I stopped adding product copy.

Same prompt, twelve steps, after the mock test bound the list/GET
name the 8B wrote (#220). Same evening. Ollama `llama3.1:8b`.

| Repeat | Checklist | Suite | Stopped | Wrote |
| --- | --- | --- | --- | --- |
| 1 | yes | green | `done` | `pkg/pr_review.py` × 2, tests |
| 2 | yes | green | `done` | `pkg/pr_review.py`, tests |
| 3 | yes | green | `done` | `pkg/pr_review.py` × 4, tests |

**3 / 3** checklist. **3 / 3** suite green. **3 / 3** `done`. Replay:
`PYTHONPATH=src python scripts/measure/eval_cli_app.py`.

Later the same day, overflow from a runnable list+show tree. Typed:
`add the comment subcommand and a mocked test`. After #216.

| Check | Result |
| --- | --- |
| First try | `grep` `comment` (add-feature hint). 20 steps. No comment |
| Timed cell (12 steps × 3) | **0 / 3** closed the comment gap. Every repeat hit the cap |
| After hint tighten | first Action `edit`; `def comment_on` on disk; `done` refused because nothing called it |

`def comment` now counts. Overflow `done` is allowed once that piece
exists — argparse wiring is not demanded by the unused-function guard.
Pagination and config stay later runs, not `--steps`. Replay:
`python scripts/measure/eval_cli_overflow.py`.

```bash
python-vibe run "add the comment subcommand and a mocked test"
```

Everyday-ready is still the older bar.

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

**Example.** `scripts/measure/bench.py`. A case counts only if the function
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


## On a real repository

**Example.** Everything above uses `demo/orders`, a fixture with two
planted bugs. This is the same tool pointed at a working repository of
4,580 first-party files that nobody wrote for this benchmark. Nothing
was written inside it: reads ran against it directly, writes against a
fresh copy of one module.

**Result**

| Job | Score |
| --- | --- |
| `brief`, `layout`, `ask --scope` | Correct. 6–7 s each |
| Import cycles reported by `layout` | 4 reported, **0 real** — then 4 reported, 4 real after the fix |
| Write a test, add a function | **1 / 12** verified, four tasks, three runs each |
| Undefined-name guard across 3,658 files | 3% flagged, **every one correct code** — now 0 |

Reading a real repository works. Writing to one does not, and the same
tasks pass on the fixture, which is worth knowing about the fixture.

Detail: [Bench record]({{ '/investigations/bench-record/' | relative_url }}).

## When a run says done and means nothing

The worst outcome is not a failure. It is a run that finishes, reports
success, and leaves the file exactly as it was — because the only way to
find that out is to go and look.

Counting why each run stopped, across 45 benchmark runs, put a number on
it: two of the nine failures reported `done`.

**Result**

| One task, ten runs each side | Reported success having changed nothing |
| --- | --- |
| Before | **5 of 10** |
| After two fixes | **0 of 10** |

Neither fix was a missing guard. One guard existed and its escape hatch
was a sentence the refusal itself handed the model, which the model
handed back. The other cause was not in the model at all: the harness
took a word out of the task, found it as a substring in a test file, and
finished. The word is in 17 of this project's test files and called in 5.

Write-up: [When a run says done and means nothing]({{ '/investigations/false-finish/' | relative_url }}).

## Asking a bigger model, rarely

If the harness could put a question to a larger model the user has
registered, when should it? The call is easy; knowing when to make it is
not.

**Result**

| Why a run stopped, 45 runs | Share | Was it really stuck? |
| --- | --- | --- |
| Asked a question | 7% | **3 of 3** |
| Ran out of steps | 18% | 4 of 8 |
| Said done, was wrong | 4% | no stop reason catches it |

A run that stops to ask has earned it: asking is capped at two, and
refused outright once files have changed. Running out of steps means
much less. Seven of the nine failures were platform and operations work,
the tier that moved 37% to 70% on harness fixes alone — gaps in the
tool, which sending them away would hide.

Write-up: [Asking a bigger model, rarely]({{ '/investigations/asking-a-bigger-model/' | relative_url }}).

## A chain of easy tasks

If the model is not very good, is it better to give it several small
instructions than one composite one?

**Result**

| Same work, same fixture, 8 runs each | Worked | Average |
| --- | --- | --- |
| One instruction | **5 of 8** | 20s |
| Split in two, sent blind | 4 of 8 | 46s |
| Split, each step checked and retried | 4 of 8 | 42s |

Splitting bought nothing and cost twice the clock. A run is already up
to twenty turns, each a single action, so splitting from outside adds a
second copy of the decomposition rather than more of it — and each run
builds its own memory, so every step started from nothing.

Write-up: [Small steps, measured]({{ '/investigations/small-steps/' | relative_url }}).

## What the harness cannot fix

Most gaps here close when the harness stops guessing and starts
checking. Four did not, and they are more informative than the ones that
did.

**Result**

| Measurement | Outcome |
| --- | --- |
| Refusing a bot's major version bump | **0 of 5** — five merged safely, nothing caught. Since fixed: **2 of 6 now allowed**, the rest name the workflow nobody ran |
| Telling the model what the project already has | Pointer correct, **ignored 3 of 3** |
| Platform work on stock `llama3.1:8b` | **6 of 8** over two passes, no new weights |
| This project's own fine-tune | **0 of 4** held-out, worse than its base model |
| Training data collected in a week of real work | **0 rows** — recording was behind a flag |
| Centring a long file's excerpt on the task's subject | Defect real and fixed; **0 of 5 either side** |
| Showing the model how long its functions are | Rule existed as a merge gate only; **21 of 30 either side** |

Five of the six are cases where the harness knew something and it made
no difference. The one that worked, worked by running something: a
dependency's major bump was cleared by installing the version and
calling every function the project uses against it.

What closes a gap is an oracle. What does not is telling the model more.

Write-up: [What the harness cannot fix]({{ '/investigations/limits/' | relative_url }}).

## A larger open model

**Example.** The 30B already timed out on this laptop. `--engine openai`
sends only the generate call to a GPU. The write limit stays here.

**Result**

| Run | Score |
| --- | --- |
| 30B on this laptop | Timeout. 0 / 4 platform cases |
| **14B on this laptop** | **Could not be measured.** 9 GB of weights on 18 GB put the machine into 12–13 GB of swap; no run finished |
| 14B / 32B on a GPU | **No live number yet.** Must beat the laptop 8B on the same four jobs |

The 14B result is about the machine, not the model. Weights are only
part of the budget: the key-value cache grows with context and the
operating system wants its share, so the practical ceiling here is about
11–12 GB, not 18. If you are choosing hardware, reckon on roughly twice
the size of the model you mean to run.

Write-up: [Cloud weights]({{ '/investigations/cloud-weights/' | relative_url }})
· [Bench record]({{ '/investigations/bench-record/' | relative_url }}).
