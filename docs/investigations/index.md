---
title: Research
description: Laptop measurements and design notes for python-vibe. Dates are the day of the run.
date: 2026-08-29
---

# Research

The scores, with the example and the table, are on
[Experiments]({{ '/investigations/experiments/' | relative_url }}).
Dates are the day of the measurement. Public pages do not name other
editors or chat products.

<div class="stats">
  <div class="stat"><b>0 / 4</b><span>0.5B vibe</span></div>
  <div class="stat"><b>4 / 4</b><span>Start commands after the harness</span></div>
  <div class="stat"><b>8 / 15</b><span>8B live parse</span></div>
  <div class="stat"><b>6–9 / 9</b><span>8B when code must run, six runs</span></div>
</div>

| Experiment | Example | Result |
| --- | --- | --- |
| 0.5B as daily work | weekday helper, count-md, `Action:` | 0 / 4 vibe, 0 / 2 parse |
| Four Start commands | `demo/orders`, `subtotl` / `stauts` | 0 / 4 then 4 / 4 |
| Which open model | same bench, code must run | 8B 6–9 / 9 over six runs; 30B timeout |
| Train more? | 35 pairs, 30 traces | No. Later ~2k clean turns |
| Larger model on a GPU | `--engine openai` | No live 14B / 32B number yet |

What you type:
[Scenarios]({{ '/scenarios/' | relative_url }}).

## Notes

| Note | What it answers |
| --- | --- |
| [Experiments]({{ '/investigations/experiments/' | relative_url }}) | Every measured run, with the example and the score. |
| [First-run four jobs]({{ '/investigations/first-run-four/' | relative_url }}) | The four Start commands on `demo/orders`. |
| [Local loop vs hosted agents]({{ '/investigations/local-vs-cloud/' | relative_url }}) | Every shipped path against a hosted IDE agent. |
| [Same jobs, same evening]({{ '/investigations/same-jobs/' | relative_url }}) | Eleven demo tasks. Laptop 8B vs a hosted IDE agent. |
| [What to improve]({{ '/investigations/what-to-improve/' | relative_url }}) | Which gaps a harness can close, and which it cannot. |
| [Small models, classic development]({{ '/investigations/small-llm-harness/' | relative_url }}) | How an 8B reaches bigger-model outcomes: oracles. |
| [Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}) | When to train again. Not on 35 pairs. Not on 30 traces. |
| [Model lanes]({{ '/investigations/model-lanes/' | relative_url }}) | Which local weight for questions, writes, structure, ship. |
| [Which model]({{ '/investigations/which-model/' | relative_url }}) | Three local models on the same eleven jobs. |
| [Hub models]({{ '/investigations/hub-models/' | relative_url }}) | Hugging Face ids. 1.5B and 1B do not parse Action:. |
| [Cloud weights]({{ '/investigations/cloud-weights/' | relative_url }}) | A larger model on a rented GPU. The harness stays here. |
| [Everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}) | Why the 0.5B LoRA is not daily work. |
| [Skills]({{ '/skills/' | relative_url }}) | The twenty kit skills and when each one loads. |
| [Platform engineering]({{ '/investigations/platform-engineering/' | relative_url }}) | Small files that must work on every OS. |
| [Everyday skills]({{ '/investigations/everyday-skills/' | relative_url }}) | Skills written as one copy-paste Action for an 8B. |
| [Harness comparison]({{ '/investigations/harness-comparison/' | relative_url }}) | What transfers from other published harnesses. |
| [0.5B vibe review]({{ '/research-vibe-review/' | relative_url }}) | Held-out vibe tasks and a 100-file stub walk. |
| [Architecture]({{ '/architecture/' | relative_url }}) | Bottom-up layers. A cycle fails the merge gate. |
