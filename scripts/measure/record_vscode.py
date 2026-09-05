#!/usr/bin/env python3
"""Record the VS Code walkthrough: install tasks, then brief / ask / run.

  PYTHONPATH=src python scripts/measure/record_vscode.py

Needs asciinema, agg, and a running Ollama with llama3.1:8b (for ask).
Writes docs/media/vscode-demo.cast and docs/media/vscode-demo.gif.
The recorded project is a fresh copy of demo/orders under /tmp/vscode.

This is what Tasks: Run Task executes. The GIF is for the README and
the VS Code page. It is not a capture of the editor chrome.
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
DEMO = ROOT / "demo" / "orders"
MEDIA = ROOT / "docs" / "media"
CAST = MEDIA / "vscode-demo.cast"
GIF = MEDIA / "vscode-demo.gif"
WORK = Path("/tmp/vscode")
COLS, ROWS = 80, 24
PROMPT = b"demo $ "

COMMANDS = (
    "python-vibe editors vscode",
    "python-vibe brief",
    'python-vibe ask "what does compute_total return?"',
    'python-vibe run "find the NameError and fix it"',
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


def _relay(fd: int, needle: bytes, timeout: float) -> None:
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
        if needle in buf:
            return
    raise TimeoutError(f"waited {timeout:.0f}s for {needle!r}")


def _type(fd: int, line: str) -> None:
    for char in line:
        os.write(fd, char.encode())
        time.sleep(0.035)
    os.write(fd, b"\n")
    time.sleep(0.05)


def drive() -> None:
    """Sit in /tmp/vscode and type the four commands into bash."""
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
    _relay(fd, PROMPT, 5)
    for line in COMMANDS:
        _type(fd, line)
        _relay(fd, PROMPT, 90)
    _type(fd, "exit")
    os.close(fd)
    os.waitpid(pid, 0)


def _scrub_cast(path: Path) -> None:
    """Drop host paths from metadata. The session itself stays /tmp/vscode."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines:
        sys.exit("empty recording")
    head = json.loads(lines[0])
    head["command"] = "python3 scripts/measure/record_vscode.py --drive"
    head["env"] = {"SHELL": "/bin/bash", "TERM": "xterm-256color"}
    lines[0] = json.dumps(head, ensure_ascii=False) + "\n"
    text = "".join(lines)
    if "/Users/" in text or "DevBox/" in text:
        sys.exit("recording leaked a personal path; redo with /tmp/vscode only")
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
            "python3 scripts/measure/record_vscode.py --drive",
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
