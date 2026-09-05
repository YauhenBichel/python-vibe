---
title: 0.5B sample-and-run
description: Same 18 held-out scripts on MLX. Four drafts at temperature 0.7 scored 6/18 base and 9/18 with one repair. Greedy LoRA scored 0/54. Sampling beat the adapter.
permalink: /investigations/sample-and-run/
date: 2026-09-05
type: article
---

# 0.5B sample-and-run

**Question.** On the same 18 held-out scripts, do four independent drafts
at temperature 0.7 beat one greedy draft? Does the step-100 LoRA help,
or only the loop (draw again, run, one traceback repair)?

**Answer.** The loop wins. The LoRA loses. Best cell is **untuned base
plus one repair**: **9 / 18** with four drafts. Greedy LoRA is
**0 / 54**.

Cite this note:
[Cite]({{ '/cite/' | relative_url }}).
Related:
[0.5B exact-stdout eval]({{ '/investigations/held-out-exec-eval/' | relative_url }})
· [Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }})
· [What to improve]({{ '/investigations/what-to-improve/' | relative_url }})
· [Experiments]({{ '/investigations/experiments/' | relative_url }}).

<nav class="toc" aria-label="On this page">
<p>On this page</p>
<ol>
  <li><a href="#how-this-was-scored">How this was scored</a></li>
  <li><a href="#the-two-grids">The two grids</a></li>
  <li><a href="#what-sampling-found">What sampling found</a></li>
  <li><a href="#what-failed">What failed</a></li>
  <li><a href="#estimate-of-next-steps">Estimate of next steps</a></li>
  <li><a href="#decision">Decision</a></li>
</ol>
</nav>

## How this was scored

5 September 2026. One laptop. MLX
`Qwen2.5-Coder-0.5B-Instruct-4bit`. Same 18 prompts as the Ollama
greedy note. None of those prompts are in the 45 train pairs. A run
counts only when the extracted script exits 0 and stdout matches
(trailing newline ignored).

Two MLX runs the same day:

| Run | Drafts per task | Temperature | Repeats | What it answers |
| --- | --- | --- | --- | --- |
| Four drafts | up to 4, history cleared | 0.7 | 1 | Can a different draw ship? |
| Greedy | 1 | 0 | 3 | Is that draw stable? |

Temperature is how randomly the next token is picked. It is not skill.
**0** is almost the same script every time. **0.7** is the Qwen chat
default; use it only when every draft is executed and junk is thrown
away. Four drafts at temperature 0 are four copies of one script.

The earlier Ollama greedy run (no LoRA) is a different engine:
**7 / 54** base, **12 / 54** with one repair. Rates are directional,
not a paired A/B.

The greedy MLX run also had a later loop tweak: if the last script
NameErrors on `sys` or `re`, prepend the import and rerun once, and
reject a repair whose first line is a traceback. That prepend did not
fire. Greedy drafts never NameErrored on `sys` or `re`. weekday is
`datetime`, which the prepend does not touch. Treat the two MLX grids
as the same model, not as a harness A/B.

## The two grids

<div class="stats">
  <div class="stat"><b>9 / 18</b><span>base + four drafts + repair</span></div>
  <div class="stat"><b>6 / 18</b><span>base, four drafts</span></div>
  <div class="stat"><b>2 / 18</b><span>greedy base (unique tasks)</span></div>
  <div class="stat"><b>0 / 54</b><span>greedy LoRA, with or without repair</span></div>
</div>

Four drafts, temperature 0.7, one trial. First exact-stdout win counts.

| Variant | Passed / 18 | Rate |
| --- | --- | --- |
| base | **6** | 33% |
| base + one repair | **9** | 50% |
| LoRA | **2** | 11% |
| LoRA + one repair | **6** | 33% |

Greedy, temperature 0, three repeats. Every repeat printed the same
reason for the same task.

| Variant | Unique tasks / 18 | Runs / 54 | Rate |
| --- | --- | --- | --- |
| base | **2** (clamp, fib) | 6 | 11% |
| base + one repair | **3** (+ weekday) | 9 | 17% |
| LoRA | **0** | 0 | 0% |
| LoRA + one repair | **0** | 0 | 0% |

The 6/54 and 9/54 totals matching the four-draft 6/18 and 9/18 is a
coincidence of counts, not the same score.

## What sampling found

Four drafts found a **different set**, not a superset of greedy.

Greedy base locked clamp and fib (first draft, all three repeats).
Four drafts on base found clamp, median, hhmmss, unique-order, wrap,
relpath — and missed fib. fib only passed after a repair at
temperature 0.7.

