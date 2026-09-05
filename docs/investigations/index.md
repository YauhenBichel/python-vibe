---
title: Research
description: Laptop measurements and design notes for python-vibe. Dates are the day of the run.
date: 2026-09-05
---

# Research

The scores, with the example and the table, are on
[Experiments]({{ '/investigations/experiments/' | relative_url }}).
Dates are the day of the measurement. Public pages do not name other
editors or chat products.

<div class="stats">
  <div class="stat"><b>12 / 18</b><span>0.5B four drafts + later loop</span></div>
  <div class="stat"><b>0 / 54</b><span>greedy 0.5B LoRA</span></div>
  <div class="stat"><b>8 / 15</b><span>8B live parse</span></div>
  <div class="stat"><b>8 / 9</b><span>8B daily jobs, 5 Sep 2026</span></div>
</div>

| Experiment | Example | Result |
| --- | --- | --- |
| 0.5B as daily work | weekday helper, count-md, `Action:` | 0 / 4 vibe, 0 / 2 parse |
| 0.5B exact stdout | 18 held-out scripts, 3 repeats, Ollama | **7 / 54** base, **12 / 54** with repair |
| 0.5B sample-and-run | same 18, MLX, four drafts then greedy | **9 / 18** then **12 / 18** with later loop; 0 hint-repairs; greedy LoRA **0 / 54** |
| 8B daily jobs | write-tests, clamp, logic bug, 3 repeats | **8 / 9** |
| 8B greenfield CLI | GitHub PR CLI, empty folder, 3 repeats | **3 / 3** after #220 (suite + `done`); overflow comment **3 / 3** after #222; pagination **3 / 3** after #233; config **3 / 3** after #241 |
| Everyday-ready bar | 15 parse prompts + ≥1 KB logic fix × 3 | after #254: harness parse **8 / 15** vs clean **0 / 15**; harness fix **0 / 3** (writes `[]` × 3; turns non-empty) vs clean **3 / 3**. Clip cell. Not everyday-ready. |
| Four Start commands | `demo/orders`, `subtotl` / `stauts` | 0 / 4 then 4 / 4 |
| Which open model | same bench, code must run | 8B 6–9 / 9 over six runs; 30B timeout |
| Train more? | 35 pairs, 30 traces | No. Later ~2k clean turns |
| Larger model on a GPU | `--engine openai` | No live 14B / 32B number yet |
| A real repository | 4,580 files, not a fixture | reading works; writing 1 / 12 |

What you type:
[Scenarios]({{ '/scenarios/' | relative_url }}).

## Notes

| Note | What it answers |
| --- | --- |
| [Experiments]({{ '/investigations/experiments/' | relative_url }}) | Every measured run, with the example and the score. |
| [0.5B exact-stdout eval]({{ '/investigations/held-out-exec-eval/' | relative_url }}) | 7 / 54 base, 12 / 54 after one repair. Ollama. 5 Sep 2026. |
| [0.5B sample-and-run]({{ '/investigations/sample-and-run/' | relative_url }}) | Four drafts 9 / 18. Later loop 12 / 18, 0 hint-repairs. Greedy LoRA 0 / 54. 5 Sep 2026. |
| [Cite]({{ '/cite/' | relative_url }}) | APA and BibTeX for the software and that measurement. |
| [Bench record]({{ '/investigations/bench-record/' | relative_url }}) | The machine, what fits in 18 GB, and all six runs behind the numbers. |
| [First-run four jobs]({{ '/investigations/first-run-four/' | relative_url }}) | The four Start commands on `demo/orders`. |
| [Local loop vs hosted agents]({{ '/investigations/local-vs-cloud/' | relative_url }}) | Every shipped path against a hosted IDE agent. |
| [Same jobs, same evening]({{ '/investigations/same-jobs/' | relative_url }}) | Eleven demo tasks. Laptop 8B vs a hosted IDE agent. |
| [Two models, one wall]({{ '/investigations/two-models/' | relative_url }}) | Two 7-8B models score 51 and 50 of 75, and fail in almost opposite ways. |
| [Where the failures are]({{ '/investigations/failures/' | relative_url }}) | Seventy-five runs classified. Two thirds of failures are wrong code, and nothing claims success having written nothing. |
| [What the harness cannot fix]({{ '/investigations/limits/' | relative_url }}) | A refusal calibrated 0 for 5, a pointer the model ignored 3 of 3, and an excerpt that cut out the very lines the task named. |
| [When a run says done and means nothing]({{ '/investigations/false-finish/' | relative_url }}) | Five runs in ten claimed work they had not done. After two fixes, none did. |
| [Asking a bigger model]({{ '/investigations/asking-a-bigger-model/' | relative_url }}) | A run that stops to ask has failed 3 times out of 3. That makes the question worth a remote call, and a spent step budget not. |
| [Small steps, measured]({{ '/investigations/small-steps/' | relative_url }}) | Splitting one task into a chain of easy ones bought nothing and cost twice the time. The loop was already a chain. |
| [What to improve]({{ '/investigations/what-to-improve/' | relative_url }}) | Which gaps a harness can close, and which it cannot. |
| [Small models, classic development]({{ '/investigations/small-llm-harness/' | relative_url }}) | How an 8B reaches bigger-model outcomes: oracles. |
| [Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}) | When to train again. Not on 35 pairs. Not on 30 traces. |
| [Model lanes]({{ '/investigations/model-lanes/' | relative_url }}) | Which local weight for questions, writes, structure, ship. |
| [Which model]({{ '/investigations/which-model/' | relative_url }}) | Three local models on the same eleven jobs. |
| [Hub models]({{ '/investigations/hub-models/' | relative_url }}) | Hugging Face ids. 1.5B and 1B do not parse Action:. |
| [Cloud weights]({{ '/investigations/cloud-weights/' | relative_url }}) | A larger model on a rented GPU. The harness stays here. |
| [Everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}) | Why the 0.5B LoRA is not daily work. |
| [Skills]({{ '/skills/' | relative_url }}) | The twenty-four kit skills and when each one loads. |
| [Platform engineering]({{ '/investigations/platform-engineering/' | relative_url }}) | Small files that must work on every OS. |
| [Everyday skills]({{ '/investigations/everyday-skills/' | relative_url }}) | Skills written as one copy-paste Action for an 8B. |
| [Harness comparison]({{ '/investigations/harness-comparison/' | relative_url }}) | What transfers from other published harnesses. |
| [0.5B vibe review]({{ '/research-vibe-review/' | relative_url }}) | Held-out vibe tasks and a 100-file stub walk. |
| [Architecture]({{ '/architecture/' | relative_url }}) | Bottom-up layers. A cycle fails the merge gate. |
