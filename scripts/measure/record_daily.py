#!/usr/bin/env python3
"""Record one real 8B daily run: fix compute_total on a logic bug.

  PYTHONPATH=src python scripts/measure/record_daily.py

Needs asciinema, agg, and Ollama llama3.1:8b.
Writes docs/media/daily-run.cast and docs/media/daily-run.gif.
The recorded project is a fresh copy of eval/fixtures/daily_logic under /tmp/daily.
"""

from __future__ import annotations

import fcntl
import json
import os
import select
import shutil
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
DEMO = ROOT / "eval" / "fixtures" / "daily_logic"
MEDIA = ROOT / "docs" / "media"
CAST = MEDIA / "daily-run.cast"
GIF = MEDIA / "daily-run.gif"
WORK = Path("/tmp/daily")
COLS, ROWS = 80, 24
PROMPT = b"demo $ "

COMMANDS = (
    'python-vibe run "fix compute_total in src/app.py so it sums the rows"',
)


def _winsize() -> bytes:
    return struct.pack("HHHH", ROWS, COLS, 0, 0)


def _prepare() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(DEMO, WORK, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    bin_dir = WORK / ".bin"
    bin_dir.mkdir()
    shim = bin_dir / "python-vibe"
    shim.write_text(
        "#!/bin/sh\n"
        f'export PYTHONPATH="{SRC}"\n'
        f'exec "{sys.executable}" -m harness "$@"\n',
        encoding="utf-8",
    )
    shim.chmod(0o755)


def _relay(fd: int, needles: tuple[bytes, ...], timeout: float) -> bytes:
    buf = b""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.15)
        if not ready:
            continue
        chunk = os.read(fd, 8192)
        if not chunk:
            break
        os.write(1, chunk)
        buf += chunk
        for needle in needles:
            if needle in buf:
                return needle
    raise TimeoutError(f"waited {timeout:.0f}s for {needles!r}")


def _type(fd: int, line: str) -> None:
    for char in line:
        os.write(fd, char.encode())
        time.sleep(0.035)
    os.write(fd, b"\n")
    time.sleep(0.05)


def drive() -> None:
    os.chdir(WORK)
    env = os.environ.copy()
    env["PATH"] = f"{WORK / '.bin'}:{env.get('PATH', '')}"
    env["PS1"] = "demo $ "
    env["PROMPT_COMMAND"] = ""
    env["TERM"] = "xterm-256color"
    env["HOME"] = str(WORK)
    env["BASH_SILENCE_DEPRECATION_WARNING"] = "1"
    pid, fd = os.forkpty()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, _winsize())
        os.execvpe("bash", ["bash", "--norc", "--noprofile"], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, _winsize())
    _relay(fd, (PROMPT,), 5)
    for line in COMMANDS:
        _type(fd, line)
        seen = _relay(fd, (PROMPT, b"\n> "), 180)
        if seen == b"\n> ":
            _type(fd, "fix the existing function")
            _relay(fd, (PROMPT,), 180)
    _type(fd, "exit")
    os.close(fd)
    os.waitpid(pid, 0)


def _scrub_cast(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines:
        sys.exit("empty recording")
    head = json.loads(lines[0])
    head["command"] = "python3 scripts/measure/record_daily.py --drive"
    head["env"] = {"SHELL": "/bin/bash", "TERM": "xterm-256color"}
    lines[0] = json.dumps(head, ensure_ascii=False) + "\n"
    text = "".join(lines)
    if "/Users/" in text or "DevBox/" in text:
        sys.exit("recording leaked a personal path; redo with /tmp/daily only")
    path.write_text(text, encoding="utf-8")


def record() -> None:
    _prepare()
    MEDIA.mkdir(parents=True, exist_ok=True)
    rec = subprocess.run(
        [
            "asciinema",
            "rec",
            "--overwrite",
            "--headless",
            "--return",
            "-f",
            "asciicast-v2",
            "--window-size",
            f"{COLS}x{ROWS}",
            "--idle-time-limit",
            "2",
            "--command",
            "python3 scripts/measure/record_daily.py --drive",
            str(CAST),
        ],
        cwd=str(ROOT),
        check=False,
    )
    if rec.returncode != 0:
        sys.exit(f"asciinema rec failed ({rec.returncode})")
    _scrub_cast(CAST)
    render = subprocess.run(
        [
            "agg",
            "--theme",
            "github-light",
            "--font-size",
            "14",
            "--cols",
            str(COLS),
            "--rows",
            str(ROWS),
            "--idle-time-limit",
            "1.2",
            "--speed",
            "1.15",
            "--fps-cap",
            "12",
            "--last-frame-duration",
            "4",
            str(CAST),
            str(GIF),
        ],
        check=False,
    )
    if render.returncode != 0:
        sys.exit(f"agg failed ({render.returncode})")
    print(f"wrote {CAST} ({CAST.stat().st_size} B)", file=sys.stderr)
    print(f"wrote {GIF} ({GIF.stat().st_size} B)", file=sys.stderr)


def main() -> None:
    if "--drive" in sys.argv:
        drive()
        return
    record()


if __name__ == "__main__":
    main()
