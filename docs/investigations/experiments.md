---
title: Experiments
description: Laptop measurements of a local Python helper. Abstract, methods, results, and related work. One machine, 29 August–5 September 2026.
permalink: /investigations/experiments/
date: 2026-09-06
type: article
---

# Experiments

Yauhen Bichel  
6 September 2026

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#abstract">Abstract</a></li>
  <li><a href="#introduction">Introduction</a></li>
  <li><a href="#related-work">Related work</a></li>
  <li><a href="#methods">Methods</a></li>
  <li><a href="#results">Results</a></li>
  <li><a href="#discussion">Discussion</a></li>
  <li><a href="#limitations">Limitations</a></li>
  <li><a href="#conclusion">Conclusion</a></li>
  <li><a href="#references">References</a></li>
</ol>
</nav>

## Abstract

A local helper plus a small open model was asked to do four daily
Python jobs on one laptop: answer a question, write a test, fix a
bug, add one function. Dates: 29–30 August and 5 September 2026.

**0.5B** here means a model with about **500 million weights** —
Qwen2.5-Coder-0.5B, plus an optional public LoRA on top. It is the
tiny Hub demo, not daily work. **8B** means about **8 billion
weights** — Ollama `llama3.1:8b`, the default. **7B** is the
on-disk coder comparison (`qwen2.5-coder:7b`).

The 0.5B adapter is a style prior, not an agent (held-out vibe
**0 / 4**; greedy LoRA **0 / 54**). One traceback repair lifts
exact-stdout from **7 / 54** to **12 / 54**. Daily jobs on the 8B
reached **9 / 9** the same evening the 7B coder scored **7 / 9**.
The helper moved the four Start commands from **0 / 4** to
**4 / 4** by doing compiler jobs itself. The everyday-ready bar —
beat a plain 8B at the next step **and** at a real bug the helper
cannot write — is not met. This project does not report a
SWE-bench score.

<div class="stats">
  <div class="stat"><b>12 / 18</b><span>tiny 0.5B (500M weights), four drafts then a later loop</span></div>
  <div class="stat"><b>0 / 54</b><span>same 0.5B + LoRA, one greedy try each</span></div>
  <div class="stat"><b>8 / 15</b><span>daily 8B (8 billion weights) picked the right first step</span></div>
  <div class="stat"><b>9 / 9</b><span>daily 8B jobs, evening of 5 Sep</span></div>
</div>

## Introduction

The question is whether a laptop helper and a small open model can
do everyday Python without a hosted agent. Two sizes are easy to
mix up: the **public 0.5B** (500 million weights, a style prior)
and the **daily 8B** (8 billion weights, what `ask` / `run` call).
“Everyday-ready” here means: beat a plain 8B at reading the next
step, **and** at fixing a real bug the helper cannot do itself.
The first “real bug” cell was a whole-line `return 0.0` on a named
sum — the helper can write that, so it is no longer a model job.

Each table below is one question, what I typed, and what happened.
The map of every note is [Results]({{ '/investigations/' | relative_url }}).
How to cite a score: [Cite]({{ '/cite/' | relative_url }}).

