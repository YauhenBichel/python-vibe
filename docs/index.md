---
title: Everyday Python on a laptop
description: Four jobs on your own machine: ask a question, write a test, fix a bug, add one small function. No account. Only the folder you point at.
date: 2026-08-29
---

# Everyday Python on a laptop

Four jobs, on your own machine. No account, and by default nothing you
type leaves the computer. It only changes files inside the folder you
point it at. If you choose `--engine openai` to borrow a bigger model,
the code in your prompt goes to that host; the default does not.

<p class="cta">
  <a href="{{ '/start/' | relative_url }}">Install and run</a>
  <a href="{{ '/live/' | relative_url }}">Live session</a>
  <a href="{{ '/scenarios/' | relative_url }}">What you type</a>
  <a href="https://github.com/YauhenBichel/python-vibe" rel="noreferrer">Source on GitHub</a>
</p>

After the [Start]({{ '/start/' | relative_url }}) install, stand in your
project folder and type one of these:

```bash
python-vibe brief
python-vibe ask  "what does compute_total return?"
python-vibe run  "write tests for apply_discount"
python-vibe run  "find the NameError and fix it"
python-vibe run  "add a function total_lines and a test"
```

`brief` needs no model. `ask` never writes. Daily `run` writes, then
runs the suite; a failing traceback goes back once. The NameError and
`total_lines` jobs are harness demos on `demo/orders` — no model.
`run` keeps a `.bak` of anything it edits. Point at another folder by
putting it first:
`python-vibe ask ~/app "what does compute_total return?"`.

<div class="stats">
  <div class="stat"><b>Ask</b><span>A question about one file or function</span></div>
  <div class="stat"><b>Test</b><span>Cover one named function</span></div>
  <div class="stat"><b>Fix</b><span>A failing suite, one repair</span></div>
  <div class="stat"><b>Add</b><span>One small function and a test</span></div>
</div>

## What it will not do

It will not browse the web, run a general shell, or walk a large tree.
On a big project add `--scope src`. Use a hosted IDE agent when the job
spans languages, extra tools, or many files at once.

[Start]({{ '/start/' | relative_url }}) · [Skills]({{ '/skills/' | relative_url }}) · [Experiments]({{ '/investigations/experiments/' | relative_url }}) · [Research]({{ '/investigations/' | relative_url }}) · [Architecture]({{ '/architecture/' | relative_url }})
