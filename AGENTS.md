# AGENTS.md

Guidance for humans and coding agents working in **python-vibe**.

This repo is a **0.5B LoRA + a deterministic harness** for everyday laptop
work. Treat the 0.5B model as a style prior. Treat `PythonVibeGuard` as the
safety boundary. Daily explore / edit / run uses 8B + tools.

## Commands

Harness tests need no GPU, no Ollama, and no Hugging Face token:

```bash
python3.13 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python scripts/measure/validate.py
```

`validate.py` is what CI runs: unit tests, `scripts/measure/smoke.py`, then
`scripts/measure/eval_everyday.py` (offline gate).

Live paths (optional):

```bash
PYTHONPATH=src python scripts/measure/smoke.py --live
PYTHONPATH=src python scripts/measure/smoke.py --mlx
```

## Non-negotiable

- The harness stays **deterministic**. Do not add a prompt-side router that
  skips `PythonVibeGuard`.
- Do not commit `.safetensors`, `.env`, tokens, hostnames, or adapter folders.
- Do not teach the model to discuss moles or lesions (PV004). This is a
  coding model.
- Do not add `curl | sh` examples (PV003).
- `scripts/run/serve.py` binds **127.0.0.1**. Do not change the default to `0.0.0.0`.
- Tests must not write into `scratch/` (gitignored; missing on CI). Use
  `tempfile.TemporaryDirectory`.
- Docs and GitHub Pages must not contain personal paths (`/Users/…`, `DevBox/…`).

## Layout

| Path | Role |
| --- | --- |
| `src/harness/task.py` | What the user asked for (leaf; every layer reads it) |
| `src/harness/guard/` | What ships and what is refused — the safety boundary |
| `src/harness/scan/` | Facts about a tree: brief, map, outline, house rules, layout |
| `src/harness/skillkit/` | Loads skills and repoints their paths at the target project |
| `src/harness/act/` | Intent becomes a change: parse, tools, patch recovery, jail |
| `src/harness/model/` | Talking to weights (the only non-deterministic layer) |
| `src/harness/observe/` | Traces, report, offline eval gate |
| `src/finetune/` | Specs, splits, Hub card, agent system prompt |
| `scripts/run/vibe.py` | Laptop REPL (`/run`, `--then`, `--project`) |
| `scripts/run/serve.py` | Local HTTP sidecar |
| `scripts/run/agent.py` | Everyday explore / edit / run / ship (use a **larger** Ollama model) |
| `src/harness/mcp_stdio.py` | Local MCP over stdio (editor child process, not an 8B Action) |
| `src/harness/editor_kit.py` | `python -m harness editors cursor` (MCP + tasks; `--global` merges `~/.cursor/mcp.json`) |
| `editors/` | Drop-in tasks.json, Continue yaml, MCP json |
| `src/harness/ship/` | Jailed `issue` `branch` `commit` `push` `pr` `merge` |
| `scripts/measure/batch_review.py` | One-file-at-a-time review of up to 100 files |
| `data/python-vibe/` | Short stdlib train/valid/test JSONL |
| `docs/` | Project site (GitHub Pages) + investigations |
| `tests/` | Fast unit tests (the merge gate) |

## How to change things

**Harness rule.** Add a regex in `src/harness/python_vibe.py` and **two** tests:
one string that must `block`, one near-miss that must `pass`. Bump
`RULESET_VERSION` only if the public meaning of a verdict changes.

**Training pair.** Short stdlib Python, type hints, no secrets. One pair is a
style prior, not a capability unlock. See investigation
[45 pairs vs style prior](docs/investigations/style-prior.md).

**HTTP sidecar.** Keep stdlib `http.server`. Cap POST bodies (`MAX_BODY`). New
routes need a test in `tests/interfaces/test_serve.py` that does not call Ollama.

**Skills.** `skills/*/SKILL.md` is written for the everyday 8B: one copy-paste
`Action:` block, no essays. Paths in a skill are `{{module}}` / `{{test}}` /
`{{scope}}`, or a real eval-fixture path — never an invented one. The harness
repoints anything that does not exist in the target project
(`src/harness/skill_target.py`); a literal fixture path that slips through
gets created in someone else's repo — see
[harness-comparison](docs/investigations/harness-comparison.md).
Measure with `scripts/measure/skill_probe.py` before you publish a new skill. See [everyday-skills](docs/investigations/everyday-skills.md).
The loop auto-picks skills; `Action: locate` is grep + auto-read. Do not name
third-party products.

**Agent loop.** `scripts/run/agent.py` defaults to `llama3.1:8b`. Small projects
get a file list and comfortable daily explore / edit / run. Large projects
get a harness: `Action: map`, `--scope`, truncated grep. `--tiny` / mlx 0.5B
is smoke only. Local editor: [docs/local-editor.md](./docs/local-editor.md).
Train the 7B-class tool LoRA with `scripts/run/agent.py --record data/agent-loop/extra.jsonl`,
then `scripts/weights/build_agent_data.py` and `scripts/weights/train.py --everyday`. Name it in
Ollama with `scripts/weights/export_ollama.py --create`. Do not spend more 0.5B train
steps expecting everyday-agent quality.

**Layers.** `src/harness/` is ordered bottom-up and a module may import a
layer strictly below it, never one above or beside it. `tests/whole/test_architecture.py`
is the gate: it fails on an upward import, a cycle, a `parents[N]`, or a
`guard/` module importing anything that writes. New shared predicate about
the *task*? It goes in `task.py`, not in whichever module needs it first —
that is how the last three cycles happened. See
[architecture](docs/architecture.md).

**Edit tool.** `Find:` stays exact-substring: it fails loudly instead of
editing the wrong line. A miss must come back *recoverable* — whitespace
retry, then the closest real lines. Do not add fuzzy matching that guesses
between two candidates; ambiguity is a refusal.

**Investigations.** New measurement pages go in `docs/investigations/`. Add the
file to `tests/website/test_pages.py`. Do not claim the LoRA audited a real repo.

**Site.** `docs/` is the public site (Jekyll → GitHub Pages). CSS is inlined
from `_includes/site.css` (one HTML request, no webfonts, no script). The
first `Pages` job 404s until you turn the site on in a browser: **Settings →
Pages → Build and deployment → Source → GitHub Actions**. The default Actions
token cannot create that site. Then re-run the workflow. Pages publishes from
the default branch only. Every page needs `title:` and `description:` front
matter and an entry in `sitemap.md`; `tests/website/test_pages.py` checks both.
URL: `https://yauhenbichel.github.io/python-vibe/`. `llms.txt` and
`llms-full.txt` are the map for coding agents (llms.txt v2). Name a
third-party editor only where this repo ships an integration for it, as
`editors/` does; a page must not otherwise advertise or compare products.
Do not put personal paths. Do not add analytics, webfonts, or a JS bundle.

## What not to “fix”

- Do not put an LLM-as-judge on the serve path.
- Do not run `batch_review.py --fix` on someone else’s project from CI.
- Do not treat a hundred `no issues` on 200-byte files as a review.
- Do not fuse / push GGUF unless the discussion on public fused weights agrees.

## Security

Report in a **public** GitHub issue — [SECURITY.md](./SECURITY.md).
Never paste live keys into issues, tests, or Pages.