[What you type]({{ '/scenarios/' | relative_url }}) ·
[The machine]({{ '/investigations/bench-record/' | relative_url }}) ·
[discussion #128](https://github.com/YauhenBichel/python-vibe/discussions/128).

## Related work

The loop is one `Action:` block, then tools — a tight read-act
loop, not a free shell (Yao et al., 2023). SWE-agent showed that
the interface around the same model moves the score (Yang et al.,
2024): previous best retrieval-only 3.8%, agent 12.5%, same model
1.3% → 12.5%. python-vibe’s first-run four jobs were **0 / 4**
then **4 / 4** after the helper. Same shape, smaller tree.

A green suite that never called the bug is not done (Liu et al.,
2023). `run` may send **one** traceback back (Shinn et al., 2023;
McAndrews, 2026). Small models can be workers at 7–8B; that is not
a claim that a 0.5B style adapter is an agent (Belcak et al.,
2025). SWE-bench is the field’s ruler (Jimenez et al., 2024). It
is the wrong ruler for a one-folder laptop helper. This project
does **not** report a SWE-bench score.

Full citations: [References]({{ '/references/' | relative_url }}).

## Methods

**Machine.** One Apple M3 Pro laptop, 18 GB unified memory. Ollama
and, for the 0.5B sample-and-run cell, MLX. Detail:
[Bench record]({{ '/investigations/bench-record/' | relative_url }}).

**Models.** Size names are weight counts, not versions.

| Name on this page | About how many weights | What it is | Role |
| --- | --- | --- | --- |
| **0.5B** | 500 million | Qwen2.5-Coder-0.5B (Hui et al., 2024), Ollama `qwen2.5-coder:0.5b` or MLX 4-bit. Optional public LoRA [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b) (Hu et al., 2022), step 100 | Style prior. Smoke and Hub demo. Not daily `ask` / `run` |
| **7B** | 7 billion | `qwen2.5-coder:7b` unless a table names another tag | Same-night comparison |
| **8B** | 8 billion | Ollama `llama3.1:8b` (Grattafiori et al., 2024) | Daily default |

A “clean” 8B is the same 8 billion weights with no agent system
prompt and no loop. Other 7B–8B tags appear only where a table
names them. The 0.5B file on disk is about 400 MB; the 8B is about
4.9 GB.

**Tasks.** Four daily jobs on `demo/orders` unless a table names
another fixture. A case counts only if the function runs and does
the job — not if a file appeared, and not if the run said `done`.
Writes stay inside the named folder. There is no general shell.

**Scoring.** One run unless the table says otherwise. A gap of one
or two cases is noise. Ten of fifteen bench cases changed verdict
across three unchanged reruns; a single parse pass is not a score.
Compiler-bound cells (NameError `subtotl`, whole-line `return 0`
on a named sum, `page=` on a list URL) finish with no model. They
are not model scores.

Replay commands sit under each table. Scripts live in
`scripts/measure/`.

## Results

### The 0.5B as daily work

The tiny model: **500 million weights**, not the daily 8B.

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

That 500-million-weight model is a style prior. It is not daily
work. I am not training more 0.5B steps.

Write-up: [0.5B vibe review]({{ '/research-vibe-review/' | relative_url }})
· [Everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}).

### Exact stdout on the 0.5B

Same tiny Qwen2.5-Coder (**500 million weights**). Not `llama3.1:8b`.

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
Cite: [Cite]({{ '/cite/' | relative_url }}). Related work: [References]({{ '/references/' | relative_url }}).

### Sample four drafts, then greedy

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

### 8B daily jobs

**Example.** 5 September 2026. Ollama `llama3.1:8b`. Three jobs that
are not the built-in NameErrors, each three times, after the harness started
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
a real ≥1 KB fix the model wrote. This table is the daily loop on small
fixtures, not that bar. The first ≥1 KB cell is retired below.

### Same-night daily jobs, 7B coder

**Example.** 5 September 2026, evening. Same script
(`scripts/measure/eval_daily.py`), same twelve steps, same fixtures.
`llama3.1:8b` remasured, then `qwen2.5-coder:7b`.

| Model | Write tests | Add clamp | Logic bug | Passed |
| --- | --- | --- | --- | --- |
| `llama3.1:8b` | 3 / 3 | 3 / 3 | 3 / 3 | **9 / 9** |
| `qwen2.5-coder:7b` | 3 / 3 | **1 / 3** (two `ask` stops) | 3 / 3 | **7 / 9** |

The two-case gap is inside the noise this page already named. I did not
switch the default.

The logic-bug 3 / 3 on both sides is the compiler bind: a whole-line
`return 0` on a named sum. Same class as the retired ≥1 KB cell. It is
not a model writing `return sum(rows)`.

Replay:
`PYTHONPATH=src python3 scripts/measure/eval_daily.py --model qwen2.5-coder:7b`.

The 7B clip bar the same evening:

| Check | Harness 7B | Clean 7B |
| --- | --- | --- |
| Live parse | **10 / 15** | **1 / 15** |
| ≥1 KB clip fix | **0 / 3** (`steps`; writes `[]` × 3; turns non-empty) | **3 / 3** (one-shot) |

`everyday_ready` stayed false. The 7B coder speaks more first Actions
than a clean 7B and still does not write `clip`. Same wall as the 8B
clip remasure.

### More 7B–8B on disk, 5 September 2026

