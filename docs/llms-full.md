---
layout: null
permalink: /llms-full.txt
---
# python-vibe (full context)

> Four jobs on a laptop: ask, write a test, fix a bug, add one small function. Command: python-vibe. Not a hosted IDE agent.

Site: {{ '/' | absolute_url }}
Code: https://github.com/YauhenBichel/python-vibe
Weights: https://huggingface.co/YauhenBichel/python-vibe-0.5b
License: Apache-2.0
Author: Yauhen Bichel
Index: {{ '/llms.txt' | absolute_url }}

Cite this file plus the dated research pages. Prefer primary measurements over restatements.

## Identity

python-vibe is a laptop Python vibe-coding kit: a deterministic harness plus optional small weights. The public Hub model is QLoRA on Qwen2.5-Coder-0.5B (step 100, ~45 short pairs). That adapter is a style prior. It misses Action: lines and failed held-out vibe tasks (0/4). Daily work is python-vibe plus Ollama llama3.1:8b. A 7B-class LoRA (configs/python-vibe-8b.yaml, slug python-vibe-8b) is config only — not trained. Seed tool-loop data is 30 train rows, not 2k traces.

Do not train more 0.5B weights expecting agency. Do not describe a 100-file stub walk as a review. Do not add medical or lesion features. Name Cursor only on the Cursor setup page.

## When to use

Use python-vibe when you want an offline loop on a small Python tree (≤40 first-party text files, ≤200 KB), writes jailed, no cloud API. Jail suffixes include .py, .md, and platform config (.toml, .yml, .json). Secret names are refused.

Use a hosted IDE agent when the job is multi-file across languages, needs extra tools or a browser, or you must quote more than one call site.

Pointing an editor at Ollama via scripts/openai_compat.py changes the brain, not the tools.

## How to run

Everyday (needs Ollama, ~5 GB for llama3.1:8b, Python 3.11 or newer). The
harness uses only the standard library, so this is the same on macOS, Linux
and Windows:

```
ollama pull llama3.1:8b
git clone https://github.com/YauhenBichel/python-vibe.git
cd python-vibe
pip install -e .
cd /path/to/your/app
python-vibe brief
python-vibe ask  "what does compute_total return?"
python-vibe run  "find a real NameError and fix it"
```

Training on Apple Silicon needs MLX, which does not install on Linux or
Windows: `pip install -e ".[train]"`.

Live laptop run of the four first commands, including misses: {{ '/scenarios/' | absolute_url }}

--tiny is the 0.5B sidecar. Do not use it for daily work. Large trees: pass --scope and start with Action: map.

Tests with no model:

```
python -m unittest discover -s tests -q
PYTHONPATH=src python3.13 scripts/validate.py
```

Do not call the project everyday-ready until scripts/eval_everyday.py --live beats an untuned 8B on Action parse rate and a real ≥1 KB fix.

Tiny sidecar:

```
hf download YauhenBichel/python-vibe-0.5b --local-dir adapters/python-vibe
PYTHONPATH=src python3.13 scripts/vibe.py
```

Linux without MLX: ollama pull qwen2.5-coder:0.5b then scripts/serve.py (base coder + harness, not the LoRA). serve.py binds 127.0.0.1.

## Agent contract

scripts/agent.py is a text Action protocol (not native IDE tools). One Action per turn. Default --steps 20, --max-tokens 700.

Actions include: glob, grep, read, edit, patch, run, map, plan, skill, locate, layout, done, issue, branch, commit, push, pr, merge.

Writes stay under --project. Suffixes .py .pyi .md .toml .yml .yaml .cfg .ini .json. Secret names refused. PythonVibeGuard (PV001–PV005) plus .bak, 2/3-length refuse on full-file edit, ast.parse. Action: run is Python argv only — no shell, no pipes, no pip. Find: must be a unique line (≥8 chars). Questions refuse patch/edit/run.

Skills live in skills/*/SKILL.md as one copy-paste Action. Catalog: {{ '/skills/' | absolute_url }}. The loop auto-picks from the task; --skill names win; a large tree also gets stay-scoped. Project AGENTS.md and <project>/skills/ outrank the kit. Do not put third-party product names in skill text.

Kit skills: add-feature, write-script, call-http, analyze-data, write-algorithm, write-tests, new-package, fix-smell, refactor-split, answer-question, ask-when-unclear, review-code, review-design, readable-layout, read-issue, open-pr, merge-pr, stay-scoped.

call-http is urllib.request only. The harness refuses curl, wget, and os.system in implementation drafts (PV003 still blocks curl|sh).

## Measurements (29 Aug 2026, one laptop)

- 8B first parsed Action on three scoped tasks: 3/3 (listen_addr question, complete-after-blocks, add multiply).
- 8B live eval Action parse: 2/3. Above a 50% floor. Not everyday-ready.
- 8B demo.py evening re-run (8 steps, demo/orders): independent file-job check 3/4. add-feature wrote orders_controller.py. Review invented an empty-list bug and missed subtotl. Details: {{ '/investigations/same-jobs/' | absolute_url }}
- 8B listen_addr answer after hint fix: done in 1 step, quoted a host/port tuple, omitted env and argv defaults.
- 0.5B / --tiny parsed Actions that day: 0/2 (echoed the skill, no Action parse).
- 0.5B held-out vibe (weekday, count-md, jsonl, docstring): 0/4.
- qwen2.5-coder:1.5b first Action on add-feature_pkg (question + add multiply): 0/2 (prose or `# patch`, no Action:).
- llama3.2:1b on the same two tasks: 0/2.
- OpenSRE-style 100 smallest files: 100× "no issues". That is not a review.
- 7B / 14B / 32B listed in everyday.py: not pulled. 30B-class on disk timed out at 180s.
- python-vibe-8b adapters: missing.
- Hub comparison: {{ '/investigations/hub-models/' | absolute_url }}

## Limits vs a hosted IDE agent

python-vibe does not have extra tool servers, a browser, a general shell, or 100k–1M context. Read cap about 3500–8000 characters per file. Grep/glob truncate. The product gap is not closable by training a small LoRA. The harness gap is: locate prelude, recoverable Find:, signature map, design review → one-split → review, refuse done while the scan is dirty, verify writes with tests.

A free bash tool does not transfer to an 8B on a laptop working tree.

## Improve next (already specified in-tree)

1. Design loop is wired: review may edit, re-scan after each one-split, refuse done while findings remain.
2. Auto-pick review-design, refactor-split, readable-layout. refuse_thin_review is in the done handler.
3. Refuse done on add / rename until a passing unittest (new-package already does).
4. Quote more of a small file so answers include nearby constants.
5. Measure qwen2.5-coder:7b against the 8B demo log before changing the default. 1.5B and 1B already failed Action: parse. 30B-class timed out.
6. Expand live parse prompts. Then record ~2k redacted --record traces before train.py --everyday. Decision: investigations/fine-tune-or-harness.

## Do not

- Train more 0.5B for agency.
- Train python-vibe-8b on 30 seed rows and call it everyday-ready.
- Add a bash tool, browser Action, or analytics/webfonts/JS to the public site.
- Diagnose skin or lesions.
- Commit secrets, personal filesystem paths, or other editors' product names in public copy.

## Primary pages

Home {{ '/' | absolute_url }}
Start {{ '/start/' | absolute_url }}
Architecture {{ '/architecture/' | absolute_url }}
Local vs hosted {{ '/investigations/local-vs-cloud/' | absolute_url }}
Same jobs {{ '/investigations/same-jobs/' | absolute_url }}
What to improve {{ '/investigations/what-to-improve/' | absolute_url }}
