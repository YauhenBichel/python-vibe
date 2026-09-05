---
title: 0.5B sample-and-run
description: Same 18 held-out scripts on MLX. Four drafts scored 9/18 with one repair. A later loop scored 12/18, but zero of those twelve were a hint-repair. Greedy LoRA scored 0/54.
permalink: /investigations/sample-and-run/
date: 2026-09-05
type: article
---

# 0.5B sample-and-run

**Question.** On the same 18 held-out scripts, do four independent drafts
at temperature 0.7 beat one greedy draft? Does the step-100 LoRA help,
or only the loop (draw again, run, one traceback repair)?

**Answer.** The loop wins. The LoRA loses. Four drafts plus one
repair scored **9 / 18**. The later loop (prepend `datetime`, say
when stdout is wrong, one 8B hint) scored **12 / 18**. Zero of those
twelve were a hint-repair. Greedy LoRA is **0 / 54**.

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
  <li><a href="#the-8b-hint-cell">The 8B hint cell</a></li>
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

Three MLX runs the same day:

| Run | Drafts per task | Temperature | Repeats | What it answers |
| --- | --- | --- | --- | --- |
| Four drafts | up to 4, history cleared | 0.7 | 1 | Can a different draw ship? |
| Greedy | 1 | 0 | 3 | Is that draw stable? |
| Four drafts + later loop | up to 4, plus one 8B hint | 0.7 | 1 | Does a bigger-model note help? |

Temperature is how randomly the next token is picked. It is not skill.
**0** is almost the same script every time. **0.7** is the Qwen chat
default; use it only when every draft is executed and junk is thrown
away. Four drafts at temperature 0 are four copies of one script.

The earlier Ollama greedy run (no LoRA) is a different engine:
**7 / 54** base, **12 / 54** with one repair. Rates are directional,
not a paired A/B.

The greedy MLX run had a later loop tweak: if the last script
NameErrors on `sys` or `re`, prepend the import and rerun once, and
reject a repair whose first line is a traceback. That prepend did not
fire. Greedy drafts never NameErrored on `sys` or `re`. weekday was
still `datetime`. Treat the first two MLX grids as the same model,
not as a harness A/B. The third run added `datetime` prepend and the
8B hint.

## The two grids

<div class="stats">
  <div class="stat"><b>12 / 18</b><span>four drafts + later loop</span></div>
  <div class="stat"><b>9 / 18</b><span>base + four drafts + repair</span></div>
  <div class="stat"><b>0</b><span>hint-repairs in the 12</span></div>
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

Five tasks never passed on the first four-draft grid: weekday,
slugify, csv-col, indent4, iso-date. Greedy later cleared weekday
only. The later loop cleared weekday on the first draw (prepend
`datetime`) and also count-ext, palindrome, and csv-col. wrap
flipped off. n = 1; treat single-task flips as noise except weekday.

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

## The 8B hint cell

Same 18, four drafts, temperature 0.7, one trial, base + repair.
After a miss, `llama3.1:8b` writes one line from the traceback or
from “exited 0 but stdout is wrong,” then the 0.5B rewrites once.
The loop also prepends `from datetime import datetime` when that
NameError appears.

**12 / 18.** Zero of the twelve are a `repair pass`. Every win was
a clean first draft on some sample.

| Task | This cell | Earlier four-draft + repair |
| --- | --- | --- |
| weekday | pass @1 (prepend) | — |
| count-ext | pass @3 | — |
| palindrome | pass @3 | — |
| csv-col | pass @2 | — |
| wrap | — | @2 |
| slugify, indent4, anagram, iso-date, relpath | — | — |

The +3 versus 9 / 18 is **weekday** (mechanical prepend) plus three
sample flips in and wrap out. n = 1. The 8B note did not turn a
failing last draft into a pass. That matches
[Asking a bigger model]({{ '/investigations/asking-a-bigger-model/' | relative_url }}):
the stuck point is worth a remote call only when the local model
is already on the right file. Here the 0.5B was not.

Still down after the hint: slugify, indent4, anagram, wrap,
iso-date, relpath.

## Estimate of next steps

Ordered by expected unique-task lift on these 18, per hour of work.
No new 0.5B train pairs. Daily `run` stays an 8B through the same
guard.

| Next | Hours | Lift after measuring | Why that number |
| --- | --- | --- | --- |
| Product default: base, four drafts, one repair | already the measured winner | Holds **9 / 18** without the later loop | LoRA is four tasks behind on the same sampler, and 0 / 54 greedy |
| Prepend `sys` / `re` / `datetime`; reject a traceback-as-source | shipped | weekday is now a first pass | `datetime.strptime` gets `from datetime import datetime` |
| 8B one-line hint, then one 0.5B rewrite | measured (~11 min) | **12 / 18** headline, **0** hint-repairs | Extra words and ISO `T` still lose. Do not spend another day here |
| Eight drafts at 0.7 instead of four | one measured run | **+0 to +2** | Diminishing. wrap already flipped both ways at n = 1 |
| Train the 18 prompts into the 0.5B | days, and it leaks the eval | Not a capability | The adapter already taught tone and scored 0 / 54 greedy |
| Daily work on an 8B | already the product | Not this eval | Live parse and a real ≥1 KB fix stay the bar |

The 8B-hint estimate was +3 to +6 unique if the leftover class was
extra words. The leftover class is still extra words, ISO, and
slugify. The 0.5B does not take the note. Stop.

What the 0.5B still will not do: daily `Action:` parse, a ≥1 KB
fix, or slugify / indent4 / iso-date. Everyday-ready is still an
8B on live parse **and** a real fix.

## Decision

1. Freeze the step-100 adapters. Do not add pairs to chase slugify
   or iso-date.
2. For 0.5B stdout smoke: **untuned base, four drafts, one repair**,
   plus the `datetime` prepend. The LoRA is style only.
3. Keep generate → run → one repair. Prefer a new draw over a
   second greedy repair. Do not wait on an 8B hint to make the
   0.5B debug itself.
4. Stop spending hours on this 18-script board. Daily work stays
   an 8B. The 8B daily-jobs table on
   [Experiments]({{ '/investigations/experiments/' | relative_url }})
   is **8 / 9**.