**Example.** Same script (`scripts/measure/eval_daily.py`), same twelve
steps, same fixtures. Tags now on this laptop: DeepSeek-Coder 6.7B,
StarCoder2 7B, CodeLlama 7B Python, OpenCoder 8B, SWE-agent-LM 7B.
OpenCoder and SWE-agent-LM came from Hub GGUFs
(`scripts/weights/import_hf_ollama.py`), not `ollama pull`.

**Result**

| Model | Write tests | Add clamp | Logic bug | Passed |
| --- | --- | --- | --- | --- |
| `llama3.1:8b` (same night) | 3 / 3 | 3 / 3 | 3 / 3 | **9 / 9** |
| `qwen2.5-coder:7b` (same night) | 3 / 3 | 1 / 3 | 3 / 3 | **7 / 9** |
| `deepseek-coder:6.7b` | 3 / 3 (compiler) | 1 pass, 1 `steps`, then 180s timeout | not run | incomplete |
| `deepseek-coder:6.7b` (empty VRAM) | 3 / 3 (compiler) | **1 pass** (`steps`), then 180s timeout | not run | incomplete |
| `starcoder2:7b` | 3 / 3 (compiler) | 180s timeout on the first generate | not run | incomplete |
| `codellama:7b-python` | 3 / 3 (compiler) | 180s timeout on the first generate | not run | incomplete |
| `opencoder:8b` | 3 / 3 (compiler) | 180s timeout on the first generate | not run | incomplete |
| `swe-agent-lm:7b` | 3 / 3 (compiler) | 180s timeout on the first generate | not run | incomplete |
| `swe-agent-lm:7b` (empty VRAM) | 3 / 3 (compiler) | 180s timeout on the first generate | not run | incomplete |

Write-tests 3 / 3 on the extra tags is the harness writing the AAA
test. The model is not called. The first job that does call it is
clamp, and a cold 7B–8B load plus one generate burned the 180s Ollama
cap. DeepSeek got one clamp through, then `steps`, then the same cap.

**Warm remasure, same evening.** Each extra tag was loaded first
(`keep_alive` 30 minutes). The pass finished. OpenCoder and
StarCoder2: warmup curl got 0 bytes in 300s, then clamp hit 180s.
SWE-agent-LM was already in memory and still hit 180s on the first
clamp generate. CodeLlama's warmup returned, then clamp still hit
180s. DeepSeek got one clamp through, then the same cap — same shape
as the cold pass. So this is not only a cold start. Write-tests
stayed 3 / 3 (compiler). Not a score.

**One-word generate, same evening.** Prompt: `Reply with the single
word ok.` Cap 180s. No daily job.

| Model | Reply | Wall |
| --- | --- | --- |
| `llama3.1:8b` (already loaded) | `Ok` | **3.9 s** |
| `qwen2.5-coder:7b` (swap from 8B) | `Ok.` | **11.5 s** |
| `deepseek-coder:6.7b` (after 7B coder) | `Ok` | **3.8 s** |
| `swe-agent-lm:7b` (after DeepSeek) | `OK.` | **19.6 s** |
| `starcoder2:7b` | timeout | 180 s |
| `codellama:7b-python` | timeout | 180 s |
| `opencoder:8b` | timeout | 180 s |

The 8B, the 7B coder, DeepSeek, and SWE-agent-LM answer. StarCoder2,
CodeLlama, and OpenCoder do not finish even this prompt inside the
cap that daily `run` uses. DeepSeek and SWE-agent-LM still timed out
on daily clamp — a one-word reply is not a score.

**Bare clamp prompt, same night.** The daily task text only. No
harness system prompt. Cap 180s. No file write.

| Model | Tokens | Wall |
| --- | --- | --- |
| `llama3.1:8b` | 384 | **22.3 s** |
| `qwen2.5-coder:7b` | 565 | **35.5 s** |
| `deepseek-coder:6.7b` | 281 | **24.0 s** |
| `swe-agent-lm:7b` | 450 | **39.6 s** |

Those four finish a short clamp ask. Daily clamp still timed out.

**First helper chat, same night.** The real first daily clamp
request: system 897 characters, user 5,935 characters, about 1,700
tokens (`num_ctx` 8,192). Same builder as `eval_daily.py`. Cap 180s.

| Model | Prompt tokens | Reply tokens | Wall |
| --- | --- | --- | --- |
| `llama3.1:8b` | 1,698 | 40 | **16.6 s** |
| `qwen2.5-coder:7b` | 1,706 | 53 | **12.4 s** |
| `deepseek-coder:6.7b` | 2,059 | 334 | **39.1 s** |
| `swe-agent-lm:7b` | 1,706 | 66 | **33.4 s** |

