"""Copy drop-in editor settings into a project. No model."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from harness.paths import REPO_ROOT

KINDS = ("vscode", "continue", "cursor", "zed")


def kit_dir() -> Path:
    packaged = Path(__file__).resolve().parent / "kit_editors"
    if packaged.is_dir():
        return packaged
    return REPO_ROOT / "editors"


def looks_like_vibe_checkout(project: Path) -> bool:
    return (project / "src" / "harness" / "cli.py").is_file()


def install_editors(
    project: Path,
    kind: str,
    *,
    allow_writes: bool = False,
    user_wide: bool = False,
) -> list[Path]:
    """Write the drop-in files for `kind`. Returns written paths."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    if user_wide and kind != "cursor":
        raise ValueError("--global is only for kind cursor")
    root = project.expanduser().resolve()
    if not user_wide:
        root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    if kind == "vscode":
        dest = root / ".vscode" / "tasks.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_merge_vscode_tasks(dest), encoding="utf-8")
        written.append(dest)
        return written
    if kind == "continue":
        dest = root / ".continue" / "config.yaml"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(
            (kit_dir() / "vscode" / "continue.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        written.append(dest)
        return written
    if kind == "zed":
        dest = root / ".zed" / "settings.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_zed_settings(root, dest), encoding="utf-8")
        written.append(dest)
        return written
    mcp_root = Path.home() if user_wide else root
    dest = mcp_root / ".cursor" / "mcp.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        _merge_mcp(
            dest,
            _cursor_server(
                root, allow_writes=allow_writes, user_wide=user_wide
            ),
        ),
        encoding="utf-8",
    )
    written.append(dest)
    if not user_wide:
        tasks = root / ".vscode" / "tasks.json"
        tasks.parent.mkdir(parents=True, exist_ok=True)
        tasks.write_text(_merge_vscode_tasks(tasks), encoding="utf-8")
        written.append(tasks)
    return written


def next_steps(kind: str, *, allow_writes: bool = False, user_wide: bool = False) -> str:
    """What a person does after the files are written. Printed by the CLI."""
    if kind != "cursor":
        return (
            "Reload the window, then Command Palette → Tasks: Run Task → "
            "py-harness: ask"
        )
    writes = (
        "read-write"
        if allow_writes
        else "read-only — re-run with --allow-writes to edit files"
    )
    where = "every workspace (~/.cursor/mcp.json)" if user_wide else "this folder"
    return (
        f"py-harness is set up for {where} ({writes}).\n"
        "1. ollama pull llama3.1:8b\n"
        "2. Command Palette → Developer: Reload Window\n"
        "3. Open Customize → MCP → enable py-harness\n"
        "4. In chat: ask py-harness what compute_total returns\n"
        "   or Tasks: Run Task → py-harness: ask\n"
        "Do not point Override OpenAI Base URL at 127.0.0.1. "
        "That request often leaves this machine."
    )


def _vscode_tasks() -> dict:
    """Task file that runs whichever interpreter has py-harness installed.

    The tasks used to call a bare `py-harness`. An editor runs a task in a
    plain shell, and that command is only there if the install put it on
    PATH, which a virtual environment or a --user install often does not.
    Naming the interpreter directly works in every case.
    """
    template = json.loads(
        (kit_dir() / "vscode" / "tasks.json").read_text(encoding="utf-8")
    )
    runner = f'"{Path(sys.executable).as_posix()}" -m harness'
    env = None if _harness_is_importable() else {
        "PYTHONPATH": (REPO_ROOT / "src").as_posix()
    }
    for task in template["tasks"]:
        task["command"] = task["command"].replace("__RUNNER__", runner)
        if env:
            task["options"] = {"env": env}
    return template


