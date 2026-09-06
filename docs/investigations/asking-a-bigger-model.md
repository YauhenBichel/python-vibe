---
title: Asking a bigger model, rarely
description: When the local model stops and asks a question, it is right to be stuck 3 times out of 3. That makes the question, not the failure, the moment worth spending a remote call on.
permalink: /investigations/asking-a-bigger-model/
date: 2026-08-30
type: article
---

The idea under test: when python-vibe is bad at something, let it put a
question to a larger model the user has registered, and let that happen
rarely enough that the tool is still a local tool.

The hard part is not the call. It is knowing when to make it. A model
that could tell when it was wrong would not be wrong. So the question
this page answers is whether the harness has a signal that says "stuck"
without already knowing the answer.

## What already exists

Four of the five pieces are built.

`AgentOptions.on_question` is a callback the run calls when it needs an
answer. The command line points it at the terminal when a person is
there; `None` means nobody is, and the run stops. Nothing about it
assumes the answer comes from a human.

`MAX_QUESTIONS = 2` caps how often one run may ask. The policy also
refuses a question once files have been changed: "You have already
changed files, so it is too late to ask." Rarity is not something this
feature would need to add. It is already enforced, and enforced against
the model's wishes rather than by asking it nicely.

`--engine openai` reaches any host that speaks the OpenAI shape, with a
token from the environment that is kept out of traces and errors. That
work landed in #126, along with the correction of three published claims
that stopped being true when it did.

A question is a sentence. That is what makes the economics work: the
remote model is not asked to write the code, only to settle one point,
and the local model does the work either side of it.

The missing piece is the decision to call.

## Measuring the signal

Fifteen benchmark cases, three passes, 45 runs, `llama3.1:8b` on an M3
Pro. Every run recorded why it stopped alongside whether the code it
produced actually worked.

| Stopped because | Worked | Runs | Share |
|---|---|---|---|
| done | yes | 32 | 71% |
| steps ran out | yes | 4 | 9% |
| steps ran out | no | 4 | 9% |
| asked a question | no | 3 | 7% |
| done | no | 2 | 4% |

Nine of the 45 runs failed, a fifth of them.

Read the table by the row that matters. **Every run that stopped to ask a
question had failed — three out of three.** None of them was a case where
the model asked something unnecessary and would have been fine. That is
a small number and it deserves to be called small, but it is the
behaviour the policy was built for: asking is discouraged, capped, and
refused outright after a write, so a model that asks anyway has pushed
through three separate reasons not to.

> **Correction, 6 September 2026.** That three-out-of-three could not
> have come out any other way. This benchmark supplied nobody to answer
> a question, so a run that asked one stopped there and was scored a
> failure — by construction, whatever it had asked. The row was not
> evidence about the signal; it was a description of the instrument.
>
> With an answerer in place, runs that ask succeed **3 of 7**, against
> **59 of 86** for runs that never ask. So asking is still the weaker
> outcome, and the case for treating it as a signal survives — but it is
> a 42% signal, not a 100% one, and the difference matters for a feature
> whose whole argument is that the trigger is precise. See
> [The instrument was broken]({{ '/investigations/measuring/' | relative_url }}).

Running out of steps is a much weaker signal. It fired on 18% of runs and
was wrong half the time: four of those eight runs had produced working
code and simply had not said so.

Two of the nine failures reported `done`. No stop reason can catch those.
A test oracle can, and the harness already has one.

## What that implies about the rate

Handing on only the questions fires on **7% of runs**, and on this
sample was right every time. Handing on questions and exhausted budgets
together fires on **24%** and is right 64% of the time.

Seven percent is rare. Twenty-four percent is not, and it buys its extra
reach by paying for runs that were already fine.

There is a second reason to prefer the narrow trigger. Seven of the nine
failures were tier 6 — paths, environment, configuration, retries. That
tier went from 37% to 70% on earlier work through harness fixes alone,
with the same model. Those are gaps in the tool, not gaps in the model's
knowledge, and sending them to a bigger model would hide them instead of
fixing them. A question is a knowledge gap by definition. A budget that
ran out usually is not.

So the narrow trigger is not a compromise forced by cost. It is the more
accurate one.

> **Correction, 6 September 2026.** The paragraph above is half right.
> Harness work really did move tier six from 37% to 70% without touching
> the model. But if that tier were *only* a gap in the tool, a different
> model driving the same tool would score alike. On the same four cases
> at five passes, a hosted 32B scores **18 of 20** where this default 8B
> scores **8 of 20** and `qwen2.5-coder:7b` scores 11 of 20 — the two
> local models level with each other, the larger one more than twice as
> good as either.
>
> So sending tier-six work to a bigger model would not only hide a tool
> gap. Part of that tier is a gap no further rule reaches, which makes it
> the tier where a remote call buys the most rather than the least. See
> [The wall two local models share]({{ '/investigations/the-wall/' | relative_url }}).

## What has to be built first

A question carries more than its text. `_question_from` builds the
options from the model's draft body, so a question whose text is a
harmless naming query renders with code attached:

```
text   : Which name did you mean, `caluclate_total` or `calculate_total`?
options: ('def calculate_total(rows):',
          'return sum(r.price for r in rows)',
          "API_KEY = 'sk-live-secret'")
```

Today that only reaches the terminal. It stops being a display detail the
moment a question is sent anywhere.

And nothing inspects what leaves. `guard/python_vibe.py` reviews drafts
arriving from the model — empty output, leaked keys, pipe-to-shell. It
never runs on the bytes going out, and `model/openai_generate.py` posts
its request body without any check at all.

That is issue #157, and it is a prerequisite rather than a follow-up.
The promise on the home page is that nothing typed leaves the computer by
default. A feature that sends questions out has to be able to say exactly
what it sent, the way #126 had to.

## Order of work

1. Guard what leaves (#157). Run the existing rules on outbound text
   when the endpoint is not local, cap the size, and print what was
   sent. A remote reader gets the question's text and reviewed options,
   never the raw draft.
2. Write the answerer. A registered endpoint turns a `Question` into an
   answer. Off unless registered; no silent default.
3. Give it a budget it cannot exceed and a record it cannot skip. The
   per-run cap of 2 already exists; a session cap and a trace entry for
   every call do not.
4. Measure it. `--repeat 5`, because ten of these fifteen cases change
   verdict between identical runs and a gap under about four cases is
   noise. Keep it only if it moves the number.
5. Correct the pages that stop being true.

## What would make this not worth doing

If step 4 shows no movement. Three failures is a thin base to build on,
and it is entirely possible that a bigger model, handed one sentence
without the file in front of it, answers no better than a coin. That is
a measurement, not a guess, and it comes before the feature ships rather
than after.
