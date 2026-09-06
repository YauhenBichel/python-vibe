---
title: The instrument was broken
description: A day spent comparing models found two faults in the benchmark instead. It punished asking a question, and it fed markdown fences to the Python parser. Every model number published before this is unsafe.
permalink: /investigations/measuring/
date: 2026-09-06
type: article
---

The question was whether a bigger model breaks the wall that two 7–8B
models hit at the same place. Answering it needed comparisons, and the
comparisons found faults in the thing doing the comparing.

Both faults were invisible while only local models were measured. Both
would have made a fine-tune evaluation wrong.

## A 14B does not run here

`qwen2.5-coder:14b` is 9 GB and pulled. It timed out on every case,
three of three, which confirms the earlier record rather than
overturning it: 9 GB of weights plus a growing key-value cache does not
fit in 18 GB beside everything else. The local ceiling is 7–8B, and the
two best candidates for that size have both been measured.

## The benchmark punished asking a question

A run that stops to ask needs somebody to answer. The benchmark supplied
nobody, so the question ended the run and scored a failure. How often a
model asks turns out to vary enormously:

| Tier 3, ten passes | Runs ended by asking |
| --- | --- |
| `llama3.1:8b` | 1 of 20 |
| `qwen2.5-coder:7b` | **11 of 20** |
| `Qwen2.5-Coder-32B` | **5 of 10** |

So the benchmark was measuring willingness to act without asking, and
reporting it as capability.

The answer now given is deliberately empty: *use the most likely
reading, say which you chose, and continue*. Answering properly would
hand over the thing each case checks. A question costs a turn, which is
what it costs a person who is not watching closely.

| Tier 3, ten passes | Nobody answering | Answered |
| --- | --- | --- |
| `llama3.1:8b` | 13 of 20 | **14 of 20** |
| `qwen2.5-coder:7b` | 7 of 20 | **13 of 20** |

The second model nearly doubled. The gap between those two was published
here as a difference in capability and was mostly this.

## The benchmark fed markdown to the Python parser

With that fixed, the hosted 32B still scored one of ten, which is not a
number a 32B produces. Watching one run turn by turn showed why. It
writes drafts like this:

```
Action: patch
Path: src/orders.py
Append:
```python
def slugify(text: str) -> str:
    return text.lower()
```
```

The fence goes through unchanged, so what reaches the file is:

```
'```python'
'def slugify(text: str) -> str:'
'    return text.lower()'
'```'
-> SyntaxError: invalid syntax
```

By its third turn the model was reporting an unterminated string literal
in a test file — reading back the wreckage of its own earlier write.
Nine of ten runs then spent the whole step budget and produced nothing
that would load.

Local models happen not to fence their code. Every hosted chat model
does. So the harness has a fault that only appears the moment it is
pointed at a model it does not run itself, which is the same class of
thing as a rule that only fires on somebody else's repository.

## What this costs

Every model comparison published before today is unsafe. The local one
was distorted by the missing answerer; the remote one measured a parser
fault. Whether size breaks the wall is still unanswered, and the credits
spent bought the discovery of the second fault rather than the answer.

That is the better outcome of the two available. An instrument that
punishes asking and mangles fenced code would have made the fine-tune
evaluation wrong in the same two ways, and that evaluation was going to
be the basis for weeks of work.

## What happened next

The fence is stripped where a draft is parsed, and the three models were
re-run on the same cases. The 32B went from 1 of 10 to **9 of 10**, and
the local models did not move — written up in
[The fence was the whole story]({{ '/investigations/the-fence/' | relative_url }}).

So neither of the two days of comparisons said anything about model
size. Tier 3 is now saturated for the 32B; the wall is at tier 6, and
that is the measurement still to make.

## Reproducing this

```bash
python scripts/measure/bench.py --tier 3 --repeat 10
python scripts/measure/bench.py --tier 3 --model qwen2.5-coder:7b --repeat 10
HF_TOKEN=… python scripts/measure/bench.py --tier 3 --engine openai \
  --model Qwen/Qwen2.5-Coder-32B-Instruct --repeat 5
```

Each row now records how often the run asked, so the effect above can be
seen rather than inferred.
