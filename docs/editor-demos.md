---
title: In your editor
description: Four things py-harness does from inside Cursor or VS Code, with the real answers and the time each took. Two of them need no model.
permalink: /editor-demos/
date: 2026-08-30
---

# In your editor

One command sets it up, and then py-harness answers from the chat panel
or the command palette without you leaving the file.

```bash
py-harness editors cursor       # or: vscode, zed
```

That writes `.cursor/mcp.json` and `.vscode/tasks.json` pointing at this
folder. Reload the window, enable **py-harness** under Customize → MCP,
and it is there.

Everything below is a real answer from that connection, with the time it
took. Nothing is written by hand.

## Where am I?

Open a project you have not seen before and ask for a summary.

    brief

    10 Python and Markdown files, 2.9 KB in total.
    Small enough that py-harness can read all of it, so you can
    ask about any part.

    Files:
      README.md  681 B
      src/orders.py  467 B
      ...

**Under a tenth of a second, and no model.** It counts the files, sizes
them, and tells you whether the project is small enough to ask about
freely or large enough to need a `--scope`.

## What is tangled here?

    layout

    layout: 1 finding(s), worst first.
      [cycle] src/render.py and src/report.py import each other

    Next move (do only this one): Move what they share into a new
    module both import.

Also instant, also no model. It reports import cycles, a folder with no
grouping, and a module much larger than its neighbours — and gives one
next move rather than a list, because a list gets four things changed at
once.

That cycle is real: `render.py` imports `build_report`, `report.py`
imports `render_line`.

## What does this function do?

Put the question in the chat panel while you are looking at the file.

    ask   what does apply_discount do?

    The `apply_discount` function computes the total after reducing
    it by a whole percentage, i.e. `-> int`.       (3.0s)

    ask   what does compute_total return?

    "int" — the function computes the sum of the line prices of one
    order.                                        (14.3s)

This one calls the model, so it takes seconds rather than none, and the
answer is held to saying what the function computes rather than reading
its type back.

## Changing something

    run   find a real NameError in src/orders.py and fix it

    this server is read-only. Restart it with --allow-writes, or
    run py-harness run in the terminal.

The editor connection is read-only until you say otherwise, and it says
so plainly rather than failing quietly. With `--allow-writes` the same
request repairs the misspelling and runs the tests, in about a tenth of
a second, without a model:

    bound unique NameError typo (subtotl → subtotal) in
    src/orders.py. Tests passed.

## What to reach for, and what not to

The two that need no model — `brief` and `layout` — are the ones worth
having in an editor. They answer instantly, they give the same answer
every time, and they cannot be wrong about what they found.

`ask` is good on a named function and slower.

`run` is worth it for the repairs the harness makes itself: a misspelled
name with one candidate, a missing import, a test for something already
covered. For anything the model has to reason about, read
[Experiments]({{ '/investigations/experiments/' | relative_url }}) first
— on a real repository, writing scored one in twelve.

A recorded VS Code session is on [VS Code]({{ '/vscode/' | relative_url }}).
A recorded Cursor session is on [Cursor]({{ '/cursor/' | relative_url }}).

Set-up detail for each editor: [VS Code]({{ '/vscode/' | relative_url }})
· [Cursor]({{ '/cursor/' | relative_url }})
· [local editor]({{ '/local-editor/' | relative_url }})
· [IDE plugins]({{ '/ide-plugins/' | relative_url }}).
