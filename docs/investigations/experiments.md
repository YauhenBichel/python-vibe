---
title: Experiments
description: Every laptop measurement for python-vibe, with the date and the score. 29–30 August 2026. Not everyday-ready.
permalink: /investigations/experiments/
date: 2026-08-29
type: article
---

# Experiments

Every run that produced a number or a yes/no, on one laptop, 29–30
August 2026. Dates are the day of the measurement. A page that only
states a decision, with no new run, is listed under notes.

**Not everyday-ready.** Everyday-ready still means beating an untuned
`llama3.1:8b` on live parse **and** a real ≥1 KB fix.

Related: [Live scenarios]({{ '/scenarios/' | relative_url }}) ·
[Research index]({{ '/investigations/' | relative_url }}) ·
[Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}).

A Medium article from this table is kept in `drafts/medium-experiments.md`
in the repository, so it is not published here as well.

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#measured">Measured</a></li>
  <li><a href="#protocol-only">Protocol only</a></li>
  <li><a href="#not-an-experiment">Not an experiment</a></li>
</ol>
</nav>

## Measured

| When | What we ran | Result | Write-up |
| --- | --- | --- | --- |
| 29 Aug | 0.5B held-out vibe (weekday, count-md, jsonl, docstring) | **0 / 4** | [0.5B vibe review]({{ '/research-vibe-review/' | relative_url }}) |
| 29 Aug | 0.5B parsed `Action:` | **0 / 2** | [Everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}) |
| 29 Aug | 0.5B QLoRA val loss | Overfit after step 100. Hub weight is that checkpoint | [0.5B vibe review]({{ '/research-vibe-review/' | relative_url }}) |
| 29 Aug | 100-file stub walk | A hundred “no issues”. Not a review | [0.5B vibe review]({{ '/research-vibe-review/' | relative_url }}) |
| 29 Aug | Four Start commands on `demo/orders`, first typing | **0 / 4** shippable | [First-run four]({{ '/investigations/first-run-four/' | relative_url }}) · [Live scenarios]({{ '/scenarios/' | relative_url }}) |
| 29–30 Aug | Same four commands after harness oracles | **4 / 4** on this tree. Three used no model | [First-run four]({{ '/investigations/first-run-four/' | relative_url }}) |
| 29–30 Aug | `find the NameError in src/orders_controller.py` | Asks. Does not write `return status`. Answering `ok` writes `return "ok"` with no model | [First-run four]({{ '/investigations/first-run-four/' | relative_url }}) |
| 29 Aug | `eval_everyday.py --live`, `llama3.1:8b` | **8 / 15** first Actions. Offline fixtures clean. Above the 50% floor | [First-run four]({{ '/investigations/first-run-four/' | relative_url }}) |
| 29 Aug | `scripts/bench.py` tiers 1, 2, 4, 5 (code must run) | 8B **9 / 9**. 7B coder **7 / 9**. 30B **timeout** | [Which model]({{ '/investigations/which-model/' | relative_url }}) |
| 29 Aug | Same bench, platform tier 6 | 8B 1 / 4. 7B coder **2 / 4**. 30B 0 / 4 timeout | [Which model]({{ '/investigations/which-model/' | relative_url }}) |
| 29 Aug | First Action on Hub 1B and 1.5B | **0**. Prose or `# patch`, no `Action:` | [Hub models]({{ '/investigations/hub-models/' | relative_url }}) |
| 29 Aug | Eleven `demo.py` jobs, 8B vs a hosted IDE agent | Laptop does not match the hosted column | [Same jobs]({{ '/investigations/same-jobs/' | relative_url }}) · [Local vs hosted]({{ '/investigations/local-vs-cloud/' | relative_url }}) |
| 29 Aug | Named-file review of a compiler finding | Quotes the undefined name. No generate | [Small models, classic development]({{ '/investigations/small-llm-harness/' | relative_url }}) |
| 29 Aug | Skills written as one copy-paste `Action:` | 8B copies; essays fail | [Everyday skills]({{ '/investigations/everyday-skills/' | relative_url }}) |
| 29 Aug | pathlib / both venv layouts / config suffixes | Wired. `os.path.join` and a POSIX-only venv path are refused | [Platform engineering]({{ '/investigations/platform-engineering/' | relative_url }}) |

Read the four Start commands as four commands, not as a score. The
fifteen live parse cases changed verdict on ten of them across three
unchanged reruns. Rows that never call the model hold still.

## Protocol only

These are how the next run will be scored. They do not have a live
number yet.

| Planned run | How it will be scored | Write-up |
| --- | --- | --- |
| Cloud 14B / 32B via `--engine openai` | Same `demo/orders` checks as the laptop 8B. Beat cell A or keep the 8B | [Cloud weights]({{ '/investigations/cloud-weights/' | relative_url }}) |
| 7B LoRA after ~2k oracle-clean `--record` turns | `eval_everyday.py --live` and `scripts/demo.py`. Lose to the 8B → delete the adapter | [Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}) |

Do not train more 0.5B steps. Do not train an 8B LoRA on thirty seed
rows. Those are decisions, already written in
[fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}).
