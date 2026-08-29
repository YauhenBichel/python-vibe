# I spent a day trying to make a 7B model write code. The fixes that stuck never called it.

*Notes from building a local coding harness on one laptop, with the numbers.*

---

There is a version of this story where I fine-tune a model and the graph goes
up. That is not what happened, and the reason is more useful than the graph
would have been.

I have been working on **python-vibe**, a harness around a small model running
locally through Ollama. No API key, no cloud, and a hard rule that it may only
change files inside the folder you point it at. The question I kept circling
was simple: when it gets something wrong, is that the model's fault or the
harness's?

To answer it I needed to stop guessing.

## Measuring the work, not the size of it

The first benchmark I wrote measured task size — one function, two files,
three files. It was the wrong axis. What matters is what the task *is*, so the
tiers became the jobs people actually bring:

- write a test for something that already exists
- add a small component
- fix a bug that is already in the code
- platform work: paths, environment variables, config, retries

And one rule that changed everything: **a case passes only if the code runs
and does the job.** Not if a file appeared. Not if the agent said it was
finished.

That rule immediately caught the agent lying to me. Here is a real run:

```
bug fixed correctly:  subtotl -> subtotal, total_with_tax([10]) == 12.0
what it reported:     "Added a unit test for the multiply function"
```

The work was right. The report was about something that never happened. If the
benchmark had trusted the summary, that would be a green tick.

## Then I tried to buy my way out with a bigger model

Three local models, same eleven jobs, one laptop:

| Model | Tests, components, bug fixes | Platform work |
| --- | --- | --- |
| `llama3.1:8b` | **9 / 9** | 1 / 4 |
| `qwen2.5-coder:7b` | 7 / 9 | **2 / 4** |
| `qwen3coder` (30B) | not run | **0 / 4 — every case timed out** |

The code-specialised model is better at operations work and *worse* at
everything else. The 30B never produced a usable turn; it just timed out, four
times out of four.

So there was nothing to buy. Whatever was going to improve had to come from
the harness.

## What the harness actually fixed

Nine rounds of this, each one starting from a failing run rather than an idea.
A sample of what was really going wrong:

**A fixture path in the system prompt.** The prompt contained
`Path: pkg/mathy.py` as an example. An 8B copies the first block it sees, so
it created `pkg/mathy.py` inside unrelated projects. I had already fixed this
in the skills and missed that the same literal sat one layer up.

**Three of ten turns thrown away.** I noticed every failing case used its
whole step budget, so I watched one:

```
3 patch    patch needs Find: or Append:
4 append   unknown Action append. Use glob|grep|read|...
5 patch    patch needs Find: or Append:
6 append   unknown Action append. Use glob|grep|read|...
```

The model was writing a field name on the action line with the body
underneath. Not a different intention — the same edit in a shape the parser
rejected. Each one was answered with a list of verbs and discarded.

**A test importing a function nobody had written.** This reads as perfectly
valid Python, because the import binds the name. The undefined-name check saw
nothing. It only fell over when the suite ran.

**A pronoun read as a function name.** `"...and a unit test for it"` was
parsed as *cover the function `it`*, so a request to **create** a function was
handled as a request to **test** one that already existed. It wrote the test
and never the function, four runs out of four.

**A new module hiding the standard library.** Asked for a clamp helper, it
created `pkg/math.py`. Every later `import math` in that project would find
the new file. That is an afternoon of someone's life.

## The pattern I did not expect

Sorting the results afterwards, the cases that pass *every time* have
something in common:

```
cover-discount   yes   steps=0   0.2s
cover-shout      yes   steps=0   0.2s
fix-nameerror    yes   steps=0   0.1s
```

**Zero steps.** The harness finished them without asking the model anything.

A misspelled name sitting next to the correct one. A missing import for a
module everyone knows. A test appended to a file that already has one. These
are compiler jobs. Done deterministically they cannot be got wrong, they take
a tenth of a second, and they do not vary between runs — which matters,
because everything the model touches varies a great deal between runs.

Meanwhile, everything still failing is the model reasoning badly rather than
formatting badly: a flag reader that does not treat `"0"` as false, a file
reader that returns `None`, a retry that never calls the function it was
given.

## Which is why I did not fine-tune

I nearly did. It is the obvious next move, and it was on the plan.

But fine-tuning on tool-use traces teaches a model to **emit the protocol
correctly** — and after nine rounds the harness absorbs almost every protocol
failure by itself. It fixes the field-name-as-action, adds the missing import,
refuses the wrong file, catches the name nobody defined.

The failures that remain are not protocol. Training a model to write
`Action: patch` more reliably does not teach it that `"0"` is falsey.

So the honest answer is: **record real traces from real use first, then look
at whether the failures are format or reasoning.** If they are format, train.
If they are reasoning, no amount of tool-trace training will help, and you
will have spent hours of compute finding that out.

## What I would take from this

**Check the work, not the report.** The single most valuable line in the
benchmark is the one that runs the code afterwards. An agent that says it
finished is evidence of nothing.

**Watch a failing run before fixing anything.** Every worthwhile change here
came from reading a transcript, not from having an idea about what might be
wrong. Three of ten turns being discarded was invisible in the score and
obvious in the trace.

**Prefer the fix that removes the model from the loop.** A deterministic
repair is faster, cheaper, and cannot regress. Every zero-step case is one the
model can no longer get wrong.

**A guard that blocks good code is worse than the bug it catches.** When I
made the undefined-name check stricter, it flagged sixteen files in my own
project that were perfectly correct. Calibrating against your own codebase is
a test worth writing.

**And be careful what you put in a prompt.** Every example path in a system
prompt is a path some model will eventually write to, in somebody's project.

---

*python-vibe is open source: [github.com/YauhenBichel/python-vibe](https://github.com/YauhenBichel/python-vibe).
The measurements above are reproducible with `scripts/bench.py`, and the
weights are on [Hugging Face](https://huggingface.co/YauhenBichel/python-vibe-0.5b)
— though as the table shows, they are a style prior and not the model to run
this with.*
