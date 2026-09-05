---
title: Skills
description: Kit skills the everyday agent loads. Each one is a short copy-paste Action. The harness picks them from the task, or you pass --skill.
permalink: /skills/
date: 2026-08-29
---

# Skills

The everyday agent does not invent a plan from a long essay. It loads one or
more **skills** from `skills/*/SKILL.md`. A skill is a short copy-paste
`Action:` block written for an 8B. Paths inside a skill are rewritten to
files in *your* project before the model sees them.

Your project's `AGENTS.md` is read first and outranks the kit. A skill with
the same name in `<project>/skills/` replaces the kit copy.

See which skills a task would load, with no model:

```bash
python-vibe brief
python-vibe run --skill add-feature "add a function multiply(a, b) and a unit test"
```

Mid-loop: `Action: skill` plus `Name: write-tests`, or `Action: write-tests`
as a shortcut.

How they are written, and what failed on an 8B: [Everyday skills]({{ '/investigations/everyday-skills/' | relative_url }}).

## How the harness picks them

`--skill` names win. Otherwise the wording of the task chooses. A large tree
also gets `stay-scoped`.

| If the task looks like… | Skills loaded |
| --- | --- |
| A what / why / how question | `answer-question` |
| Merge a pull request | `merge-pr` |
| Open a PR, commit, or push | `open-pr` |
| Read a GitHub issue or pull request | `read-issue` |
| Create a package or project layout | `new-package` |
| Design or develop a GitHub CLI app | `new-package`, `write-cli-app`, `call-http`, `write-tests` |
| Rename or clean up a smell | `fix-smell` |
| Review one named file | `review-code` |
| Review structure / design / layout | `review-design`, `refactor-split`, `readable-layout` |
| Add, implement, or introduce | `add-feature`, `write-tests` |
| Script / CLI / argv | `write-script`, `write-tests` |
| HTTP API / fetch JSON / “like curl” | `call-http`, `write-tests` |
| Analytics / tally / csv | `analyze-data`, `write-tests` |
| Algorithm / binary search / stack | `write-algorithm`, `write-tests` |
| Path / venv / filesystem / platform | `write-paths`, `write-tests` |
| CI / pipeline / workflow YAML | `write-workflow` |
| Vague, no file and no symbol | `ask-when-unclear` |
| Mentions tests | `write-tests` |
| Mode is large | `stay-scoped` as well |

