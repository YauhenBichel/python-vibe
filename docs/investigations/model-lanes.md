---
title: Model lanes
description: Which local weight to use for which py-harness job. Routing versus cascading, measured on this laptop 29 Aug 2026.
permalink: /investigations/model-lanes/
date: 2026-08-29
type: article
---

# Model lanes

**Question.** Should py-harness use a different local model for questions,
writes, refactors, and ship work?

**Answer.** Yes as **lanes**. No as an automatic swap onto the 0.5B sidecar
or the 30B that timed out. The everyday brain stays `llama3.1:8b` until a
7B coder is pulled and beats it on a live write. The cheap “second model”
you already have is not another weight — it is the oracle.

See which lane a task is, with no model call:

```bash
py-harness route "what does compute_total return?"
py-harness route "add multiply(a, b) and a test"
py-harness route "create a pr for #50"
```

Related: [fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }})
· [hub models]({{ '/investigations/hub-models/' | relative_url }})
· [everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#what-is-on-this-laptop">What is on this laptop</a></li>
  <li><a href="#what-the-papers-mean-by-routing">What the papers mean by routing</a></li>
  <li><a href="#lanes">Lanes</a></li>
  <li><a href="#live-write-jobs-same-afternoon">Live write jobs, same afternoon</a></li>
  <li><a href="#how-to-save-money">How to save money</a></li>
</ol>
</nav>

## What is on this laptop

| Weight | Size | Role today |
| --- | --- | --- |
| `llama3.1:8b` | 4.9 GB | Everyday default. Chat + tools. |
| `qwen2.5-coder:0.5b` | 397 MB | Smoke / `--tiny` only. Action parse 0/2. Held-out vibe 0/4. |
| `qwen2.5-coder:1.5b` | 986 MB | On disk. Not measured on this Action protocol. |
| `qwen2.5-coder:7b` | — | **Not pulled.** Optional write specialist later. |
| `qwen3coder` (30B-class) | 18 GB | Timed out at the 180s Ollama cap. |

## What the papers mean by routing

**Router** (RouteLLM, Hybrid-LLM): pick one model *before* the first
token. Good when task kinds differ and the pick is cheap.

**Cascade** (FrugalGPT, AutoMix, SynConfRoute): run a cheap model, then a
*verifier* decides whether to escalate. The papers that work on code use
**syntax and tests** as the judge, not a second LLM.

py-harness already cascades on oracles (`ast.parse`, undefined names,
a test that sets up its inputs, the old definition gone). Escalation is **another turn of the same
8B**, not a load of 18 GB mid-run. Loading a second weight on a laptop
is the expensive move. A hosted usage pool is what you are trying not
to open.

A learned RouteLLM is out of scope. `looks_like_*` is the router. It is
already deterministic.

## Lanes

| Lane | Task looks like | Model | Do not |
| --- | --- | --- | --- |
| `none` | issue / branch / commit / pr / merge | none | Pull a 30B to write a PR title |
| `read` | what / why / how, review one named file | `llama3.1:8b` | `--tiny`. 0.5B misses `Action:` |
| `write` | add, bugfix, rename, tests, script, HTTP, paths | `llama3.1:8b` | Auto-switch to 30B. Optional `--model qwen2.5-coder:7b` only after it is pulled and measured |
| `structure` | review the tree / one-split loop | `llama3.1:8b` | Expect a 30B to replace the design scan |

`py-harness route` prints the lane. `--model` still wins when you pass
it. The default does not change by itself, so a 1.5B that has never
parsed `Action:` cannot sneak into a write.

## Live write jobs, same afternoon

`scripts/run/demo.py` on `demo/orders`, `llama3.1:8b`.

| When | Job | Verified | Seconds | What happened |
| --- | --- | --- | --- | --- |
| 29 Aug ~15:03, 12 steps | write-tests for `apply_discount` | passed | 19 | Oracle held. Suite names the function. |
| 29 Aug ~15:03 | NameError in `src/orders.py` | failed | 37 | Left `subtotal` unbound. Hit the step budget. |
| 29 Aug ~15:03 | rename `calc` → `multiply` | failed | 26 | Twelve `patch` turns, **no writes**. `Find:` never hit. |
| 29 Aug ~15:18, 8 steps | NameError | passed on disk | 13 | Autofix bound `subtotl`. 8B then asked a question. |
| 29 Aug ~15:18 | rename | passed | 10 | Autofix renamed `def calc`. 8B ran tests and said done. |
| 29 Aug ~15:20 | NameError | passed | 0.1 | Harness wrote the bind, ran tests, **no model**. |
| 29 Aug ~15:20 | rename | passed | 0.1 | Harness renamed `def calc`, ran tests, **no model**. |
| 29 Aug ~15:21 | write-tests for `apply_discount` | passed | 13 | Still a model job. Suite names the function. |

A different weight would not have made `Find:` unique. Those two misses
are now **harness jobs**. Before the first generate, the harness:

- binds a unique NameError typo (`subtotl` → `subtotal` next to
  `subtotal = …`)
- renames `def calc` to the name in the task and **keeps the typed
  signature** (the skill’s `def calc(x, y):` never matched
  `def calc(x: int, y: int)`)
- runs the project suite itself. If that is green, the run ends
  **without loading a model**. Same 8B. No 7B download.

## How to save money

1. Keep one everyday 8B loaded. Switching models costs RAM and time.
2. Use `route` to see the lane. Use `--tiny` only for smoke.
3. Do not pull the 30B for daily writes. It already lost on latency.
4. If you want a **write specialist**, pull `qwen2.5-coder:7b` and
   measure `scripts/run/demo.py --model qwen2.5-coder:7b --case bugfix`
   against this afternoon’s 8B log. Keep it only if the independent
   file check passes and the 8B still fails.
5. A unique typo or rename is finished by the harness. Do not spend
   tokens asking what to do next.

The product that saves money is **one capable local model plus oracles**,
not a menu of five weights for five moods.
