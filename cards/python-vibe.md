---
license: apache-2.0
base_model: Qwen/Qwen2.5-Coder-0.5B-Instruct
library_name: mlx
pipeline_tag: text-generation
tags:
  - mlx
  - lora
  - qwen2.5-coder
  - python
  - code-generation
  - coding-agent
language:
  - en
---

# python-vibe-0.5b

LoRA adapters (step 100) on Qwen2.5-Coder-0.5B-Instruct, 4-bit MLX, for short
Python drafts. Owned by [YauhenBichel](https://huggingface.co/YauhenBichel).

**These weights are a style prior, not a coding agent.** They shape how a
draft is written. They do not plan, explore a repository, or use tools well.
Read the measurements below before choosing them for anything.

The code is
[py-harness](https://github.com/YauhenBichel/py-harness) (formerly python-vibe).

## What py-harness is

A deterministic harness around a small local model. The model proposes; the
harness decides what is allowed to happen. Everything except the model call
is ordinary Python with no third-party dependencies, so the same behaviour is
reproducible and testable without a GPU, a token, or a network.

What the harness does on its own, before and around any model output:

- **Restricts writes.** Every change is resolved inside the project directory,
  is checked for syntax, and leaves a `.bak`. A rewrite that shrinks a file by
  more than a third is refused.
- **Finds the file first.** When a task names a file, that file is opened and
  the model is told to change it and no other. When it names a symbol, the
  symbol is searched for before the model's first turn.
- **Refuses the common failure.** A question that tries to edit, a repeated
  search that cannot teach it anything, an answer that repeats an instruction
  back instead of answering, a task finished with nothing changed.
- **Asks when the task is unclear.** A request that names no file and no
  function is put back to the user rather than guessed at.
- **Reports structure.** Import cycles, ungrouped packages, oversized modules
  and missing tests, worst first, with one change named.

## Which model to use

| Model | Role |
| --- | --- |
| An 8B such as `llama3.1:8b` through Ollama | Everyday explore, edit and run |
| These 0.5B adapters | Short single-file drafts, and harness smoke tests |

The 0.5B adapters are published so the harness can be demonstrated and tested
by anyone, at no cost and with no GPU. They are not the everyday model.

## Install

Works the same on macOS, Linux and Windows. The harness needs only the
standard library.

```bash
git clone https://github.com/YauhenBichel/py-harness.git
cd py-harness
pip install -e .
```

```bash
py-harness brief  ./your-project      # summary, no model
py-harness layout ./your-project      # structure report, no model
py-harness ask    ./your-project "what does compute_total return?"
py-harness run    ./your-project "add multiply(a, b) and a unit test"
```

```python
from pathlib import Path
from harness import Agent, AgentOptions

result = Agent(AgentOptions(project=Path("~/app"))).run("fix the NameError")
result.summary, result.writes, result.refusals
```

`AgentOptions(allow_writes=False)` makes a run read-only: no file is changed
and the model is told so.

## Using these adapters

```bash
hf download YauhenBichel/python-vibe-0.5b --local-dir adapters/python-vibe
```

```python
from mlx_lm import load, generate

model, tokenizer = load(
    "mlx-community/Qwen2.5-Coder-0.5B-Instruct-4bit",
    adapter_path="adapters/python-vibe",
)
```

MLX is macOS only. Elsewhere, `ollama pull qwen2.5-coder:0.5b` runs the
**base** model through the same harness, not these adapters.

`adapters.safetensors` is step 100, not the last step: a longer run overfit
after that checkpoint.

Base weights: `Qwen/Qwen2.5-Coder-0.5B-Instruct`, Apache-2.0.

## Experiments

One laptop. 29–30 August and 5 September 2026. **Not everyday-ready.**
Everyday-ready still means beating an untuned `llama3.1:8b` on live parse
**and** a real ≥1 KB fix the model wrote. Full write-up:
[Experiments](https://yauhenbichel.github.io/py-harness/investigations/experiments/).

| Experiment | Example | Result |
| --- | --- | --- |
| 0.5B as daily work | weekday helper, count-md, `Action:` | **0 / 4** vibe, **0 / 2** parse |
| 0.5B exact stdout | 18 held-out scripts, 3 repeats, Ollama | **7 / 54** base, **12 / 54** with one repair |
| 0.5B sample-and-run | same 18, MLX, four drafts then greedy | **9 / 18** then **12 / 18** with a later loop; greedy LoRA **0 / 54** |
| 8B daily jobs | write-tests, clamp, logic bug, 3 repeats | **8 / 9** |
| 8B greenfield CLI | GitHub PR CLI, empty folder, 3 repeats | **3 / 3** after #220 (suite + `done`); overflow comment **3 / 3** after #222; pagination **3 / 3** after #233; config **3 / 3** after #241 |
| Everyday-ready bar | 15 parse prompts + ≥1 KB logic fix × 3 | after #246: harness parse **9 / 15** vs clean **0 / 15**; harness fix **3 / 3** (no model turns) vs clean **3 / 3**. Zero-return cell retired as a model job. Not everyday-ready. |
| Four Start commands | `demo/orders`, `subtotl` / `stauts` | 0 / 4 then 4 / 4 |
| Which open model | same bench, code must run | 8B **6–9 / 9** over six runs; 30B timeout |
| Train more? | 35 pairs, 30 traces | No. Later ~2k clean turns |
| A real repository | 4,580 files, not a fixture | reading works; writing **1 / 12** |

These adapters are the 0.5B style prior in that table. They are not the
8B daily path. Do not remasure the retired zero-return ≥1 KB cell.

## Which model to run it with

Three local models were measured on the same eleven jobs, each checked by
running the code afterwards. One laptop, 29 August 2026, through Ollama.

| Model | Write a test, add a component, fix a bug | Platform work |
| --- | --- | --- |
| `llama3.1:8b` | **6–9 / 9** | 1 / 4 |
| `qwen2.5-coder:7b` | 7 / 9 | **2 / 4** |
| `qwen3coder` (30B) | not run | **0 / 4, every case timed out** |

A code-specialised 7B is better at operations work and worse at everything
else. A 30B does not finish a single task on this hardware. The 8B stays
the default.

The 8B row is a range because the same nine cases were run six times
against unchanged code and gave 9, 6, 8, 7, 8, 7. Over the full
fifteen-case benchmark, ten of fifteen changed verdict between identical
runs. The other rows are one run each: enough to show that the 30B never
finished, not enough to rank the two smaller models. Treat a gap under
about four cases as noise, and run any comparison of your own more than
once.

The hardware is part of the result. This was an Apple M3 Pro with 18 GB
of unified memory, shared with the operating system, so the practical
ceiling is about 11–12 GB of model rather than 18. A 14B at 9 GB clears
that on paper and still could not be measured: it put the machine into
12–13 GB of swap and no run finished.

These adapters are not in that table on purpose. They are a style prior:
they draft one short file, and they miss the `Action:` lines the loop needs.

One more measurement worth having before you try this on your own code:
on a real 4,580-file repository rather than the demo fixture, reading
works — a project summary, a structure report and a scoped question were
all correct — and writing does not. Writing tests and adding functions to
real modules scored one out of twelve across four tasks run three times
each. The same tasks pass on the fixture.

## What the harness does that the model does not

The cases that pass every time are the ones finished without asking a model
at all:

    cover-discount   steps=0   0.2s
    fix-nameerror    steps=0   0.1s

A misspelled name beside the right one, a missing import for a well-known
module, a test appended to a file that already has one — those are compiler
jobs, and doing them deterministically means they cannot be got wrong.

What still fails is reasoning, not formatting: a flag reader that does not
treat "0" as false, a retry that never calls what it was given. That is the
argument against reaching for more training first — the protocol is not
where these runs fail.

## What was measured

Scores, examples, and replay commands:
[Experiments](https://yauhenbichel.github.io/py-harness/investigations/experiments/)
· [which model](https://github.com/YauhenBichel/py-harness/blob/HEAD/docs/investigations/which-model.md)
· [research-vibe-review](https://github.com/YauhenBichel/py-harness/blob/HEAD/docs/research-vibe-review.md).

- About 45 training pairs. Validation was best near step 100, which is what
  this repository ships.
- Held-out tasks (print a weekday, count `.md` files, add a docstring) run
  through the harness, but the Python is often wrong. A style prior, not a
  reliable one.
- A real repository does not fit in the context window. Review is one small
  file at a time, roughly 200 to 2500 bytes.
- One hundred files reviewed as "no issues" is not a review. Read
  `scratch/batch-review.jsonl` before keeping any `--fix` write.

Faults found by pointing the harness at its own repository, and fixed in it:

- A fixture path in the system prompt made an 8B create `pkg/mathy.py` inside
  unrelated projects.
- A question was "answered" by pasting the instruction back; the check that
  should have caught it matched a type name inside the instruction's own
  example.
- Told to fix a named file, the model patched a different one, because the
  harness searched for a word taken from the directory path instead of
  opening the file it had been given.

Open questions:
[45 pairs vs style prior](https://github.com/YauhenBichel/py-harness/issues/9) ·
[guard evasion](https://github.com/YauhenBichel/py-harness/issues/8).
