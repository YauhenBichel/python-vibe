---
title: The fence was the whole story
description: A hosted 32B scored 1 of 10 and looked incapable. The fault was four backticks reaching the Python parser. With them stripped it scores 9 of 10, and the local models it was being compared against do not move at all.
permalink: /investigations/the-fence/
date: 2026-09-06
type: article
---

[The instrument was broken]({{ '/investigations/measuring/' | relative_url }})
ended with a question it could not answer: a hosted 32B scored **1 of
10** on tier 3, which is not a number a 32B produces, and the reason
looked like a parser fault rather than a fact about the model.

It was a parser fault. With the fence stripped, the same model on the
same cases scores **9 of 10**.

## The measurement

Tier 3, ten runs, same two cases, same prompts. The only thing that
changed between the two columns is whether the harness takes the
markdown fence off a draft before writing it to a file.

| `Qwen2.5-Coder-32B-Instruct`, tier 3 | worked |
| --- | --- |
| before the fence was stripped | 1 of 10 |
| after | **9 of 10** |

Per case, after: `slugify` 5 of 5, `wordcount` 4 of 5. The single
failure is an ordinary one — `word_count not found in any module` —
not a broken file. Median run 15.3 seconds.

Both columns were measured *after* the missing answerer was fixed, so
the two faults do not overlap and the jump belongs to the fence alone.

## The local models do not move

This is the part worth keeping. The same fix, measured on the two local
weights the 32B was being compared against:

| `llama3.1:8b`, tier 3, twenty runs | worked |
| --- | --- |
| without the fence fix | 10 of 20 |
| with it | 10 of 20 |

Identical, which is the answer the theory predicts.

That is the control, and it is meant to show nothing. Local weights do
not wrap their code in a fence — zero of twenty recorded turns contain
one — so stripping a fence they never write cannot change what they
score. The number that moved is the number that was being corrupted.

The control is worth reading for a second reason. The same model on the
same code scored **14 of 20** in the note before this one and **10 of
20** here. Nothing changed between them but the night. Tier 3 is two
cases, and two cases cannot resolve anything smaller than the effect
measured above — which is why the fence result is believable and why a
future comparison between two models should run all fifteen.

## What kind of bug this was

Neither fault was a bug in the model, and neither was visible while only
local models were measured:

- The benchmark supplied nobody to answer a question, so a run that
  stopped to ask scored a failure. `llama3.1:8b` asks once in twenty
  runs and barely noticed. `qwen2.5-coder:7b` asks eleven times in
  twenty, and nearly doubled once somebody answered.
- The parser fed markdown to Python. Local weights happen not to fence
  their code. Every hosted chat model does.

Both have the same shape: **the harness had quietly specialised to the
one model it runs itself.** Each fault was invisible from inside that
choice and appeared the moment something else was plugged in. That is
the same class as a rule that only misfires on somebody else's
repository, and it is worth looking for more of them before the next
comparison, not after.

## What it cost, and what it bought

Two days of model comparisons produced no fact about any model. Every
per-tier number published before 6 September is unsafe, and the
[two models, one wall]({{ '/investigations/two-models/' | relative_url }})
note carries a warning saying so.

Against that: the fine-tune evaluation was going to run on this
instrument. It would have punished the trained model for asking, fed it
markdown, and reported both as capability. A wrong answer to *should we
train* is worth more than two days.

## What is still not known

Tier 3 is now saturated for the 32B, so it says nothing about the wall.
The wall is at tier 6 — `env-flag`, `venv-python`, `read-env-file`,
`retry` — where two 7–8B models stopped at the same place. Whether size
clears *that* is the open question, and it is now askable for the first
time.

## Reproducing this

```bash
HF_TOKEN=… python scripts/measure/bench.py --tier 3 --engine openai \
  --model Qwen/Qwen2.5-Coder-32B-Instruct --repeat 5
python scripts/measure/bench.py --tier 3 --model llama3.1:8b --repeat 10
python scripts/measure/bench.py --tier 3 --model qwen2.5-coder:7b --repeat 10
```

The fix is `unfenced()` in `src/harness/act/parse.py` ([#283]),
applied to `Find`, `Replace` and `Append`. Two of its behaviours exist
because mutation testing killed the first draft: anything after the
closing fence is dropped, because a model that signs off with "That
should do it." otherwise puts that sentence in the file; and the *first*
closing fence ends the code, so a reply showing a second example block
does not swallow the prose between them.

[#283]: https://github.com/YauhenBichel/py-harness/pull/283
