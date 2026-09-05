# python-vibe

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](./LICENSE)
[![CI](https://github.com/YauhenBichel/python-vibe/actions/workflows/ci.yml/badge.svg)](https://github.com/YauhenBichel/python-vibe/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/badge/docs-GitHub%20Pages-2F6FED)](https://yauhenbichel.github.io/python-vibe/)
[![Pages](https://github.com/YauhenBichel/python-vibe/actions/workflows/pages.yml/badge.svg)](https://yauhenbichel.github.io/python-vibe/)
[![Contributors](https://img.shields.io/github/contributors/YauhenBichel/python-vibe)](https://github.com/YauhenBichel/python-vibe#contributors)

Four jobs on a laptop: **ask**, **write a test**, **fix a bug**, **add one
small function**. Runs on your machine. Only touches the folder you point
at. Site: [yauhenbichel.github.io/python-vibe](https://yauhenbichel.github.io/python-vibe/).

Daily work is `python-vibe` plus Ollama `llama3.1:8b`. The public 0.5B LoRA
is a style prior, not the everyday path.
Weights: [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b).

Join: [good first issue](https://github.com/YauhenBichel/python-vibe/labels/good%20first%20issue) ·
[Discussions](https://github.com/YauhenBichel/python-vibe/discussions) ·
[Contributors](#contributors). You do
not need a GPU to run tests.

Contributing: [CONTRIBUTING.md](./CONTRIBUTING.md) · security: [SECURITY.md](./SECURITY.md).
Vulnerabilities: open a **public** GitHub issue. Do not paste live keys.

## Use it

From your project folder, after `pip install -e .` and `ollama pull llama3.1:8b`:

```bash
python-vibe brief
python-vibe ask  "what does compute_total return?"
python-vibe run  "write tests for apply_discount"
python-vibe run  "find the NameError and fix it"
python-vibe run  "add a function total_lines and a test"
```

`python-vibe` with no arguments reprints that list. Daily `run` writes,
then runs the suite and sends a failing traceback back once.
`find the NameError` and `add a function total_lines` are harness demos
on `demo/orders` (unique typo and a template add, no model).
Point at another folder by putting it first:
`python-vibe ask ~/app "what does add return?"`.

```python
from harness import Agent, AgentOptions

result = Agent(AgentOptions(project=Path("~/app"))).run("fix the NameError")
result.summary, result.writes
```

Full settings: [docs/api.md](./docs/api.md). Layers: [docs/architecture.md](./docs/architecture.md).
Site: [Start](https://yauhenbichel.github.io/python-vibe/start/).
A typed session on `demo/orders` (5 Sep 2026): [Live demo](https://yauhenbichel.github.io/python-vibe/live/).
What those commands did on one laptop: [Scenarios](https://yauhenbichel.github.io/python-vibe/scenarios/).
Every measured run: [Experiments](https://yauhenbichel.github.io/python-vibe/investigations/experiments/).

## Live demo

5 September 2026. Fresh copy of `demo/orders`. Only `ask` called
`llama3.1:8b`. The two writes are harness demos (no model). This is a
real asciinema recording, not a mock. Daily `run` is 8B: write, run the
suite, send a failing traceback back once.

![python-vibe on demo/orders](docs/media/live-demo.gif)

```
$ python-vibe brief
10 Python and Markdown files, 2.9 KB in total.

$ python-vibe ask "what does compute_total return?"
"int", which computes the sum of the line prices of one order.

$ python-vibe run "find the NameError and fix it"
bound unique NameError typo (subtotl → subtotal) in src/orders.py. Tests passed.

$ python-vibe run "add a function total_lines and a test"
added def total_lines(prices) in src/orders.py. Tests passed.
```

Replay: `asciinema play docs/media/live-demo.cast`.
A same-day **daily** `run` (8B, logic bug, suite after the write):
`docs/media/daily-run.gif`. Replay:
`asciinema play docs/media/daily-run.cast`.
Full page: [Live demo](https://yauhenbichel.github.io/python-vibe/live/).

## Experiments

I tried a small open LLM for daily Python: ask, write a test, fix a bug,
add one function. One laptop. 29–30 August 2026. **Not everyday-ready.**

| Experiment | Example | Result |
| --- | --- | --- |
| 0.5B as daily work | weekday helper, count-md, `Action:` | **0 / 4** vibe, **0 / 2** parse |
| Four Start commands | `demo/orders`, `subtotl` / `stauts` | **0 / 4**, then **4 / 4** after the harness |
| Which open model | same bench, code must run | 8B **6–9 / 9** over six runs; 7B coder 7 / 9 once; 30B timeout |
| Train more? | 35 pairs, 30 traces | No. Later ~2k clean turns |
| Larger model on a GPU | `--engine openai` | No live 14B / 32B number yet |
| Does a 14B fit? | 9 GB of weights, 18 GB machine | **No.** 12–13 GB of swap, no run finished |
| On a real repository | 4,580 files, not `demo/orders` | reading works; writing **1 / 12** |

The four commands as typed, first night vs after the harness:

| I typed | First night | After the harness |
| --- | --- | --- |
| `ask "what does compute_total return?"` | `"int"` | Type plus what it computes |
| `run "write tests for apply_discount"` | Dead test below `if __name__` | Already covered. Nothing written |
| `run "find the NameError and fix it"` | Three files edited | `subtotl` → `subtotal`. No model |
| `run "add a function total_lines and a test"` | Opened a file. Suite red | `total_lines(prices)` + test. No model |

Live first-Action parse (`eval_everyday.py --live`, `llama3.1:8b`):
**8 / 15**, one run. Everyday-ready still means beating an untuned 8B on
parse **and** a real ≥1 KB fix.

Reproduce any of it with `python scripts/measure/bench.py --repeat 5`, which
reports a pass rate per case instead of a single verdict.

Read those as a rough size, not a rank. The nine-case group was run six
times against unchanged code and gave 9, 6, 8, 7, 8, 7; over the full
fifteen-case bench ten of fifteen changed verdict between identical
runs. A gap smaller than about four cases is noise.

Five cases pass every single time — `double`, `clamp`, `cover-discount`,
`cover-shout`, `fix-nameerror` — and three of those five finish with **no
model call at all**. That is why they hold still.

### The machine

Apple M3 Pro, 11 cores, **18 GB unified memory**, macOS 26.5.2, Ollama
0.33.2. Unified memory means the model competes with everything else
running, so the practical ceiling is about **11–12 GB of model**, not 18.

| Model | On disk | Usable here |
| --- | --- | --- |
| `llama3.1:8b` | 4.9 GB | yes, the default |
| `qwen2.5-coder:7b` | 4.7 GB | yes |
| `qwen2.5-coder:14b` | 9.0 GB | no — pages to disk |
| 30B-class MoE | 18.6 GB | no — times out |

The 14B is the one worth knowing about: it clears 18 GB on paper and
still does not run, because weights are only part of the budget. If you
are choosing hardware for this, buy memory, and reckon on roughly double
the model size you want to run.

Tables with the planted example:
[Experiments](https://yauhenbichel.github.io/python-vibe/investigations/experiments/)
· [Scenarios](https://yauhenbichel.github.io/python-vibe/scenarios/).
The machine, what fits in it, and all six runs case by case:
[Bench record](https://yauhenbichel.github.io/python-vibe/investigations/bench-record/).
Thread: [discussion #128](https://github.com/YauhenBichel/python-vibe/discussions/128).

## Everyday agent

**Small** (≤40 first-party text files, ≤200 KB): the agent gets a file list.
Writes are limited to Python plus a few config suffixes (`.toml`, `.yml`, `.json`);
secret names are refused.

**Large**: stay in one folder.

```bash
python-vibe brief
python-vibe ask --scope src "what does apply_source refuse?"
python-vibe run --scope src "write tests for apply_discount"
```

Writes stay under `--project` and go through `PythonVibeGuard` + `.bak`.
One action per turn: `map` · `plan` · `skill` · `glob` · `grep` · `read` ·
`edit` · `patch` · `run` · `done`.

`map` returns a signature outline, not just sizes. A `Find:` that misses by
whitespace is retried and re-indented; one that misses outright comes back
with the closest real lines. A repeated read-only action is refused once.
Your project's own `AGENTS.md` is read first and outranks the kit skills.
Why each of those: [harness-comparison](./docs/investigations/harness-comparison.md).

Best-practice skills live in `skills/`. The agent preloads them when the
task says “add” / “test” / “path” / “venv” / “create a package” / “rename” / “issue” / “PR”,
or you pass `--skill`. `Action: skill` + `Name:` loads one mid-loop. Ship
actions (`issue`, `branch`, `commit`, `push`, `pr`, `merge`) are limited:
no force, not `main`/`master`, no secret filenames. Full catalog and when
each one loads: [Skills](https://yauhenbichel.github.io/python-vibe/skills/).

```bash
python-vibe run --skill add-feature "add a function multiply(a, b) and a unit test"
```

Point an OpenAI-compatible editor at the same 8B: [docs/local-editor.md](./docs/local-editor.md).

```bash
PYTHONPATH=src python3.13 scripts/measure/eval_everyday.py
PYTHONPATH=src python3.13 scripts/measure/eval_everyday.py --live
```

Do not call this everyday-ready until `--live` beats an untuned 8B on parse
rate and a real ≥1 KB fix. Notes:
[docs/investigations/everyday-laptop.md](./docs/investigations/everyday-laptop.md) ·
[docs/research-vibe-review.md](./docs/research-vibe-review.md) ·
[docs/investigations/local-vs-cloud.md](./docs/investigations/local-vs-cloud.md) ·
[docs/investigations/what-to-improve.md](./docs/investigations/what-to-improve.md).

## Tiny sidecar (0.5B)

Anyone can pull the adapters (no Hugging Face login) and start the harnessed REPL.
This track drafts **one small file**. It does not walk a repo.

```bash
git clone https://github.com/YauhenBichel/python-vibe.git
cd python-vibe
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
hf download YauhenBichel/python-vibe-0.5b --local-dir adapters/python-vibe
PYTHONPATH=src python3.13 scripts/run/vibe.py
```

`vibe.py` also downloads that Hub repo itself if `adapters/python-vibe` is empty.
Linux / Windows without MLX: `ollama pull qwen2.5-coder:0.5b` then
`PYTHONPATH=src python3.13 scripts/run/serve.py` (base coder + harness, not the LoRA).

```
client → harness :8080 → ollama qwen2.5-coder:0.5b
              ↓
     pass / revise / block
     block twice → fixed fallback
```

The harness blocks empty drafts, leaked keys, `curl|sh`, and lesion diagnosis
(wrong surface). It does not rewrite style.

### Interactive `/run`

Every draft goes through `PythonVibeGuard`. `/run` executes the last Python
block in `scratch/last.py`.

```
vibe> print the weekday for a YYYY-MM-DD date from argv
vibe> /run 2026-08-29
vibe> also accept --short for Mon
vibe> /run 2026-08-29 --short
```

```bash
PYTHONPATH=src python3.13 scripts/run/vibe.py --run --then \
  "print the weekday for argv YYYY-MM-DD" -- 2026-08-29
```

`--then` sends the traceback back once if `/run` fails. `--engine ollama`
uses the pulled `qwen2.5-coder:0.5b` base instead of the LoRA.

### One file in your project

```bash
PYTHONPATH=src python3.13 scripts/run/vibe.py --project /path/to/your/app
```

```
vibe> /open src/app.py
vibe> add a docstring to the main function and keep the rest
vibe> /apply
```

```bash
PYTHONPATH=src python3.13 scripts/run/vibe.py \
  --project /path/to/your/app \
  --file src/app.py \
  --apply \
  "add type hints to main(); do not change behaviour"
```

### Review up to 100 files (still one file per call)

`batch_review.py` loads the LoRA once and walks the smallest first-party `.py`
files (skips `.venv`). Review first. `--fix` rewrites only when the review is
not `no issues`, keeps a `.bak`, and refuses a tiny overwrite.

```bash
PYTHONPATH=src python3.13 scripts/measure/batch_review.py \
  --project /path/to/your/app \
  --limit 100
```

Report: `scratch/batch-review.jsonl`. Read it before you keep any `--fix` write.

## Train (Mac / MLX 3.13)

Tiny style prior:

```bash
PYTHONPATH=src python3.13 scripts/weights/build_data.py
PYTHONPATH=src python3.13 scripts/weights/train.py
```

Everyday tool loop (7B-class, after you have traces):

```bash
python-vibe run "find a real NameError and fix it"
PYTHONPATH=src python3.13 scripts/weights/build_agent_data.py
PYTHONPATH=src python3.13 scripts/weights/train.py --everyday
```

Turns land in `.python-vibe/traces.jsonl` unless you pass `--no-record`.
That folder is gitignored. `--record path.jsonl` writes somewhere else.
Do not commit live paths or keys.

## Test

Harness tests require Python 3.11 or newer and need no GPU or Ollama. On macOS
and Linux:

```bash
PYTHONPATH=src python -m unittest discover -s tests -q
PYTHONPATH=src python scripts/measure/validate.py
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -q
python scripts/measure/validate.py
```

On Windows Command Prompt:

```batch
set PYTHONPATH=src
python -m unittest discover -s tests -q
python scripts/measure/validate.py
```

On Linux, everyday agent use runs through Ollama rather than MLX:

```bash
ollama pull llama3.1:8b
PYTHONPATH=src python scripts/run/agent.py --project /path/to/your/app --brief
```

For the tiny sidecar on those platforms, use the base coder model:

```bash
ollama pull qwen2.5-coder:0.5b
PYTHONPATH=src python scripts/run/serve.py
```

Training the LoRA itself requires Apple Silicon, MLX, and Python 3.13. See
[discussion #14](https://github.com/YauhenBichel/python-vibe/discussions/14) for
the open discussion about training without MLX.

Live Ollama (base 0.5B through `PythonVibeGuard`):

```bash
ollama pull qwen2.5-coder:0.5b
PYTHONPATH=src python3.13 scripts/measure/smoke.py --live
```

LoRA on Mac (MLX, Python 3.13). `--best` uses
`adapters/python-vibe/0000100_adapters.safetensors` when that checkpoint is
present.

```bash
PYTHONPATH=src python3.13 scripts/measure/smoke.py --mlx
```

## Serve (tiny sidecar)

```bash
ollama pull qwen2.5-coder:0.5b
PYTHONPATH=src python3.13 scripts/run/serve.py
```

```bash
curl -s localhost:8080/health
curl -s localhost:8080/v1/python-vibe \
  -H 'content-type: application/json' \
  -d '{"prompt":"jsonl reader that skips bad lines"}'
```

Binds **127.0.0.1**. Do not change the default to `0.0.0.0`.

## Hugging Face

Public adapters: [YauhenBichel/python-vibe-0.5b](https://huggingface.co/YauhenBichel/python-vibe-0.5b)
(`adapters.safetensors` is the step-100 checkpoint).

```bash
hf download YauhenBichel/python-vibe-0.5b --local-dir adapters/python-vibe
PYTHONPATH=src python3.13 scripts/weights/pull_hf.py python-vibe
```

To publish a new train (needs `hf auth login` and write access to **your**
namespace — set `HF_USER` / `HF_REPO`, never implied as the official account):

```bash
PYTHONPATH=src python3.13 scripts/weights/push_hf.py python-vibe --what adapters --public
```

---

## Contributors

Thank you to everyone who has helped python-vibe.

<!-- readme: contributors,bots/- -start -->
<table>
	<tbody>
		<tr>
			<td align="center">
				<a href="https://github.com/YauhenBichel">
					<img src="https://avatars.githubusercontent.com/YauhenBichel?s=48" width="48" alt="Yauhen Bichel" />
					<br />
					<sub><b>Yauhen Bichel</b></sub>
				</a>
			</td>
			<td align="center">
				<a href="https://github.com/xianjianlf2">
					<img src="https://avatars.githubusercontent.com/xianjianlf2?s=48" width="48" alt="Mark Xian" />
					<br />
					<sub><b>Mark Xian</b></sub>
				</a>
			</td>
			<td align="center">
				<a href="https://github.com/ItzSaurav">
					<img src="https://avatars.githubusercontent.com/ItzSaurav?s=48" width="48" alt="Itzsaurav" />
					<br />
					<sub><b>Itzsaurav</b></sub>
				</a>
			</td>
			<td align="center">
				<a href="https://github.com/svkzn">
					<img src="https://avatars.githubusercontent.com/svkzn?s=48" width="48" alt="svkzn" />
					<br />
					<sub><b>svkzn</b></sub>
				</a>
			</td>
			<td align="center">
				<a href="https://github.com/Aditya-233">
					<img src="https://avatars.githubusercontent.com/Aditya-233?s=48" width="48" alt="Aditya" />
					<br />
					<sub><b>Aditya</b></sub>
				</a>
			</td>
			<td align="center">
				<a href="https://github.com/kkkhs">
					<img src="https://avatars.githubusercontent.com/kkkhs?s=48" width="48" alt="Huangshuo Kuang" />
					<br />
					<sub><b>Huangshuo Kuang</b></sub>
				</a>
			</td>
		</tr>
	</tbody>
</table>
<!-- readme: contributors,bots/- -end -->

The list is filled by [Contributors](./.github/workflows/contributors.yml) from GitHub commits (bots omitted). [Contributor graph](https://github.com/YauhenBichel/python-vibe/graphs/contributors) · [good first issue](https://github.com/YauhenBichel/python-vibe/labels/good%20first%20issue)
