---
title: Bench record
description: The machine, the models, and every benchmark run behind the numbers on this site. One laptop, 29–30 August 2026.
permalink: /investigations/bench-record/
date: 2026-08-30
type: article
---

# Bench record

Every number quoted elsewhere on this site comes from the runs below, on
the machine below. It is one laptop, so treat the figures as the size of
a thing rather than a rank.

Summary and conclusions: [Experiments]({{ '/investigations/experiments/' | relative_url }}).

## The machine

| | |
| --- | --- |
| Chip | Apple M3 Pro, 11 cores (5 performance, 6 efficiency), 14 GPU cores |
| Memory | **18 GB unified**, shared between macOS, the editor and the model |
| macOS | 26.5.2 |
| Runtime | Ollama 0.33.2, Python 3.13.2 |
| Storage | 44 GB free at the time of the runs |

The memory number is the one that decides what can be tried. It is
unified, so the GPU has no separate pool: a model competes with
everything else running.

## What actually fits

Weights are 4-bit (Q4_K_M) unless stated. "Fits" means the run completes
without the machine paging to disk.

| Model | On disk | Fits in 18 GB | Measured |
| --- | --- | --- | --- |
| `qwen2.5-coder:0.5b` | 0.4 GB | yes | yes |
| `qwen2.5-coder:1.5b` | 1.0 GB | yes | yes |
| `llama3.1:8b` | 4.9 GB | yes, comfortably | yes, the default |
| `qwen2.5-coder:7b` | 4.7 GB | yes, comfortably | yes |
| `qwen2.5-coder:14b` | 9.0 GB | on paper | **no — see below** |
| `qwen3-coder-30b-a3b` | 18.6 GB | no | no, times out |

The practical ceiling is not 18 GB. Weights are only part of it: the
key-value cache grows with context, and macOS and an editor want several
gigabytes. On this machine the usable budget is about **11–12 GB**.

The 14B is the interesting case because on paper it clears that. It does
not. Starting a benchmark against it put the machine into 12–13 GB of
swap and no single fifteen-case run finished in the time an 8B run takes
four times over. The failure is paging, not the model.

That was written down as a risk before the run, in the same note that
said a result under those conditions would be void. It was.

## The benchmark

`scripts/measure/bench.py`. Fifteen cases in six tiers. A case counts only if
the function runs and does the job afterwards — not if a file appeared,
and not if the agent reported success.

Six full runs of `llama3.1:8b`, same code, same machine.

| Case | What it asks for | Passed |
| --- | --- | --- |
| `double` | one small component | `YYYYYY` **6/6** |
| `initials` | one small component | `Y·Y·Y·` **3/6** |
| `largest` | one small component | `YY·Y·Y` **4/6** |
| `average` | a component and its test | `Y·YYYY` **5/6** |
| `clamp` | a component and its test | `YYYYYY` **6/6** |
| `slugify` | a new module | `·Y··Y·` **2/6** |
| `wordcount` | a new module | `Y··Y··` **2/6** |
| `cover-discount` | a test for code already there | `YYYYYY` **6/6** |
| `cover-shout` | a test for code already there | `YYYYYY` **6/6** |
| `fix-nameerror` | a bug already in the code | `YYYYYY` **6/6** |
| `fix-offbyone` | a bug already in the code | `Y·Y·Y·` **3/6** |
| `env-flag` | paths, env, config, retries | `Y·····` **1/6** |
| `read-env-file` | paths, env, config, retries | `···Y··` **1/6** |
| `retry` | paths, env, config, retries | `YYY·Y·` **4/6** |
| `venv-python` | paths, env, config, retries | `··YYY·` **3/6** |

Totals per run: **12, 8, 10, 10, 11, 7** of 15.

- Everyday work (a component, a test, a bug fix): **9, 6, 8, 7, 8, 7** of 9
- Platform work (paths, environment, config, retries): **2, 1, 2, 2, 2, 0** of 4
- Model time per run: 75–126 seconds

## What the repeats show

Five cases pass every single time: `double`, `clamp`,
`cover-discount`, `cover-shout`, `fix-nameerror`. Three of those five
finish with **no model call at all** — the harness repairs them
mechanically, in about a tenth of a second.

Ten of the fifteen changed verdict between identical runs.

So a single run cannot show a gain or a regression here. The spread on
the everyday group alone is three cases wide. Anything smaller than
about four cases is inside the noise, which is why the model comparison
below is quoted as a size and not a ranking.

