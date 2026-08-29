---
title: Everyday Python on a laptop
description: Ask questions about a Python project and let it make small fixes, on your own machine. No account, no cloud service, and it only changes files in the folder you choose.
date: 2026-08-29
---

# Everyday Python on a laptop

Ask questions about a Python project, and let it make small fixes. It runs
on your own machine: no account, no cloud service, and nothing you type
leaves your computer.

It can only change files inside the folder you point it at, it checks that
what it writes is valid Python, and it keeps a backup of anything it edits.

On a big project you give it one folder to work in, so it never tries to
read everything at once.

<p class="cta">
  <a href="{{ '/start/' | relative_url }}">Install and run</a>
  <a href="{{ '/cursor/' | relative_url }}">Add to Cursor</a>
  <a href="https://github.com/YauhenBichel/python-vibe" rel="noreferrer">Source on GitHub</a>
</p>

After the install on the [Start]({{ '/start/' | relative_url }}) page, this
is what using it looks like:

```bash
python-vibe brief ./my-project     # a summary of the project. No AI needed.
python-vibe ask   ./my-project "what does compute_total return?"
python-vibe run   ./my-project "find the NameError and fix it"
```

<div class="stats">
  <div class="stat"><b>Free</b><span>No account and no usage cost</span></div>
  <div class="stat"><b>Offline</b><span>Your code stays on your machine</span></div>
  <div class="stat"><b>5 GB</b><span>One download, then it works</span></div>
  <div class="stat"><b>3 steps</b><span>Same on macOS, Linux and Windows</span></div>
</div>

<div class="tracks">
  <section class="track">
    <h2>Everyday</h2>
    <p>Ask a question, fix a bug, add a function with a test. It finds the right file for you, may only change files inside your folder, and runs your tests afterwards. Best on a project of up to about forty of your own Python files.</p>
    <p><a href="{{ '/start/' | relative_url }}">Full install</a> · <a href="{{ '/cursor/' | relative_url }}">Add to Cursor</a> · <a href="{{ '/skills/' | relative_url }}">Skills the agent uses</a></p>
  </section>
  <section class="track">
    <h2>Tiny sidecar</h2>
    <p>A very small model published on <a href="https://huggingface.co/YauhenBichel/python-vibe-0.5b" rel="noreferrer">Hugging Face</a>, so anyone can try the checks without a large download. It writes one short file at a time and is not good enough for daily work. It exists to demonstrate and to test.</p>
    <p><a href="{{ '/research-vibe-review/' | relative_url }}">0.5B measurements</a></p>
  </section>
</div>

## When this is the right tool

Use python-vibe when you want a free, offline helper on one Python project,
and you want to be certain it cannot touch anything outside the folder you
gave it.

Use a paid, hosted assistant when the job spans several languages, needs to
browse the web, or needs to reason across a large codebase at once.

Use a hosted IDE agent when the job is multi-file across languages, needs extra tools or a browser, or you must quote more than one call site. Pointing a local editor at Ollama changes the brain, not the tools.

[Local loop vs hosted agents]({{ '/investigations/local-vs-cloud/' | relative_url }}) · [What to improve]({{ '/investigations/what-to-improve/' | relative_url }})

## Honest limits

- No general shell. `Action: run` is Python argv only.
- Writes are project text files under `--project` (Python plus a few config suffixes; no secret names), with `.bak`, a 2/3-length guard, and `ast.parse`.
- Large trees need `--scope` and `Action: map`. An 8B will not walk a hundred files.
- The 7B everyday LoRA (`python-vibe-8b`) is a config. It is not trained.
- Live parse on this kit (29 Aug 2026) is **2 / 3**. That is not everyday-ready.

## Research

- [Local loop vs hosted agents]({{ '/investigations/local-vs-cloud/' | relative_url }}) — every shipped path, same jobs
- [Same jobs, same evening]({{ '/investigations/same-jobs/' | relative_url }}) — eleven demo tasks, laptop 8B vs a hosted IDE agent
- [What to improve]({{ '/investigations/what-to-improve/' | relative_url }}) — harness work that closes a gap, and work that does not
- [Small models, classic development]({{ '/investigations/small-llm-harness/' | relative_url }}) — oracles that make an 8B finish a change
- [Fine-tune or harness]({{ '/investigations/fine-tune-or-harness/' | relative_url }}) — when new weights help, and when they do not
- [Model lanes]({{ '/investigations/model-lanes/' | relative_url }}) — which local weight for which job
- [Hub models]({{ '/investigations/hub-models/' | relative_url }}) — Hugging Face ids to run or tune; 1.5B does not parse Action:
- [Everyday laptop]({{ '/investigations/everyday-laptop/' | relative_url }}) — why 0.5B is not daily work
- [Demo]({{ '/demo/' | relative_url }}) — eleven everyday tasks on one small tree, including misses
- [Skills]({{ '/skills/' | relative_url }}) — the nineteen kit skills and when the harness loads each one
- [Platform engineering]({{ '/investigations/platform-engineering/' | relative_url }}) — pathlib, venv layouts, config files, every OS
- [Everyday skills]({{ '/investigations/everyday-skills/' | relative_url }}) — skills written for an 8B
- [Harness comparison]({{ '/investigations/harness-comparison/' | relative_url }}) — what transfers from other agent harnesses
- [Architecture]({{ '/architecture/' | relative_url }}) — layer rule
