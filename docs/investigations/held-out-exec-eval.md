---
title: 0.5B exact-stdout eval
description: Eighteen held-out scripts, three repeats. Ollama qwen2.5-coder 0.5B scored 7/54 base and 12/54 after one traceback repair. Most runs crashed or printed extra words.
permalink: /investigations/held-out-exec-eval/
date: 2026-09-05
type: article
---

# 0.5B exact-stdout eval

**Question.** If the 0.5B writes a short script and we *run* it, how often
does stdout match? Does one traceback repair help?

**Answer.** **7 / 54** base. **12 / 54** after one repair. The 0.5B is still
not daily work. Repair is worth keeping. More style pairs are not.

Cite this note:
[Cite]({{ '/cite/' | relative_url }}).
Related:
[0.5B sample-and-run]({{ '/investigations/sample-and-run/' | relative_url }})
· [0.5B vibe review]({{ '/research-vibe-review/' | relative_url }})
· [Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }})
· [Experiments]({{ '/investigations/experiments/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#how-this-was-scored">How this was scored</a></li>
  <li><a href="#the-score">The score</a></li>
  <li><a href="#what-failed">What failed</a></li>
  <li><a href="#per-task">Per task</a></li>
  <li><a href="#decision">Decision</a></li>
</ol>
</nav>

## How this was scored

5 September 2026. One laptop. Ollama `qwen2.5-coder:0.5b` (untuned base,
not the LoRA). Eighteen prompts that are **not** in the 45 train pairs.
Each task three times. A run counts only when the extracted script exits
0 and stdout matches the expected line (trailing newline ignored).

The unit tests for the checkers all passed: every reference script scores,
junk output fails. The failures below are the **model**, not the harness
tests.

LoRA variants were not run on Ollama. The same-day MLX pair
(four drafts, then greedy, with and without the step-100 LoRA) is
[0.5B sample-and-run]({{ '/investigations/sample-and-run/' | relative_url }}).
Engines differ, so the rates are directional, not a paired A/B.

## The score

<div class="stats">
  <div class="stat"><b>7 / 54</b><span>base 0.5B</span></div>
  <div class="stat"><b>12 / 54</b><span>base + one repair</span></div>
  <div class="stat"><b>24</b><span>base crashes</span></div>
  <div class="stat"><b>23</b><span>base wrong stdout</span></div>
</div>

| Variant | Passed | Rate | Typical miss |
| --- | --- | --- | --- |
| base | **7 / 54** | 13% | crash, or extra words |
| base + one traceback repair | **12 / 54** | 22% | still extra words |

Repair lifted the total. It did not make the model reliable. Verdicts
still flip on the same prompt: fizzbuzz 2/3, hhmmss 2/3.

## What failed

Two classes, almost even on the base runs:

| Class | Base runs | What it looked like |
| --- | --- | --- |
| Nonzero exit | 24 / 54 | Often `NameError: sys is not defined` — the script used `sys.argv` and never imported `sys`. Also `TypeError` on `%`, `IndexError` on argv |
| Wrong stdout | 23 / 54 | The number was right, the line was not. `Clamped value: 10` instead of `10`. `The median is: 3` instead of `3` |
| Pass | 7 / 54 | fizzbuzz, hhmmss, and a few others, not every repeat |

Repair then failed 42 of 54: 22 wrong stdout, 20 still crashing.

The 0.5B can write a FizzBuzz. It does not print only what it was asked
to print, and it often forgets the import that its own `argv` read needs.

## Per task

Passes out of three repeats.

| Task | Base | + repair |
| --- | --- | --- |
| fizzbuzz | 2 | **3** |
| hhmmss | 2 | 2 |
| fib | 1 | 2 |
| unique-order | 0 | 2 |
| rotate | 1 | 1 |
| wrap | 1 | 1 |
| median | 0 | 1 |
| weekday | 0 | 0 |
| count-ext | 0 | 0 |
| clamp | 0 | 0 |
| slugify | 0 | 0 |
| palindrome | 0 | 0 |
| sum-even | 0 | 0 |
| csv-col | 0 | 0 |
| indent4 | 0 | 0 |
| anagram | 0 | 0 |
| iso-date | 0 | 0 |
| relpath | 0 | 0 |

Eleven of eighteen tasks never passed, even with a repair.

## Decision

Freeze the 0.5B adapters. Keep generate → run → one repair in the loop.
Daily work stays an 8B. Do not add more handwritten style pairs to chase
these eighteen scripts. The MLX follow-up put a number on that: greedy
LoRA scored 0 / 54. Four untuned drafts plus one repair scored 9 / 18.
The later loop scored 12 / 18 with zero hint-repairs.
