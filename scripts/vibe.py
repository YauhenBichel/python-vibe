#!/usr/bin/env python3
"""Real-life vibe coding on this laptop: base (or LoRA) → harness → optional /run.

  PYTHONPATH=src python scripts/vibe.py
  PYTHONPATH=src python scripts/vibe.py --run "weekday name for argv YYYY-MM-DD" -- 2026-08-29

Type a task. After a draft: /run, /reset, /q.
Default MLX path is the untuned 0.5B. Pass --lora for the frozen step-100 style prior.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from finetune.models import SPECS  # noqa: E402
from harness.code import (  # noqa: E402
    apply_source,
    extract_python,
    read_project_file,
    resolve_project_file,
    write_and_run_fixed,
)
from harness.engines import any_mlx, make_hint, make_mlx, make_ollama, remember  # noqa: E402
from harness.fallbacks import PYTHON_VIBE_FALLBACK  # noqa: E402
from harness.python_vibe import PythonVibeGuard  # noqa: E402
from harness.run import complete  # noqa: E402

SCRATCH = ROOT / "scratch" / "last.py"
HELP = "commands: /open FILE  /apply  /run [args...]  /reset  /q"
_LAST_ERR = ""
_PROJECT: Path | None = None
_FILE: Path | None = None
_ORIGINAL = ""


def _mlx_generate(max_tokens: int, *, adapters: bool) -> tuple[str, Callable[[str], str]]:
    return make_mlx(SPECS["python-vibe"], max_tokens, adapters=adapters)


def _ollama_generate() -> tuple[str, Callable[[str], str]]:
    return make_ollama(SPECS["python-vibe"])


def _open_file(rel: str) -> None:
    global _FILE, _ORIGINAL
    if _PROJECT is None:
        raise SystemExit("pass --project DIR first")
    _FILE = resolve_project_file(_PROJECT, rel)
    _ORIGINAL = _FILE.read_text(encoding="utf-8") if _FILE.is_file() else ""
    print(f"open {_FILE} ({len(_ORIGINAL)} chars)", file=sys.stderr)


def _wrap_project_prompt(task: str) -> str:
    if _FILE is None:
        return task
    body = read_project_file(_FILE)
    return (
        f"Edit this project file. Task: {task}\n"
        f"Path: {_FILE.relative_to(_PROJECT) if _PROJECT else _FILE}\n"
        "Reply with the complete new file in one ```python block. "
        "Keep the rest of the file. Do not invent other files.\n\n"
        f"```python\n{body}\n```\n"
    )


def _apply() -> None:
    if _FILE is None:
        print("no file open — /open path.py first", file=sys.stderr)
        return
    if not SCRATCH.is_file():
        print("no draft to apply", file=sys.stderr)
        return
    source = SCRATCH.read_text(encoding="utf-8")
    apply_source(_FILE, source, original=_ORIGINAL)
    print(f"wrote {_FILE} (backup {_FILE.with_suffix(_FILE.suffix + '.bak')})", file=sys.stderr)


def _ask(generate_once: Callable[[str], str], prompt: str) -> bool:
    outcome = complete(generate_once, PythonVibeGuard(), PYTHON_VIBE_FALLBACK, prompt)
    draft = outcome.output or ""
    print(draft)
    print(
        json.dumps(
            {
                "verdict": outcome.verdict,
                "fallback": outcome.fallback,
                "findings": [f.rule_id for f in outcome.findings],
            }
        ),
        file=sys.stderr,
    )
    saved = False
    if draft and not outcome.fallback:
        remember(generate_once, prompt, draft)
        source = extract_python(draft)
        if source:
            SCRATCH.parent.mkdir(parents=True, exist_ok=True)
            SCRATCH.write_text(source.rstrip() + "\n", encoding="utf-8")
            print(f"saved {SCRATCH}", file=sys.stderr)
            saved = True
        else:
            print("no python block in draft — not touching scratch/last.py", file=sys.stderr)
    return saved


def _run(argv: list[str]) -> int:
    global _LAST_ERR
    if not SCRATCH.is_file():
        print("nothing to run — ask for a script first", file=sys.stderr)
        return 1
    source = SCRATCH.read_text(encoding="utf-8")
    try:
        result, fixed = write_and_run_fixed(source, SCRATCH, argv, cwd=ROOT)
    except subprocess.TimeoutExpired:
        _LAST_ERR = "timed out (12s)"
        print(_LAST_ERR, file=sys.stderr)
        return 124
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    _LAST_ERR = (result.stderr or result.stdout).strip()
    if fixed:
        print("prepended missing import and reran", file=sys.stderr)
    print(f"exit {result.code}", file=sys.stderr)
    return result.code


def _repl(generate_once: Callable[[str], str], label: str) -> None:
    print(f"python-vibe ({label})  {HELP}", flush=True)
    while True:
        try:
            line = input("vibe> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        if line in {"/q", "/quit", ":q"}:
            return
        if line == "/reset":
            getattr(generate_once, "history", []).clear()
            print("history cleared")
            continue
        if line == "/run" or line.startswith("/run "):
            extra = line.split()[1:]
            _run(extra)
            continue
        if line.startswith("/open "):
            try:
                _open_file(line.split(maxsplit=1)[1])
            except ValueError as exc:
                print(exc, file=sys.stderr)
            continue
        if line == "/apply":
            try:
                _apply()
            except ValueError as exc:
                print(exc, file=sys.stderr)
            continue
        _ask(generate_once, _wrap_project_prompt(line))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?")
    parser.add_argument(
        "--engine",
        choices=("auto", "mlx", "ollama"),
        default="auto",
        help="auto = MLX base if mlx-lm is around, else Ollama base",
    )
    parser.add_argument(
        "--lora",
        action="store_true",
        help="load the frozen step-100 style adapters (MLX only)",
    )
    parser.add_argument(
        "--hint-model",
        default="llama3.1:8b",
        help="Ollama model for a one-line --then hint (empty to skip)",
    )
    parser.add_argument("--run", action="store_true", help="generate then execute last.py")
    parser.add_argument(
        "--then",
        action="store_true",
        help="if --run fails, send the traceback back to the model and run once more",
    )
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument(
        "--project",
        type=Path,
        help="project root the model may read/write (required to edit your code)",
    )
    parser.add_argument("--file", help="open this .py file under --project")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write the last draft over --file (keeps a .bak)",
    )
    args, rest = parser.parse_known_args()
    script_args = [a for a in rest if a != "--"]
    global _PROJECT
    if args.project:
        _PROJECT = args.project.expanduser().resolve()
        if not _PROJECT.is_dir():
            sys.exit(f"not a directory: {_PROJECT}")
    if args.file:
        _open_file(args.file)

    engine = args.engine
    if engine == "auto":
        engine = "mlx" if any_mlx() else "ollama"
    label, generate_once = (
        _mlx_generate(args.max_tokens, adapters=args.lora)
        if engine == "mlx"
        else _ollama_generate()
    )
    print(f"engine {label}", file=sys.stderr)

    if args.prompt:
        prompt = args.prompt
        if args.run and _FILE is None:
            prompt += (
                " Reply with one fenced ```python block only. "
                "Call main() from `if __name__ == '__main__'` so running the file prints. "
                "Stdlib only. Read extra args from sys.argv."
            )
        saved = _ask(generate_once, _wrap_project_prompt(prompt))
        if args.apply:
            if not saved:
                raise SystemExit("no python block to apply")
            _apply()
            return
        if not args.run:
            return
        if not saved:
            raise SystemExit("no python block to run")
        code = _run(script_args)
        if code == 0 or not args.then:
            raise SystemExit(code)
        note = ""
        if args.hint_model.strip():
            hinter = make_hint(args.hint_model.strip())
            if hinter is not None:
                try:
                    note = hinter(
                        "One line: what is wrong and how to fix it. No code.\n"
                        f"```\n{_LAST_ERR[:800]}\n```"
                    ).strip()
                except (TimeoutError, RuntimeError, OSError):
                    note = ""
        repair = (
            "The script failed when I ran it. Fix it.\n"
            "Reply with one complete fenced python block.\n"
            "Do not paste the traceback. Write the fixed script only.\n"
        )
        if note:
            repair += f"Hint: {note[:400]}\n"
        repair += f"```\n{_LAST_ERR}\n```\n"
        if not _ask(generate_once, repair):
            raise SystemExit(code)
        raise SystemExit(_run(script_args))
    _repl(generate_once, label)


if __name__ == "__main__":
    main()