The 8B and the 7B coder opened with `Action: patch`. DeepSeek opened
with `Action: skill` then a patch. SWE-agent-LM opened with prose.
The helper first turn is not too big to finish once a generate has
already succeeded on the machine.

**Cold first helper chat, same night.** Unload (`keep_alive` 0),
then the same first clamp chat. Cap 180s.

| Model | Load | Wall |
| --- | --- | --- |
| `llama3.1:8b` | 8.0 s (7B still listed) | **17.1 s** |
| `deepseek-coder:6.7b` | 25.2 s (empty) | **53.6 s** |
| `swe-agent-lm:7b` | 28.2 s (empty) | **37.9 s** |

A clean cold first turn is well under 180s. Daily clamp still timed
out when a load returned no bytes.

**Clean daily remasure, same night.** `keep_alive` 0 did not evict
`qwen2.5-coder:7b`. Then `eval_daily.py --model deepseek-coder:6.7b`:
write-tests 3 / 3 (compiler), first clamp generate 180s timeout.
After the timeout, `qwen2.5-coder:7b` was still the loaded tag.
DeepSeek never sat in memory. That swap is the 180s miss — the same
first chat is 54 s from empty VRAM.

**Empty VRAM daily, same night.** `ollama stop qwen2.5-coder:7b`
left `{"models":[]}`. Then the same script:

| Job | Result |
| --- | --- |
| Write tests | 3 / 3 (compiler) |
| Add clamp | **1 pass** (`steps` after 12), then 180s timeout on the second |
| Logic bug | not run |

The same empty-VRAM start on `swe-agent-lm:7b` (`ollama stop`
DeepSeek first): write-tests 3 / 3 (compiler), first clamp generate
180s timeout. After the timeout the tag *was* loaded. An isolated
first chat on that tag was 38 s; the daily first generate did not
return in 180s. A follow-up `ok` generate while `/api/ps` still
listed the tag hit 60s. Listed is not the same as answering. After
`/api/ps` was empty again, the same `ok` prompt finished in **6.8 s**
(load 6.5 s). The wedge ended when the listed load expired.

**After expiry, same night.** Empty VRAM. The real first helper
clamp chat finished in **14.5 s** (load 4.9 s, 1,708 prompt tokens,
prose). Then `eval_daily.py` on that same loaded tag: write-tests
3 / 3 (compiler), first clamp generate 180s timeout. The isolated
chat answers; the daily first generate did not return in 180s.

**Agent body, same night.** `OllamaGenerate.body()` sends `model`,
`stream`, `messages`, and `options.num_ctx`. It does not send
`keep_alive`. Two identical first-turn POSTs of that body (about
6,800 characters, 8,192 context) both hit 180s. The same body with
`keep_alive` 30 minutes added finished in **115.7 s** (load 105.6 s,
1,709 prompt tokens, prose). After that reply, `/api/ps` listed
`llama3.1:8b`, not SWE. Still not a nine-cell table.

**Two `keep_alive` chats, same night.** Empty VRAM. The same Agent
body with `keep_alive` 30 minutes: first POST **180s** timeout
(`/api/ps` still empty). Immediate second POST **44.8 s** (load
18.0 s, 1,708 prompt tokens, prose). After that reply `/api/ps`
was empty again; a later check listed `llama3.1:8b`. One 115.7 s
finish does not make `keep_alive` a first-turn fix. Still not a
nine-cell table. **Do not switch.** Default stays `llama3.1:8b`.

Replay one finished table:
`PYTHONPATH=src python3 scripts/measure/eval_daily.py --model llama3.1:8b`.

Write-up: [Which model]({{ '/investigations/which-model/' | relative_url }})
· [Hub models]({{ '/investigations/hub-models/' | relative_url }}).

### 8B greenfield CLI

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