def _merge_vscode_tasks(dest: Path) -> str:
    incoming = _vscode_tasks()
    if not dest.is_file():
        return json.dumps(incoming, indent=2) + "\n"
    try:
        data = json.loads(dest.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    labels = {task.get("label") for task in incoming.get("tasks", [])}
    kept = [
        task
        for task in data.get("tasks", [])
        if isinstance(task, dict) and task.get("label") not in labels
    ]
    data["version"] = incoming.get("version", data.get("version", "2.0.0"))
    data["tasks"] = kept + incoming["tasks"]
    incoming_inputs = incoming.get("inputs", [])
    incoming_ids = {item.get("id") for item in incoming_inputs}
    kept_inputs = [
        item
        for item in data.get("inputs", [])
        if isinstance(item, dict) and item.get("id") not in incoming_ids
    ]
    if incoming_inputs or kept_inputs:
        data["inputs"] = kept_inputs + incoming_inputs
    return json.dumps(data, indent=2) + "\n"


def _harness_is_importable() -> bool:
    """True when a bare interpreter can `import harness` with no help.

    An editor starts the server as a plain subprocess, without whatever
    PYTHONPATH the person had set when they generated the file.
    """
    probe = subprocess.run(
        [sys.executable, "-c", "import harness"],
        capture_output=True,
        env={"PATH": os.environ.get("PATH", "")},
        check=False,
    )
    return probe.returncode == 0


def _stdio_server(project: Path) -> dict:
    """Command an editor will spawn. Absolute interpreter + project."""
    server = {
        "command": Path(sys.executable).as_posix(),
        "args": ["-m", "harness", "mcp", "--project", project.as_posix()],
    }
    if not _harness_is_importable():
        server["env"] = {"PYTHONPATH": (REPO_ROOT / "src").as_posix()}
    return server


def _cursor_server(
    project: Path, *, allow_writes: bool, user_wide: bool = False
) -> dict:
    """Portable Cursor MCP. Uses ${workspaceFolder} so the file can be shared.

    Cursor interpolates that variable to the folder the person has open.
    An absolute --project would bake in one machine and one folder.
    """
    args = ["-m", "harness", "mcp", "--project", "${workspaceFolder}"]
    if allow_writes:
        args.append("--allow-writes")
    server: dict = {
        "type": "stdio",
        "command": _cursor_command(project, user_wide=user_wide),
        "args": args,
    }
    env = _cursor_env(project, user_wide=user_wide)
    if env:
        server["env"] = env
    return server


def _cursor_command(project: Path, *, user_wide: bool = False) -> str:
    """A name on PATH when that is enough. Else this process's interpreter."""
    if user_wide:
        return Path(sys.executable).as_posix()
    if _harness_is_importable() or looks_like_vibe_checkout(project):
        return "python3"
    return Path(sys.executable).as_posix()


def _cursor_env(project: Path, *, user_wide: bool = False) -> dict[str, str]:
    if user_wide:
        if _harness_is_importable():
            return {}
        return {"PYTHONPATH": (REPO_ROOT / "src").as_posix()}
    if looks_like_vibe_checkout(project):
        return {"PYTHONPATH": "${workspaceFolder}/src"}
    if not _harness_is_importable():
        return {"PYTHONPATH": (REPO_ROOT / "src").as_posix()}
    return {}


def _merge_mcp(dest: Path, server: dict) -> str:
    """Put py-harness in mcp.json. Keep every other server."""
    data: dict = {}
    if dest.is_file():
        try:
            loaded = json.loads(dest.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            data = loaded
    servers = data.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers
    servers["py-harness"] = server
    return json.dumps(data, indent=2) + "\n"


def _zed_settings(project: Path, dest: Path) -> str:
    """Merge py-harness into .zed/settings.json. Do not drop other keys."""
    incoming = _stdio_server(project)
    data: dict = {}
    if dest.is_file():
        try:
            loaded = json.loads(dest.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            data = loaded
    servers = data.setdefault("context_servers", {})
    if not isinstance(servers, dict):
        servers = {}
        data["context_servers"] = servers
    servers["py-harness"] = incoming
    return json.dumps(data, indent=2) + "\n"