A question is never treated as a write. Ship skills (`read-issue`, `open-pr`,
`merge-pr`) do not force, do not target `main` / `master`, and skip secret
filenames. A harness commit keeps you as the author and adds
`Co-authored-by: python-vibe` so the [python-vibe](https://github.com/python-vibe)
GitHub user appears on that commit.

## Kit catalog

Twenty-four skills ship with python-vibe.

### Code changes

| Skill | What it tells the model to do | When it is used |
| --- | --- | --- |
| [`add-feature`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/add-feature/SKILL.md) | Add one requested function, then a test. One `Append:` patch. | Task starts with add, implement, or introduce. Not for questions or one-line bugs. |
| [`write-script`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/write-script/SKILL.md) | One argparse module in `pkg/` with `if __name__`. | Script, CLI, argv, weekday-style helpers. |
| [`write-cli-app`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/write-cli-app/SKILL.md) | One argparse GitHub PR CLI with urllib. Token from the environment. | Design or develop a CLI that talks to GitHub. Not a weekday script. |
| [`walk-files`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/walk-files/SKILL.md) | Reach every file under a folder with `rglob`: find by suffix, total the sizes. | The task says under, inside, recursively, or every file in a folder. |
| [`use-archive`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/use-archive/SKILL.md) | Pack a folder into a zip, or list what an archive holds. Standard library, no shell. | Zip, unzip, tar, archive, compress, extract. |
| [`compare-things`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/compare-things/SKILL.md) | Report what differs between two files or two dicts, and return it rather than print it. | Compare, diff, changed, missing. |
| [`call-http`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/call-http/SKILL.md) | One `urllib.request` JSON GET/POST. | HTTP API, REST, “like curl”. Never `curl\|sh`. |
| [`analyze-data`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/analyze-data/SKILL.md) | One `Counter` / group-by over rows. | Analytics, tally, csv, histogram. |
| [`write-algorithm`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/write-algorithm/SKILL.md) | One named algorithm (binary search, stack). | Data structures and algorithms. |
| [`write-paths`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/write-paths/SKILL.md) | One `pathlib` helper. Both venv layouts. `Path.home()`. | Filesystem, venv, Windows / macOS / Linux paths. |
| [`write-workflow`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/write-workflow/SKILL.md) | One workflow YAML that runs `unittest`. No curl, no `0.0.0.0`. | CI, pipeline, or workflow. Not a Python function add. |
| [`write-tests`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/write-tests/SKILL.md) | Add one test that sets up its inputs, calls the function, then checks the result. | After `add-feature`, or when the task asks for tests. |
| [`new-package`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/new-package/SKILL.md) | Create `pkg/` and `tests/`, with an `__init__.py` that only lists what the package exports. | Create a package or project structure. Not for one function on an existing module. |
| [`fix-smell`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/fix-smell/SKILL.md) | Rename one opaque function to readable snake_case. One `Find:` / `Replace:`. | Smell, rename, or clean up. Not for add or questions. |
| [`refactor-split`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/refactor-split/SKILL.md) | Move part of a file that does too much into a file of its own. | Refactor or extract. Does not rewrite the whole tree. |

### Questions and reviews

| Skill | What it tells the model to do | When it is used |
| --- | --- | --- |
| [`answer-question`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/answer-question/SKILL.md) | Answer from the file the harness already opened. One short fact. | The task is a what / why / how question. |
| [`ask-when-unclear`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/ask-when-unclear/SKILL.md) | Ask you one short question before changing anything. | No file and no symbol, or two files would both be reasonable. Not when the harness has already found the file. |
| [`review-code`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/review-code/SKILL.md) | Report defects in one file. Do not edit it. | Review, check, or find bugs. Not when the task asks for a fix. |
| [`review-design`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/review-design/SKILL.md) | Read the design scan, then one split until the scan is clean. | Review, structure, or system design of the tree. |
| [`readable-layout`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/readable-layout/SKILL.md) | Say why the project is hard to read — two files importing each other, a folder with too many files, one file much larger than the rest, or no tests — and name **one** change. | Structure, layout, layers, organise, or refactor. Not for adding one function. |

### Ship and large trees

| Skill | What it tells the model to do | When it is used |
| --- | --- | --- |
| [`read-issue`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/read-issue/SKILL.md) | `Action: issue` or `Action: pr` plus `Number: N`. The brief names files that exist here, the job, and comments from other users on the same ticket (signed-in `gh` user). | The task names an issue or pull request. |
| [`open-pr`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/open-pr/SKILL.md) | Commit, push, then open a PR (`Title:` / `Body: Closes #N`). | The task says PR, commit, or push. |
| [`merge-pr`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/merge-pr/SKILL.md) | `Action: merge` plus `Number: N`. No force. | The task says merge. |
| [`stay-scoped`](https://github.com/YauhenBichel/python-vibe/blob/HEAD/skills/stay-scoped/SKILL.md) | Stay in one folder. Do not grep the whole tree. | Mode is large, grep is truncated, or you named a folder with `--scope`. |

## What a skill is not

- Not a hosted IDE tool server. The model still emits one text `Action:` per turn.
- Not training data for the 0.5B LoRA. Do not train more 0.5B weights to “learn skills”.
- Not a place to name other editors or chat products. Skills are copy-paste blocks.

[Architecture]({{ '/architecture/' | relative_url }}) describes `skillkit/`
(catalog, target, style). [Using]({{ '/api/' | relative_url }}) shows the
`skills` field on `AgentOptions`.