Same prompt, twelve steps, after that unused-function skip (#222). Same
evening. Ollama `llama3.1:8b`. Seeded list+show+mocks tree.

| Repeat | Comment gap | Stopped | Wrote |
| --- | --- | --- | --- |
| 1 | closed | `done` | `pkg/pr_review.py` × 2 |
| 2 | closed | `done` | `pkg/pr_review.py` |
| 3 | closed | `done` | `pkg/pr_review.py` |

**3 / 3** closed comment. Pagination and config stayed leftover — later
typed runs, not `--steps`. Replay:
`PYTHONPATH=src python scripts/measure/eval_cli_overflow.py`.

```bash
python-vibe run "add the comment subcommand and a mocked test"
```

Same evening, pagination from a list+show+comment tree. Typed:
`add pagination to the GitHub PR CLI`. After #228 (indented `page=`
counts; a module-level `pulls?page=` NameErrors on import). Twelve
steps × 3. Seeded list+show+comment tree.

| Repeat | Pagination gap | Stopped | Wrote |
| --- | --- | --- | --- |
| 1 | open | steps | none |
| 2 | open | steps | none |
| 3 | open | steps | none |

**0 / 3** closed pagination. Config stayed leftover. An earlier
twenty-step try on a leftover comment tree wrote `pkg/pagination.py`
and a module-level `?page=`, then drifted. The timed cell wrote
nothing.

