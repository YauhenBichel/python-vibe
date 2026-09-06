---
title: Platform engineering
description: How py-harness treats small files that must work on Windows, macOS, and Linux. Path limits, pathlib skill, and refuses an 8B cannot argue with.
permalink: /investigations/platform-engineering/
date: 2026-08-29
---

# Platform engineering

Platform work is mostly small files: a path helper, a venv layout, a
`pyproject.toml`, a workflow YAML. The failure mode is not “the file is too
big.” It is “the draft only works on the author’s laptop.”

py-harness treats that as a harness problem, not a bigger-model problem.

## What the harness already did

Every path the model is shown uses forward slashes (`Path.as_posix()`). A
Windows-style `src\app.py` is accepted as input and rewritten before the
write limit uses it. A virtual environment’s interpreter is `bin/python` on POSIX
and `Scripts/python.exe` on Windows. Those rules live in `harness/paths.py`
and are tested on every OS the suite runs on.

## What this page adds

1. **`write-paths` skill.** One copy-paste `Action: edit` of `pkg/paths.py`.
   `pathlib`, `os.name`, both venv layouts, `Path.home()`. No `os.path.join`.
   No hardcoded home paths.
2. **`write-workflow` skill.** One workflow YAML that runs the unit suite.
   Live 8B treated “add a CI workflow” as add-feature and wrote a function
   named `workflow` into `src/util.py`. The task kind is now `looks_like_ops`.
   Drafts with `curl|sh`, `0.0.0.0`, or an inline secret are refused.
3. **Limit which files may be written.** Writes may target `.py`, `.pyi`, `.md`, `.toml`,
   `.yml`, `.yaml`, `.cfg`, `.ini`, and `.json`. Secret names
   (`.env`, `credentials.json`, `.pypirc`, `secrets.json`) are refused on
   read and write. The map and grep skip them.
4. **Compiler-shaped refuses.** A draft that joins paths with `os.path`,
   hardcodes a home or `/tmp`, writes `bin/python` without the Windows
   branch, opens a text file without `encoding="utf-8"`, or calls `chmod`
   without an `os.name != "nt"` guard is not written. The next Action is
   named. The model does not get a lecture.

## Why this is the professional loop

A hosted IDE agent remembers “Windows uses backslashes” because the context
window is huge and the model is large. An 8B on a laptop does not. Classic
development for that gap is: pin the Path:, refuse the Windows-hostile
draft, keep config files under the same limit as Python.

The 0.5B LoRA is still a style prior. Do not train it on thirty path rows
and expect agency. Measure `write-paths` with `scripts/measure/skill_probe.py`
before calling it everyday-ready.

## Honest limits

It still has no free shell, no package manager, and no cloud API.
A `.sh` installer, a remote host, or a secret file is out of scope on
purpose. Large trees still need `--scope`. Public pages do not name other
editors or chat products.
