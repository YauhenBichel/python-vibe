---
title: Local loop vs hosted agents
description: Every python-vibe path against a hosted IDE agent. Measured on a laptop, 29 Aug 2026. None of the local brains match a hosted agent.
permalink: /investigations/local-vs-cloud/
date: 2026-08-29
type: article
---

# Local loop vs hosted agents

Every weight, CLI, and wiring path in this repo, set next to a hosted IDE agent with native tools, extra servers, a browser, and a 100k–1M context window.

Measured on one laptop (29 Aug 2026): Ollama `llama3.1:8b`, `qwen2.5-coder:0.5b`, Hub [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b). The hosted column is a frontier coding agent in an IDE, not a local weight.

**None of the python-vibe brains match a hosted IDE agent.** The published LoRA is 0.5B. The everyday default is untuned `llama3.1:8b`. A 7B LoRA is a config only — not trained.

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#every-python-vibe-path">Every python-vibe path</a></li>
  <li><a href="#same-jobs-every-path">Same jobs, every path</a></li>
  <li><a href="#use-python-vibe-when">Use python-vibe when</a></li>
  <li><a href="#use-a-hosted-ide-agent-when">Use a hosted IDE agent when</a></li>
</ol>
</nav>

| On this laptop | Result |
| --- | --- |
| Published Hub model | 1 (`python-vibe-0.5b`) |
| 0.5B parsed Actions that day | 0 / 2 |
| 8B first Action on three scoped tasks | 3 / 3 |
| 8B live eval parse floor | 2 / 3 |

First Action on the same three tasks (`scripts/measure/skill_probe.py` plus one live `agent.py` question). A score of 1 means the first parsed Action was the intended one (`done` on a question, `patch` + `Append:` on add).

| Task | 0.5B | 8B + harness | Hosted IDE agent |
| --- | --- | --- | --- |
| `what does listen_addr return?` | 0 | 1 | 1 |
| complete after two blocked drafts | 0 | 1 | 1 |
| add `multiply` + test | 0 | 1 | 1 |

The 8B still answered `listen_addr` as “a tuple of host and port” and omitted env and argv defaults. The hosted agent quoted both in one read.

## Every python-vibe path

| Path | What it is | On the laptop | Vs a hosted IDE agent |
| --- | --- | --- | --- |
| `YauhenBichel/python-vibe-0.5b` | Only published Hub weights. QLoRA on Qwen2.5-Coder-0.5B. Style prior from ~45 pairs. | Adapters on disk. Held-out vibe tasks 0/4. A 100-file stub walk returned “no issues”. | Not a daily coding model. Misses `Action:` lines. Do not train more 0.5B for agency. |
| `qwen2.5-coder:0.5b` (`--tiny` / `serve.py`) | Base 0.5B without the LoRA. Linux serve is this + harness, not MLX adapters. | Pulled (~400 MB). No parse on `listen_addr` or add-multiply (echoed the skill). | Worse than 8B. Smoke and CI only. |
| `vibe.py` / `batch_review.py` | One-shot draft or one-file review. No explore loop. | Shipped. A batch of 100 stubs was not a review. | A hosted agent walks many files, applies diffs, and runs tests. |
| `agent.py` + `llama3.1:8b` | Everyday default. Text Actions + locate prelude + skills and the write limit. | Pulled (~5 GB). After a hint fix: `done` in one step on `listen_addr`. Add-feature probe: `patch` + `Append:`. Parse eval 2/3. | Closest laptop stand-in. Answers are shallow. No extra tools, no browser, text files only (no secrets). 20 steps max. |
| `agent.py` + qwen2.5-coder 7B / 14B / 32B | Listed in `everyday.py`. Same harness. | Not pulled. Not measured that day. | Likely stronger Python than 8B. Still a text protocol, not native IDE tools. 32B is RAM-heavy. |
| `train.py --everyday` (`python-vibe-8b`) | MLX LoRA on Qwen2.5-Coder-7B-Instruct-4bit. Needs ~2k tool traces. | Config only. `adapters/python-vibe-8b` is not trained. Seed data is 30 train rows. | Could teach `Action:` format. Will not grow context, extra tools, or an IDE loop. |
| `openai_compat.py` | Local OpenAI `/v1` so an editor can pick `llama3.1:8b`. | Docs shipped. Does not add tools. The editor still drives the loop. | Wires a python-vibe brain into an editor chat. Quality stays 8B-class unless you pick a hosted model. |

A 30B coder may already sit on the same machine as `--model`. It is not in `EVERYDAY_OLLAMA_CHOICES`. It still has no native IDE tools.

## Same jobs, every path

| Job | 0.5B LoRA / `--tiny` | 8B + harness | Hosted IDE agent |
| --- | --- | --- | --- |
| Answer `what does listen_addr return?` | No Action. Echoed the skill line. | `done` in 1 step after a hint fix. “tuple of host and port.” Missed env + argv. | One read. Quoted host/port env names and argv. |
| Add `multiply(a, b)` + test | No parse. Wrote `Action: patch + Append:` as one line. | `patch Path: pkg/mathy.py` + `Append: def multiply…` | Function + test + run. |
| Held-out vibe (weekday, count-md) | 0 / 4 with harness. | Eval gate exists. Live parse 2/3. Not everyday-ready. | Ordinary edits. |
| Review a 100-file repo | 100× “no issues” on stubs. | Need `--scope` + `map`. 8B will not walk the tree. | Multi-file, tests, extra tools. |
| Browser / extra tools / any language | No. `run` is Python argv. Writes are limited to project text files. | No. | Yes. |
| Offline / $0 API | Yes. ~400 MB. | Yes. ~5 GB RAM for 8B Q4. | No. Cloud, billed on a usage pool. |
| Safe writes on a laptop | `PythonVibeGuard` + `.bak` + 2/3 length + `ast.parse`. | Same write limit. Questions refuse `patch` / `edit` / `run`. | Editor diff / confirm. No PV00x rules. Relies on you. |

## Use python-vibe when

You want a cheap offline loop on a small Python tree (≤40 files, ≤200 KB), writes limited to one folder, no cloud. Default `llama3.1:8b`. Keep 0.5B for Hub demos and CI smoke.

Pull 7B or 14B if 8B answers stay shallow. Train `python-vibe-8b` only after ~2k redacted traces.

## Use a hosted IDE agent when

The job is multi-file, another language, extra tools, a browser, or you need a precise quote from more than one call site.

Pointing an editor at Ollama via `openai_compat.py` does not make 8B into a hosted agent. It only changes the brain, not the tools.

Evening re-run of the eleven demo jobs, same 8B, against a hosted IDE agent on the same wording: [same jobs, same evening]({{ '/investigations/same-jobs/' | relative_url }}). File-job check 3 / 4. add-feature wrote the controller.

Next: [what to improve]({{ '/investigations/what-to-improve/' | relative_url }}).
