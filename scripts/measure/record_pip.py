#!/usr/bin/env python3
"""Record pip install py-harness-cli, then two no-model jobs.

  PYTHONPATH=src python3 scripts/measure/record_pip.py

Needs asciinema, agg, and network (PyPI). No Ollama.
Writes docs/media/pip-demo.cast and docs/media/pip-demo.gif.
The recorded project is a fresh copy of demo/orders under /tmp/orders.
The venv is /tmp/pv. Do not record a personal path.
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
DEMO = ROOT / "demo" / "orders"
MEDIA = ROOT / "docs" / "media"
CAST = MEDIA / "pip-demo.cast"
GIF = MEDIA / "pip-demo.gif"
WORK = Path("/tmp/orders")
VENV = Path("/tmp/pv")
WHEEL = Path("/tmp/ph-wheel")
COLS, ROWS = 80, 24
PROMPT = b"$ "

COMMANDS = (
    "python3 -m venv /tmp/pv",
    ". /tmp/pv/bin/activate",
    "pip install py-harness-cli",
    "cd /tmp/orders",
    "py-harness brief",
    'py-harness run "find the NameError and fix it"',
)


def _winsize() -> bytes:
    return struct.pack("HHHH", ROWS, COLS, 0, 0)


def _stage_wheel() -> None:
    """Install 0.3.1+ from a local wheel until that version is on PyPI."""
    if WHEEL.exists():
        shutil.rmtree(WHEEL)
    WHEEL.mkdir(parents=True)
    built = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-deps",
            "-w",
            str(WHEEL),
            str(ROOT),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if built.returncode != 0:
        sys.exit(built.stderr or built.stdout or "pip wheel failed")


def _prepare() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    shutil.copytree(DEMO, WORK, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if VENV.exists():
        shutil.rmtree(VENV)
    _stage_wheel()


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
        time.sleep(0.03)
    os.write(fd, b"\n")
    time.sleep(0.05)


def drive() -> None:
    os.chdir("/tmp")
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV", None)
    env.pop("PYTHONPATH", None)
    env["PATH"] = "/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
    env["PIP_FIND_LINKS"] = str(WHEEL)
    env["PS1"] = "$ "
    env["PROMPT_COMMAND"] = ""
    env["TERM"] = "xterm-256color"
    env["HOME"] = "/tmp"
    env["BASH_SILENCE_DEPRECATION_WARNING"] = "1"
    pid, fd = os.forkpty()
    if pid == 0:
        fcntl.ioctl(0, termios.TIOCSWINSZ, _winsize())
        os.execvpe("bash", ["bash", "--norc", "--noprofile"], env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, _winsize())
    _relay(fd, PROMPT, 5)
    for line in COMMANDS:
        _type(fd, line)
        wait = 120 if "pip" in line or "venv" in line else 60
        _relay(fd, PROMPT, wait)
    _type(fd, "exit")
    os.close(fd)
    os.waitpid(pid, 0)


def _scrub_cast(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if not lines:
        sys.exit("empty recording")
    head = json.loads(lines[0])
    head["command"] = "python3 scripts/measure/record_pip.py --drive"
    head["env"] = {"SHELL": "/bin/bash", "TERM": "xterm-256color"}
    lines[0] = json.dumps(head, ensure_ascii=False) + "\n"
    text = "".join(lines)
    if "/Users/" in text or "DevBox/" in text:
        sys.exit("recording leaked a personal path; redo with /tmp only")
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
            "python3 scripts/measure/record_pip.py --drive",
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
            "1.4",
            "--fps-cap",
            "10",
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