Wins that were not the first draw, base: clamp on draw 2, median on
3, unique-order on 3, wrap on 4, relpath on 2. hhmmss landed on draw
1.

base + repair added fizzbuzz on draw 4, rotate on 2, sum-even on 2
(those three were new draws, not a traceback fix) and **fib** as a
true repair. Only one of the +3 from 6 to 9 is self-debug. The rest
is “draw again.”

Greedy repair shipped **weekday** 3/3: first draft
`NameError: datetime`, second draft printed `Saturday`. That task
never passed on the four-draft grid. At temperature 0 the 0.5B can
add one import. At 0.7 it did not.

LoRA at temperature 0 is a brick. weekday printed `what day is this?`
plus `2026`. Repair added `it's not a leap year.` Clamp, fizzbuzz,
and slugify printed nothing. iso-date invented
`datetime.fromiso8601`. Repair recovered zero tasks. At 0.7 the
adapter lucked into hhmmss and palindrome, then four more with
repair (count-ext, anagram, fizzbuzz, unique-order). It still lost
clamp, median, wrap, relpath, rotate, fib, and sum-even to the
untuned base.

Five tasks never passed on any four-draft variant: weekday, slugify,
csv-col, indent4, iso-date. Greedy later cleared weekday only.

## What failed

Dominant on **base**, four drafts: used `sys.argv` and never imported
`sys`; called `main()` without defining it; printed extra words
(`Number of files ending with '.md' in .: 2` instead of `2`); parsed
`2026-09-05T17:27:00` with a space format.

Dominant on **LoRA**, four drafts: invented APIs (`list.distinct()`,
`import slugify`), `def count(sys.argv)` as a SyntaxError, empty
stdout with exit 0. Temperature 0.7 plus the style adapter widened
the broken set, not the useful one.

Dominant on **repair**: the 0.5B sometimes pasted the traceback into
the next file. A true repair that fixed a NameError was rare (fib on
base, palindrome on LoRA, weekday on greedy).

Dominant on **greedy base**: extra words (count-ext), fizzbuzz
stopped at 15, slugify echoed the raw string, rotate `c d b`,
palindrome `Yes`, sum-even `21`, indent4 left two-space padding,
csv-col `FileNotFoundError: '1'`, median `NameError: main`, iso-date
`int('05T17:27:00')`. Three copies of each.

## Estimate of next steps

Ordered by expected unique-task lift on these 18, per hour of work.
No new 0.5B train pairs. Daily `run` stays an 8B through the same
guard.

| Next | Hours | Expected lift | Why that number |
| --- | --- | --- | --- |
| Product default: base, four drafts, one repair | already the measured winner | Keeps **9 / 18** as the 0.5B stdout ceiling we have | LoRA is four tasks behind on the same sampler, and 0 / 54 greedy |
| Prepend `import sys` / `import re` on that NameError, reject a traceback-as-source | already in the later loop | **0** on this greedy grid | Those NameErrors did not appear. Ollama greedy crashed 24 / 54, often on `sys` — re-run that engine if you want a number |
| Also prepend `datetime` / `from datetime import datetime` | shipped | **+0 unique** on greedy (weekday already a repair pass); saves the repair turn | `datetime.strptime` gets `from datetime import datetime`; `datetime.date` gets `import datetime` |
| 8B writes one line from stderr, 0.5B rewrites once | next measured cell | **+3 to +6** unique if the hint names extra words, the ISO `T`, or swapped argv | Repair now also says “exited 0 but stdout is wrong” so extra words reach the 8B. Asking-a-bigger-model: spend the remote call on the stuck point, not the file |
| Eight drafts at 0.7 instead of four | one measured run | **+0 to +2** | wrap already landed on draw 4. Diminishing |
| Train the 18 prompts into the 0.5B | days, and it leaks the eval | Not a capability | The adapter already taught tone and scored 0 / 54 greedy |

Confidence is high on “do not train” and “keep four drafts.” Medium
on the 8B hint: the leftover failures are format and extra words, not
missing algorithms. Low on more samples.

What the 0.5B still will not do after that work: daily `Action:`
parse, a ≥1 KB fix, or eleven of the eighteen if the hint is weak.
Everyday-ready is still an 8B on live parse **and** a real fix.

## Decision

1. Freeze the step-100 adapters. Do not add pairs to chase weekday,
   slugify, or iso-date.
2. For 0.5B stdout smoke: **untuned base, four drafts, one repair**.
   The LoRA is style only.
3. Keep generate → run → one repair. Prefer a new draw over a second
   greedy repair.
4. The next measured hour is an 8B one-line hint on extra words /
   ISO / argv. Then stop. Daily work stays an 8B.
