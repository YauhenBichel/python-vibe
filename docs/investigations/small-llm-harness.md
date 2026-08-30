---
title: Small models, classic development
description: How a laptop 8B reaches bigger-model outcomes. The lever is a deterministic harness plus ordinary software practice, not more 0.5B training.
permalink: /investigations/small-llm-harness/
date: 2026-08-29
type: article
---

# Small models, classic development

A hosted IDE agent looks “smarter” on small Python jobs because it has
native tools and it **finishes the check**. An 8B on a laptop can close
much of that gap without becoming a bigger model. The method is old:
constrain the next step, then let a compiler-shaped oracle decide whether
the work is done.

Related: [what to improve]({{ '/investigations/what-to-improve/' | relative_url }})
· [fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }})
· [everyday skills]({{ '/investigations/everyday-skills/' | relative_url }})
· [harness comparison]({{ '/investigations/harness-comparison/' | relative_url }}).

## What transfers from classic development

These are not slogans for the model to read. They are **harness refuses**.
The 8B copies one `Action:` block. The harness is the senior engineer.

| Classic practice | Harness lever | Why a small model needs it |
| --- | --- | --- |
| Read the file that defines it before answering | the harness finds and reads that file first | 8B will grep the wrong word or answer “a tuple” |
| One concern per change | one-split design loop, `refuse_god_target` | 8B rewrites the crowded module |
| Name things so the next reader can grep them | `refuse_opaque_names`, `refuse_rename_incomplete` | 8B leaves `def calc` and says it renamed |
| A test says what it checks, and sets up its inputs before checking | `write-tests` + `refuse_weak_test` | 8B writes `assertEqual(fn(), n)` or `def test_it` |
| Tests live next to the code, not inside it | `refuse_test_in_impl` | Live 8B appended `def test_` to `src/orders.py` |
| The compiler is the oracle | `ast.parse`, undefined-name scan, unittest | Existing tests often miss the planted `NameError` |
| Do not ship on a green suite that never calls the bug | `refuse_done_oracle` | 8B ran unittest, exited 0, left `subtotl` |
| HTTP clients are stdlib, not a pipe | `refuse_shell_fetch`, PV003 | 8B will emit `curl` if the skill says “API” |
| Pin the file name you want copied | `everyday_example_path` = the skill’s `Path:` | 8B writes `weekday.py` instead of `weekday_name.py` |
| Paths work on every OS | `write-paths` + `refuse_platform_draft` | 8B writes `os.path.join` and a laptop home path |

None of this requires a larger weight. It requires the loop to **refuse
`done`** until the oracle is quiet.

## What does not transfer

A small model will not grow a browser, extra tool servers, or a 100k
context window because you add another skill essay. Those are product
gaps. Do not spend a week on them. Do not train more 0.5B steps to “learn
agency.” The 0.5B adapter is a style prior; it misses `Action:` lines.

Raising `--steps` is not a substitute for review → one-split → review, or
for “undefined name still in the file → patch that name.”

## Measured on this laptop (29 Aug 2026, evening)

`scripts/demo.py` against `demo/orders` with `llama3.1:8b`, eight steps.

| Job | Agent said done | Independent check | What the oracle should have caught |
| --- | --- | --- | --- |
| `apply_discount` return type | yes | not a file check | Shallow `"int"` — already a thin-`done` case |
| NameError in `src/orders.py` | yes | failed (`subtotl`) | Undefined name + suite never called `total_with_tax` |
| add `total_lines` + test | no (step budget) | passed | Extra `pkg/prices.py`; loop did not stop |
| tests for `apply_discount` | yes | failed | `def test_` landed in the impl file |
| rename `calc` → `multiply` | yes | failed (`x`) | Old def / broken params |
| review, do not edit | no | passed (no writes) | Limit held; no useful defect quote |
| dry-run NameError | yes | passed | Harness named the typo; no write |
| vague `clean this up` | question | passed | Ask-when-unclear, no model turn |

The pattern: **start Action is often right; finish is a lie.** Classic
development treats “the tests are green” as insufficient when the tests
do not exercise the change. The harness now does the same: an unbound
name in the file you named blocks `done`, even if `run` exited 0.

## Recipe for the next skill

1. Write one copy-paste `Action:` block. Put a real `Path:` in it.
2. Add `looks_like_*` and `everyday_example_path`, so the file the
   harness opens first is quoted in the prompt.
3. Add an oracle: `ast` / undefined names / unittest / “old def gone.”
4. Refuse `done` until the oracle is quiet.
5. Run `scripts/skill_probe.py` and `scripts/demo.py --case …` on this machine.
6. Publish the skill only if the first Action is the intended one.

That is how a small LLM works like a bigger one on a laptop tree: not by
imitating a hosted agent’s tools, but by making the loop as strict as a
careful code review.
