---
title: Everyday Python on a laptop
description: Four jobs on your own machine: ask a question, write a test, fix a bug, add one small function. No account. Only the folder you point at.
date: 2026-09-05
---

# Everyday Python on a laptop

A small helper for Python on your own computer. You type a job. It
reads and writes only inside the folder you point at. Nothing leaves
the machine unless you ask it to call a remote model.

<p class="cta">
  <a href="{{ '/start/' | relative_url }}">Install and run</a>
  <a href="{{ '/live/' | relative_url }}">See a real session</a>
  <a href="{{ '/investigations/' | relative_url }}">Read the scores</a>
  <a href="https://github.com/YauhenBichel/python-vibe" rel="noreferrer">Source on GitHub</a>
</p>

After [Start]({{ '/start/' | relative_url }}), stand in your project and
type one of these:

```bash
python-vibe brief
python-vibe ask  "what does compute_total return?"
python-vibe run  "write tests for apply_discount"
python-vibe run  "find the NameError and fix it"
python-vibe run  "add a function total_lines and a test"
```

`brief` needs no model. `ask` never writes. `run` writes, then runs the
tests. The NameError and `total_lines` jobs on `demo/orders` are done
by the helper, not the model. `run` keeps a `.bak` of anything it
edits. Point at another folder by putting it first:
`python-vibe ask ~/app "what does compute_total return?"`.

<div class="stats">
  <div class="stat"><b>Ask</b><span>A question about one file or function</span></div>
  <div class="stat"><b>Test</b><span>Cover one named function</span></div>
  <div class="stat"><b>Fix</b><span>A failing suite, one repair</span></div>
  <div class="stat"><b>Add</b><span>One small function and a test</span></div>
</div>

## Where to go

<div class="tracks">
  <div class="track">
    <h2>Use it</h2>
    <p><a href="{{ '/start/' | relative_url }}">Start</a> — install, then the four commands.</p>
    <p><a href="{{ '/scenarios/' | relative_url }}">What you type</a> — the same jobs, and what happened.</p>
    <p><a href="{{ '/live/' | relative_url }}">Live</a> — a recorded session.</p>
    <p><a href="{{ '/api/' | relative_url }}">Using</a> — every command and flag.</p>
    <p><a href="{{ '/skills/' | relative_url }}">Skills</a> — what loads for a given job.</p>
  </div>
  <div class="track">
    <h2>See the work</h2>
    <p><a href="{{ '/investigations/' | relative_url }}">Results</a> — the map of every score.</p>
    <p><a href="{{ '/investigations/which-model/' | relative_url }}">Which model</a> — keep the 8B.</p>
    <p><a href="{{ '/vscode/' | relative_url }}">VS Code</a> — Tasks: Run Task. Recorded walkthrough.</p>
    <p><a href="{{ '/architecture/' | relative_url }}">Architecture</a> — how the helper is stacked.</p>
  </div>
</div>

## What it will not do

It will not browse the web, run a general shell, or walk a large tree.
On a big project add `--scope src`. Use a hosted IDE agent when the job
spans languages, extra tools, or many files at once.
