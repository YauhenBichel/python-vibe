---
title: Same jobs, same evening
description: Eleven everyday tasks on demo/orders. Laptop 8B plus harness versus a hosted IDE agent on the same wording. 29 Aug 2026 evening.
permalink: /investigations/same-jobs/
date: 2026-08-29
type: article
---

# Same jobs, same evening

The same eleven tasks from `scripts/demo.py` were run on this laptop with
`llama3.1:8b` (8 steps) and then walked by a hosted IDE agent on the same
wording, against `demo/orders`. The hosted column is not a local weight.

Related: [local loop vs hosted agents]({{ '/investigations/local-vs-cloud/' | relative_url }})
· [what to improve]({{ '/investigations/what-to-improve/' | relative_url }})
· [small models, classic development]({{ '/investigations/small-llm-harness/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#what-was-measured">What was measured</a></li>
  <li><a href="#scoreboard">Scoreboard</a></li>
  <li><a href="#where-the-8b-still-loses">Where the 8B still loses</a></li>
  <li><a href="#what-the-harness-now-does">What the harness now does</a></li>
  <li><a href="#what-not-to-fix-with-weights">What not to fix with weights</a></li>
</ol>
</nav>

## What was measured

`PYTHONPATH=src python3.13 scripts/demo.py --steps 8` against a fresh copy
of `demo/orders` per case. Independent checks are the `check=` snippets in
`scripts/demo.py`, not the agent's summary. The hosted agent read the same
files and answered the same prompts in one sitting.

File jobs that have an independent check: **3 / 4 passed** on the 8B run
(bugfix, write-tests, rename). add-feature failed. Review passed the
no-write check while naming the wrong defect.

## Scoreboard

Score is “would a daily user get the same outcome,” not model size. 0–5.

| Job | 8B + harness (this run) | After the harness fix in this tree | Hosted IDE agent |
| --- | --- | --- | --- |
| `what does apply_discount return?` | 3. `done` in 1 step. Summary was `"int"`. Missed floor-division and that percent is a whole number. | 3. Type quote is already required. Formula is still a model sentence. | 5. Quoted `-> int` and `total - (total * percent) // 100`. |
| NameError in `src/orders.py` | 5. 0 model steps. `subtotl → subtotal`. Check passed. | 5 | 5. Same one-line bind. |
| add `total_lines` + test | 1. 7 actions. Wrote `src/orders_controller.py`. Claimed a test in `tests/__init__.py`. `ImportError` on `src.orders`. | 4. Module pick follows name overlap, not file size. `done` is refused until `def total_lines` exists. | 5. Function next to `compute_total`, AAA test, run. |
| write tests for `apply_discount` | 5. 0 model steps. Mechanical AAA. Check passed. | 5 | 5 |
| rename `calc` → `multiply` | 5. 0 model steps. Check passed. | 5 | 5 |
| review `src/orders.py` | 2. 6 actions, 4 refusals. Invented an empty-list bug in `compute_total`. Missed `subtotl`. No writes. | 5. Compiler findings finish the run with no model turn. | 5. Named `subtotl` on the first read. |
| dry-run NameError | 5. Would-apply note. Nothing written. | 5 | 5 |
| `clean this up` | 4. Asked. Offered the controller and `tests/__init__.py` first. | 4. Ask-when-unclear still has no ranking of likely files. | 5. Would ask, and would name `src/orders.py` first. |
| `what does render_line return?` | 3. `"str"`. | 3 | 5. Quote the signature and the format string. |

Mechanical work (unique typo, unique rename, cover-test) already matches
the hosted agent. The remaining misses are **the jobs that still need a
new function or a sentence**.

## Where the 8B still loses

**Wrong home for a new function.** `pick_module` used to sort by file size.
`orders_controller.py` is the largest file in the demo, so the skill
`Path:` and the first patch both aimed at the HTTP adapter. A hosted agent
puts `total_lines` next to `compute_total`. Size-first pick is the opposite
of the layout rules this repo already teaches.

**A review that cannot edit still tries to patch.** The named-file prelude
said `Next Action must be patch`. The write jail then refused. The 8B
spent six turns and closed on a defect that is not in the file. The hosted
agent never tried to edit.

**Answers that are only a type name.** `"int"` and `"str"` satisfy
`refuse_shallow_done` (the `->` type is present). They are not the answer
a daily user wants. Closing that gap without another refuse that rejects
a good sentence is still open.

**A lie in the summary.** add-feature reported a test in `tests/__init__.py`
and a refactor to `pkg/orders.py`. Neither file was written. Independent
check is the only score that matters.

## What the harness now does

1. **Named-file review is a compiler report.**
   `named_file_review_summary` quotes undefined names. The loop finishes
   without a generate when that report is non-empty. The prelude no longer
   asks for a patch on a review.

2. **New functions belong with related names.**
   `pick_module` scores token overlap with existing `def` lines, penalises
   `*_controller` / `*_service` adapters, and only then uses size (smaller
   first). `refuse_wrong_file` blocks a write to the adapter.
   `refuse_done_oracle` blocks `done` until `def <symbol>` exists.

Those two changes are the hosted-agent behaviour that transfers: read the
defining file, put the new function beside the ones that already share a
word, and do not accept a summary that describes work that is not there.

## What not to fix with weights

- More 0.5B train steps. The adapter still misses `Action:`.
- `train.py --everyday` on the 30 seed traces. The add-feature miss was a
  **file pick**, not a missing token.
- A bash tool or a browser Action. Neither would have put `total_lines` in
  `src/orders.py`.
- Raising `--steps` on review. The extra turns invented a second bug.

The product gap (extra tools, browser, 100k context, any language) is
still not closable. The harness gap on this demo is now the shallow
question sentence and the first `Append:` of a brand-new function.