Same prompt, after the harness put `page=` on the list URL (#233).
No model. Seeded list+show+comment tree.

| Repeat | Pagination gap | Stopped | Wrote |
| --- | --- | --- | --- |
| 1 | closed | `done` | `pkg/pr_review.py` |
| 2 | closed | `done` | `pkg/pr_review.py` |
| 3 | closed | `done` | `pkg/pr_review.py` |

**3 / 3** closed pagination. Config stayed leftover — a later typed
`run`, not `--steps`. Replay:
`PYTHONPATH=src python scripts/measure/eval_cli_overflow_page.py`.

```bash
python-vibe run "add pagination to the GitHub PR CLI"
```

Same evening, config from a list+show+comment+`page=` tree. Typed:
`add a config file via Path.home`. Twelve steps × 3.

| Repeat | Config gap | Stopped | Wrote |
| --- | --- | --- | --- |
| 1 | open | steps | none |
| 2 | open | steps | none |
| 3 | open | steps | none |

**0 / 3** closed config. The tree already looked finished, so the 8B
wrote nothing — the pagination 0/3 shape.

Same prompt, after the harness wrote `pkg/config.py` with `Path.home()`
(#241). No model. Seeded list+show+comment+`page=` tree.

| Repeat | Config gap | Stopped | Wrote |
| --- | --- | --- | --- |
| 1 | closed | `done` | `pkg/config.py` |
| 2 | closed | `done` | `pkg/config.py` |
| 3 | closed | `done` | `pkg/config.py` |

**3 / 3** closed config. Comment, pagination, and config are all later
typed runs that the harness can finish without the 8B. Replay:
`PYTHONPATH=src python scripts/measure/eval_cli_overflow_config.py`.

```bash
python-vibe run "add a config file via Path.home"
```

Everyday-ready is still the older bar.

### Everyday-ready bar

**Example.** Same evening, 5 September 2026. Ollama `llama3.1:8b`.
Fifteen `action_prompts.jsonl` rows for first Action. Then
`fix compute_total in pkg/util_stats.py so it sums the rows` on a
2.8 KB file that returns `0.0` — not `tota`, not `subtotl`. Three
repeats, twelve steps. Clean 8B is the same model with no
`AGENT_SYSTEM` and no agent loop (one-shot draft).

| Check | Harness 8B | Clean 8B |
| --- | --- | --- |
| Live parse | **11 / 15** | **0 / 15** |
| ≥1 KB logic fix | **0 / 3** (`steps`; two writes were tests only) | **3 / 3** (one-shot) |

After #229 (refuse rewriting a covering test). Same evening, same
script, same twelve steps.

| Check | Harness 8B | Clean 8B |
| --- | --- | --- |
| Live parse | **10 / 15** | **0 / 15** |
| ≥1 KB logic fix | **0 / 3** (`steps`; writes `[]` × 3) | **3 / 3** (one-shot) |

#229 stopped the test rewrite. It did not get a patch on
`compute_total`.

After #238 (refuse explore once the named impl is open). Same evening,
same script, same twelve steps.

| Check | Harness 8B | Clean 8B |
| --- | --- | --- |
| Live parse | **11 / 15** | **0 / 15** |
| ≥1 KB logic fix | **0 / 3** (`steps` × 2, `done` × 1; writes `[]` × 3) | **3 / 3** (one-shot) |

#238 did not get a patch on `compute_total`. Harness still beats clean
on parse. Clean still beats harness on the real fix.

Same evening, after overflow closed (#243). Same script, same twelve
steps.

| Check | Harness 8B | Clean 8B |
| --- | --- | --- |
| Live parse | **12 / 15** | **0 / 15** |
| ≥1 KB logic fix | **0 / 3** (`steps` × 2, `done` × 1; writes `[]` × 3) | **3 / 3** (one-shot) |

Parse moved. The fix did not: still no write to `compute_total`.

After #246 (bind a zero return to a sum) and #248 (print turns). Same
evening, same script, same twelve steps.

| Check | Harness 8B | Clean 8B |
| --- | --- | --- |
| Live parse | **9 / 15** | **0 / 15** |
| ≥1 KB logic fix | **3 / 3** (`done`; `pkg/util_stats.py`; turns `[]`) | **3 / 3** (one-shot) |

The model never ran. The harness wrote the sum and stopped. Parse still
beats clean. The fix ties clean, so the script's `harness_fix > clean_fix`
is false. **Not everyday-ready.**

That whole-line `return 0` / `return 0.0` on a named sum is the same
class as `subtotl` and `page=`: the compiler writes it. The ≥1 KB cell
that used that shape is **retired as a model job**. Do not remasure
`eval/fixtures/everyday_fix`. Replay of the last recorded night:
`PYTHONPATH=src python scripts/measure/eval_everyday_bar.py`.

The live ≥1 KB cell is `clip` in `eval/fixtures/everyday_live`: it
filters outliers instead of clamping them. The compiler leaves that
shape alone. Score it only when `#248` turns are non-empty.

After #254 (never-autofix clip cell). Same evening, same script, same
twelve steps.

| Check | Harness 8B | Clean 8B |
| --- | --- | --- |
| Live parse | **8 / 15** | **0 / 15** |
| ≥1 KB logic fix | **0 / 3** (`steps` × 2, `done` × 1; writes `[]` × 3; turns non-empty) | **3 / 3** (one-shot) |

The model ran. It did not write `clip`. Parse still beats clean. Clean
still one-shots the file. **Not everyday-ready.** Replay:
`PYTHONPATH=src python scripts/measure/eval_everyday_bar.py`.

Same evening, same script, `qwen2.5-coder:7b`: harness parse **10 / 15**
vs clean **1 / 15**; harness fix **0 / 3** vs clean **3 / 3**. Not
everyday-ready. Detail under
[same-night daily jobs](#same-night-daily-jobs-7b-coder).

### Four jobs, as typed

**Example.** Sample tree `demo/orders`. Two NameErrors sit in the code:

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

### Which small open model

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

### Hub GGUFs that Ollama does not ship

**Example.** 5 September 2026. Two small code models on Hugging Face
that this laptop can hold and that `ollama pull` cannot see.
`scripts/weights/import_hf_ollama.py` downloads the Q4_K_M GGUF (~4.7 GB)
and runs `ollama create`.

| Local tag | Source | What it is |
| --- | --- | --- |
| `opencoder:8b` | [infly/OpenCoder-8B-Instruct](https://huggingface.co/infly/OpenCoder-8B-Instruct) | Code-instruct 8B |
| `swe-agent-lm:7b` | [SWE-bench/SWE-agent-LM-7B](https://huggingface.co/SWE-bench/SWE-agent-LM-7B) | Qwen2.5-Coder-7B plus 5k traces from their agent |

```bash
python3 scripts/weights/import_hf_ollama.py --name opencoder
python3 scripts/weights/import_hf_ollama.py --name swe-agent-lm
python-vibe --model opencoder:8b run "add a function clamp and a unit test"
```

**Result.** Both tags are on disk. A one-word generate hit 180s on
OpenCoder and finished in 19.6 s on SWE-agent-LM. The first helper
clamp chat (~1,700 tokens) finished in 38 s on a clean cold load of
SWE-agent-LM. Daily clamp timed out when a load returned no bytes
(write-tests 3 / 3 is the compiler bind, no model). That is not a
score. Default stays `llama3.1:8b`. Other 7B–8B weights that fit
this laptop, and the ones that do not, are listed on
[Hub models]({{ '/investigations/hub-models/' | relative_url }}).

Write-up: [Hub models]({{ '/investigations/hub-models/' | relative_url }}).

### Train more, or not

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


### On a real repository

**Example.** Everything above uses `demo/orders`, a fixture with two
built-in bugs. This is the same tool pointed at a working repository of
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

### When a run says done and means nothing

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

### Asking a bigger model, rarely

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

### A chain of easy tasks

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

### The instrument was broken

A day spent asking whether a bigger model breaks the wall found two
faults in the benchmark instead. Both were invisible while only local
models were measured; both would have made a fine-tune evaluation wrong.

**Result**

| Tier 3, ten passes | Nobody answering | Answered |
| --- | --- | --- |
| `llama3.1:8b` | 13 of 20 | **14 of 20** |
| `qwen2.5-coder:7b` | 7 of 20 | **13 of 20** |

A run that stops to ask needs somebody to answer, and nobody was there,
so the question ended the run as a failure. `qwen2.5-coder:7b` asks in
eleven runs of twenty where `llama3.1:8b` asks in one, so the benchmark
was measuring willingness to act without asking.

The second fault only appears against a hosted model: it wraps drafts in
markdown fences, the fence reaches the file unchanged, and the result is
a `SyntaxError`. Nine of ten runs then produced nothing that would load.
A 14B, meanwhile, times out on this machine three times out of three.

So whether size breaks the wall is still unanswered, and every model
number published before this is unsafe.

Write-up: [The instrument was broken]({{ '/investigations/measuring/' | relative_url }}).

### Two models, one wall

Before training anything, the cheap question: is the base model the
constraint? The benchmark takes a model name, so it costs one command.

**Result**

| Seventy-five runs each | Worked | Wrote nothing | Wrote the wrong thing |
| --- | --- | --- | --- |
| `llama3.1:8b` | 51 of 75 | 8 | **16** |
| `qwen2.5-coder:7b` | 50 of 75 | **18** | 7 |

One case apart on the score, and almost opposite failures. Two models of
different lineage meeting the same wall says something about the size
rather than about either model.

It also moves the bar for a fine-tune. Wrong-code failures can be more
than halved without a single extra run working — they just become
refusals to act. Raising the count that works is the target; improving
the manner of failing is not.

The per-tier splits in that run suggested sending some task types to one
model and some to the other. Checked at ten passes, the bugfix tier came
out level at 18 of 20 each — the apparent gap was one case in a five-run
sample — while tier 3 widened to 13 against 7. So there is no task type
worth routing to `qwen2.5-coder`, and five passes turns out to be too
few to compare two models per tier at all.

Write-up: [Two models, one wall]({{ '/investigations/two-models/' | relative_url }}).

### Where the failures are

Seven harness changes measured, six moved nothing. So rather than
measure an eighth, seventy-five runs were classified by what they left
behind, and eight hundred and thirty-six model turns by what the model
was sent.

**Result**

| Of the 24 failures in 75 runs | Share |
| --- | --- |
| wrote something, but not the thing asked for | **42%** |
| wrote nothing at all | 33% |
| wrote something, it did not do the job | 25% |
| **claimed success having written nothing** | **0%** |

Two thirds of what fails is plausible, wrong code, and nothing
deterministic separates that from plausible, right code — only running
it does, and the suite already runs. The harness has taken the failures
it can take.

The last row is the week's one measured gain: that shape was two of
nine failures a week ago and is nought of twenty-four now. Not a higher
pass rate — no lies about it.

A quarter of every run is the harness saying no: 23% of turns are a
refusal or a nudge, most often "run the tests before finishing" (58),
"read the file before patching it" (36) and "that is the wrong file"
(32).

Write-up: [Where the failures are]({{ '/investigations/failures/' | relative_url }}).

### What the harness cannot fix

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

### A larger open model

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

## Discussion

The helper is the load-bearing part for the jobs it can finish
without a model. First-run four went **0 / 4** to **4 / 4** once
the compiler wrote the NameError, the test, and `total_lines`.
Greenfield overflow (comment, pagination, config) closed the same
way. That is the SWE-agent lesson at a smaller tree: the interface
moves the score.

The model still has to do the rest. Daily `llama3.1:8b` is **9 / 9**
on small fixtures and **8 / 15** on first-step parse. The
everyday-ready bar asks for a ≥1 KB logic fix the helper cannot
write (`clip`). Harness **0 / 3**, clean 8B **3 / 3**. So the loop
helps the model pick an Action and hurts it on the one cell that
still counts.

The 0.5B (500 million weights) is a style prior. Exact-stdout **7 / 54** base,
**12 / 54** after one repair; greedy LoRA **0 / 54**. Sampling
finds a different set, not a superset. That matches Feedback Over
Form: a traceback fixes `NameError` and `SyntaxError`, not logic.

A 7B coder is close (**7 / 9**) and not better. Extra 7B–8B tags
timed out on the first daily generate that calls the model. Default
stays `llama3.1:8b`. Writing on a 4,580-file tree is **1 / 12**.
Do not treat the fixture scores as a real-repo review.

Two models of different lineage hit the same wall (51 vs 50 of 75).
Wrong-code failures can become refusals without the pass count
moving. Raising the count that works is the target.

## Limitations

One laptop, 18 GB unified memory. One run unless a table says
otherwise; gaps of one or two cases are noise. Several published
cells are compiler binds, not model writes. The instrument was
wrong for part of the month: unanswered `ask` stops, and markdown
fences reaching the file. Every model number from before that note
is unsafe.

This project does **not** report a SWE-bench score. The public
numbers are four jobs on `demo/orders` and a 4,580-file write rate
of **1 / 12**. No hosted chat product is named. No claim that the
0.5B LoRA audited a real repository.

## Conclusion

Keep `llama3.1:8b`. Do not train more 0.5B steps. Do not switch
the default to a 7B coder or a Hub GGUF that misses the 180s
generate cap. The helper should keep finishing compiler jobs. The
everyday-ready bar stays: beat a plain 8B at the next step **and**
at a real bug the helper cannot write. It does not, yet.

## References

Bichel, Y. (2026). *python-vibe* [Computer software].
<https://github.com/YauhenBichel/python-vibe>

Bichel, Y. (2026, September 5). 0.5B exact-stdout eval. In
*python-vibe* experiments.
<https://yauhenbichel.github.io/python-vibe/investigations/held-out-exec-eval/>

Bichel, Y. (2026, September 5). 0.5B sample-and-run. In
*python-vibe* experiments.
<https://yauhenbichel.github.io/python-vibe/investigations/sample-and-run/>

Belcak, P., Heinrich, G., Diao, S., Fu, Y., Dong, X.,
Muralidharan, S., Lin, Y. C., & Molchanov, P. (2025). Small
language models are the future of agentic AI.
<https://arxiv.org/abs/2506.02153>

Grattafiori, A., et al. (2024). *The Llama 3 herd of models*.
<https://arxiv.org/abs/2407.21783>

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S.,
Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large
language models. *ICLR*.
<https://arxiv.org/abs/2106.09685>

Hui, B., Yang, J., Cui, Z., Yang, J., et al. (2024).
*Qwen2.5-Coder technical report*.
<https://arxiv.org/abs/2409.12186>

Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O.,
& Narasimhan, K. (2024). SWE-bench: Can language models resolve
real-world GitHub issues? *ICLR* (oral).
<https://arxiv.org/abs/2310.06770>

Liu, J., Xia, C. S., Wang, Y., & Zhang, L. (2023). Is your code
generated really correct? Rigorous evaluation of large language
models for code generation. *NeurIPS* (EvalPlus / HumanEval+).
<https://arxiv.org/abs/2305.01210>

McAndrews, C. J. (2026). Feedback over form: Why execution
feedback matters more than pipeline topology in 1–3B code
generation.
<https://arxiv.org/abs/2604.21950>

Shinn, N., Cassano, F., Labash, B., Gopinath, A., Narasimhan, K.,
& Yao, S. (2023). Reflexion: Language agents with verbal
reinforcement learning. *NeurIPS*.
<https://arxiv.org/abs/2303.11366>

Yang, J., Jimenez, C. E., Wettig, A., Lieret, K., Yao, S.,
Narasimhan, K., & Press, O. (2024). SWE-agent: Agent-computer
interfaces enable automated software engineering. *NeurIPS*.
<https://arxiv.org/abs/2405.15793>

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., &
Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language
models. *ICLR*.
<https://arxiv.org/abs/2210.03629>

APA and BibTeX for this software: [Cite]({{ '/cite/' | relative_url }}).
The longer related-work list: [References]({{ '/references/' | relative_url }}).
