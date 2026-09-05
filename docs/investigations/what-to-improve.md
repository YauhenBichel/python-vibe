---
title: What to improve
description: Harness work that can close a gap with a hosted agent, and work that cannot. Do not train more 0.5B for agency.
permalink: /investigations/what-to-improve/
date: 2026-09-05
type: article
---

# What to improve

The product gap is not closable. The harness gap is.

A hosted IDE agent has native tools, extra servers, a browser, and a large context window. python-vibe is a local loop: twenty typed Actions, a write limit, twenty steps, 700 tokens, project text files only (Python plus a few config suffixes; no secrets). Improving this project means making the **8B loop reliable on small Python and platform trees** — not growing a browser Action or pretending 8B is a frontier model.

Related: [local loop vs hosted agents]({{ '/investigations/local-vs-cloud/' | relative_url }}) · [harness comparison]({{ '/investigations/harness-comparison/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#what-to-copy-what-to-refuse">What to copy, what to refuse</a></li>
  <li><a href="#closest-score-on-the-same-jobs">Closest score on the same jobs</a></li>
  <li><a href="#work-already-in-the-tree">Work already in the tree</a></li>
  <li><a href="#05b-stdout-estimated">0.5B stdout, estimated</a></li>
  <li><a href="#what-not-to-spend-a-week-on">What not to spend a week on</a></li>
  <li><a href="#two-success-bars">Two success bars</a></li>
</ol>
</nav>

## What to copy, what to refuse

Published harness notes in this repo already said the quiet part: **edit format and context assembly** move small-model pass rates. A free shell tool does not transfer to an 8B on a laptop working tree.

| Hosted-agent behavior | Copy into python-vibe? | Local lever | Status (29 Aug 2026) |
| --- | --- | --- | --- |
| Read the defining file before answering | Yes | `prelude()` locate + refuse a shallow `done` (must quote the `->` type) | Wired. Files under 12 KB are read whole so nearby constants stay in the quote. |
| Patch one function, then add a test, then run | Yes, scoped — not a stranger’s full suite | `pick_skills` + write-tests inject + refuse `done` before a passing run | Wired for add-feature, new-package, bugfix, refactor, and a design-loop write. |
| Review structure, then one split, then review again | Yes | Design scan + refuse `done` while findings remain | Wired. Prelude allows a one-split edit. After each write the harness re-scans. `done` is refused while findings remain. |
| Show a repo map of signatures | Yes | `Action: map` (120-line outline) | Wired. Large trees still need `--scope`. |
| Recover a near-miss edit | Yes | `Find:` whitespace retry + closest-line hint | Wired. Keep exact `Find:` (fails loud). Do not add fuzzy patches. |
| Extra tools, browser, any language, 100k–1M context | No | None. The write limit and step budget stay. | Out of scope on purpose. `openai_compat.py` does not add these. |
| Free-form terminal | No | Typed `run` only (no `-c`, pip, pipes) | Correct for an 8B on a laptop tree. |
| Train the brain to emit the protocol | Later, after traces | `train.py --everyday` on ~2k redacted `--record` turns | 30 train rows + 40 seed templates. No `python-vibe-8b` adapters. |

## Closest score on the same jobs

Score is “would a daily user get the same outcome,” not model size. 0–5. “After harness” is the recommended local work, not a new weight.

| Job | 8B + harness today | After recommended harness | Hosted IDE agent |
| --- | --- | --- | --- |
| Typed question | 3 | 3 | 5 |
| Add a function + test | 1 (wrong file, 29 Aug evening) | 4 (name-overlap pick + refuse `done` until `def` exists) | 5 |
| Rename / smell | 5 | 5 | 5 |
| Named-file review | 2 (invented a defect) | 5 (compiler findings, no model turn) | 5 |
| One-split refactor | 2 | 3 | 5 |
| 100-file review | 1 | 2 | 5 |
| Extra tools / browser / any language | 0 | 0 | 5 |

## Work already in the tree

Ship these before training another model.

1. **Design loop.** Wired. After each one-split edit the harness re-scans. `done` is refused while findings remain. Review tasks may edit. Live 8B still aims at the god module; `refuse_god_target` now blocks that path before the draft runs.
2. **Auto-pick** `review-design`, `refactor-split`, and `readable-layout`. Thin-review refuse is in the `done` handler.
3. **Verify writes.** Add / bug / rename / refactor / a design-loop write: inject tests or `run`. `done` is refused until a passing unittest.
4. **Deeper small-file reads.** Files under 12 KB are read whole. Larger files still truncate at 3500 characters plus a tail.
5. **Measure bigger local models.** 29 Aug 2026, this laptop: 8B first Action was `done` on `complete` (thin summary), `patch` on add-multiply (tests file first, not impl), `read` on a dirty design review (skills were auto-picked; prelude asked for `edit`). The on-disk 30B coder timed out at the 180s Ollama cap. 7B coder is not pulled. Default stays 8B.
6. **Raise the live parse floor.** `eval/action_prompts.jsonl` has ten rows. Live 8B parse is 7/10. Everyday-ready still means beating an untuned 8B on parse **and** a real ≥1 KB fix.
7. **AAA tests.** `write-tests` now requires `test_<unit>_<result>` and `got = …`. One-line `assertEqual(fn(), n)` is refused.
8. **Editor drop-in.** `python -m harness editors vscode|continue|cursor` copies tasks / Continue / local MCP. `serve` speaks `/v1/chat/completions`. Hosted-editor chat override of loopback is out of scope (no public tunnel).
9. **Everyday laptop Python.** Skills `write-script`, `call-http`, `analyze-data`, `write-algorithm`. Prelude now quotes the skill `Path:` (`pkg/weekday_name.py`, not `pkg/<noun>.py`). Drafts that emit `curl` / `wget` / `os.system` are refused.
10. **Compiler oracle.** Undefined-name scan (`scan/names.py`). `done` is refused if a bugfix file still has `subtotl`. Tests in an impl file are refused. A rename that still defines the old name is refused. See [small models, classic development]({{ '/investigations/small-llm-harness/' | relative_url }}).
11. **Platform paths.** Skill `write-paths`. The limit includes `.toml` / `.yml` / `.json`. Drafts that use `os.path.join`, a hardcoded home or `/tmp`, or a POSIX-only venv path are refused. See [platform engineering]({{ '/investigations/platform-engineering/' | relative_url }}).
12. **Traces, then a 7B LoRA.** Only after a live design loop reaches no structure findings. `--record` into `data/agent-loop/extra.jsonl` (gitignored). Thirty seed rows are not enough. Decision write-up: [fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}).
13. **Named-file review quotes the compiler.** Wired. `review src/orders.py` no longer asks for a patch, then refuses it. Undefined names finish the run with no generate. Measured: [same jobs, same evening]({{ '/investigations/same-jobs/' | relative_url }}).
14. **New functions stay with related names.** Wired. `pick_module` no longer prefers the largest file (that was the controller). Prelude pins `Path:`. After the def exists the harness writes the AAA test. `done` is refused until `def <symbol>` exists. A second `orders.py` is refused.

## 0.5B stdout, estimated

The 18-script MLX pair is
[0.5B sample-and-run]({{ '/investigations/sample-and-run/' | relative_url }}).
Four drafts plus one repair is **9 / 18**. Greedy LoRA is **0 / 54**.
Hours and expected unique-task lift on those 18:

| Next | Hours | Expected lift |
| --- | --- | --- |
| Keep base, four drafts, one repair as the 0.5B stdout default | 0 | Holds 9 / 18 |
| Prepend `sys` / `re` on that NameError; reject a traceback-as-source | already in the later loop | 0 on the greedy MLX grid (those NameErrors did not appear) |
| Prepend `datetime` the same way | shipped | 0 unique (weekday already a repair pass) |
| 8B one-line hint from stderr, then one 0.5B rewrite | next measured cell | +3 to +6 if the leftover class is extra words / ISO `T` / argv |
| Eight drafts instead of four | one measured run | +0 to +2 |
| Train the 18 prompts into the 0.5B | days, and it leaks the eval | Not a capability |

Daily `run` stays an 8B. Do not spend the week on more 0.5B pairs.

## What not to spend a week on

- More 0.5B train steps. The adapter is a style prior. Held-out vibe tasks failed. It misses `Action:` lines. Greedy LoRA scored 0 / 54 on the 18-script exec eval.
- Training `python-vibe-8b` on the thirty seed rows and calling it everyday-ready.
- A bash tool, a browser Action, or extra-tool bridges. Those make the laptop write limit weaker and do not move the measured jobs.
- Raising `--steps` as a substitute for a review → one-split → review loop.

## Two success bars

| Bar | python-vibe (local) | Hosted IDE agent |
| --- | --- | --- |
| Ready for daily use | Small Python tree. First Action correct on Q&A / add / rename / one-split. Writes limited to one folder. Offline. | Any repo, any language, extra tools, browser. Precise multi-site quotes. You pay a usage pool. |
| How you know | `skill_probe.py` shows the intended Action with prelude on; live eval beats the 8B baseline; a design loop reaches “no structure findings” without rewriting the tree. | Already there. Pointing an editor at Ollama does not move this bar. |