## Comparing models

One run each, on the same fifteen cases. Enough to see that a model
never finished; not enough to separate two that did.

| Model | Everyday | Platform | Note |
| --- | --- | --- | --- |
| `llama3.1:8b` | 6–9 / 9 over six runs | 0–2 / 4 | the default |
| `qwen2.5-coder:7b` | 7 / 9, one run | 2 / 4 | better at ops, worse elsewhere |
| `qwen2.5-coder:14b` | not measurable | not measurable | pages to disk on 18 GB |
| 30B-class MoE | 0 / 4 | 0 / 4 | timed out, four of four |
| 1B and 1.5B | — | — | never emitted `Action:` |

## On a real repository

`demo/orders` is a fixture with two planted bugs. Everything above uses
it. This section is the same tool pointed at a working repository of
**4,580 first-party Python and Markdown files, 25 MB of source, 2.2 GB
on disk** — one nobody wrote for this benchmark.

Nothing was written inside that repository. Read-only commands ran
against it directly; every write task ran against a fresh copy of one
module in a temporary directory. Its HEAD, its dirty-file count and its
`.bak` count were identical before and after.

### Reading it

| Command | Time | Result |
| --- | --- | --- |
| `brief` | 6.4 s | Correct file counts and top-level breakdown |
| `layout` | 7.1 s | Four import cycles reported |
| `ask --scope` | 2 questions | Both answers correct against the source |

`ask` is worth quoting, because on the fixture it had been answering
with a bare type:

> `semver_to_tuple` … computes a tuple of three integers representing
> the major, minor and patch versions

### The cycles were all wrong, then all right

The four cycles `layout` first reported were **none of them real**. It
matched modules on file name, so three different `connection.py` files
collapsed into one node, and `rich.console` — a third-party package —
counted as an import of a local `console.py`.

| | Reported | Real |
| --- | --- | --- |
| Matching on file name | 4 | **0** |
| Matching on module path | 4 | **4** |

The two in first-party code are genuine mutual imports, each broken by
moving an import inside a function, and one carries a `# noqa: E402`
where somebody had already worked around it.

### Writing to it went badly

Four tasks against real modules, three runs each, every result checked
by running the code:

| Task | Verified | Summary matched reality |
| --- | --- | --- |
| `write tests for semver_to_tuple` | 0 / 3 | 2 / 3 |
| `write tests for redact_slack_token` | 0 / 3 | 3 / 3 |
| `write tests for looks_like_cancel_request` | 0 / 3 | 1 / 3 |
| `add is_newer(left, right) + a test` | 1 / 3 | 2 / 3 |

**One of twelve.** The same tasks pass on `demo/orders`, which is worth
knowing about `demo/orders`.

One run wrote a test file containing a single import line and reported
`done`. The completion check asked only whether the symbol appeared
anywhere under `tests/`, and it did — in that import. `unittest` found
no tests in the file at all.

### A guard that flagged correct code

The undefined-name check, used to decide whether a file still has an
unbound name, was run across every first-party file in that repository.

| | Files reporting an undefined name |
| --- | --- |
| Before | **3%** — every one of them correct code |
| After | **0 of 3,658** |

All of them were ordinary modern Python: names bound under
`if TYPE_CHECKING:`, imports guarded by `try/except ImportError`, PEP 695
type parameters and `type` aliases, and `match`/`case` captures.

The lesson is the one the benchmark keeps giving: a rule written from
one observed failure, applied to every file, finds things that are not
there.

## Reproducing this

```bash
ollama pull llama3.1:8b
pip install -e .
python scripts/measure/bench.py --model llama3.1:8b --repeat 5
```

`--repeat` runs every case that many times and reports a rate rather than
a verdict:

```
case              tier  passed
double            1     YYY  3/3
largest           1     YYY  3/3
initials          1     Y..  1/3

totals per pass: [3, 2, 2]  of 3
passed every pass: 2   changed verdict: 1
A gap smaller than the spread above is noise.
```

Without it the run says so, because one pass of this benchmark is a
sample and not a score.

A model too large for the machine can be reached without buying
hardware, through an OpenAI-compatible host:

```bash
export PYTHON_VIBE_BASE_URL=…  PYTHON_VIBE_API_KEY=…
python scripts/measure/bench.py --engine openai --model <a model that host serves>
```

The prompt carries the code the harness read, so point that at a host
you would show your code to. See
[cloud weights]({{ '/investigations/cloud-weights/' | relative_url }}).
