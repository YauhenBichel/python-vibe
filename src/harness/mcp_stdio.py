"""Local MCP over stdio so an editor can apply the write limit without a tunnel.

This is the editor calling py-harness. It is not an Action the 8B may emit.
Stdout is JSON-RPC only. Logs go to stderr.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from harness.agent import Agent, AgentOptions

PROTOCOL = "2024-11-05"
PROMPTS = (
    {
        "name": "ask",
        "description": "Read-only question. py-harness does not change files.",
        "arguments": [
            {"name": "task", "description": "The question", "required": True}
        ],
    },
    {
        "name": "run",
        "description": "Explore, edit and run inside the project folder.",
        "arguments": [
            {"name": "task", "description": "What to do", "required": True}
        ],
    },
)

TOOLS = (
    {
        "name": "ask",
        "description": (
            "Read-only question about the project. Uses the py-harness write limit. "
            "Does not change files."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"task": {"type": "string"}},
            "required": ["task"],
        },
    },
    {
        "name": "run",
        "description": (
            "Explore, edit and run inside the project folder. Writes only when "
            "the server was started with --allow-writes."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "scope": {"type": "string"},
            },
            "required": ["task"],
        },
    },
    # These two need no model and take under a second, which makes them
    # the ones worth reaching for in an editor. Only ask and run were
    # offered, so the only tools an editor had were the two slowest and
    # least certain.
    {
        "name": "brief",
        "description": (
            "Summarise this project: how large it is, what is in it, and "
            "whether it is small enough to read whole. Needs no model."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"scope": {"type": "string"}},
        },
    },
    {
        "name": "layout",
        "description": (
            "Report what makes this project hard to read: import cycles, "
            "a folder with no grouping, an oversized module. Needs no model."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"scope": {"type": "string"}},
        },
    },
)


def _text(rpc_id, body: str) -> dict[str, Any]:
    """One plain answer, in the shape an editor expects."""
    return {
        "jsonrpc": "2.0",
        "id": rpc_id,
        "result": {"content": [{"type": "text", "text": body}]},
    }


def _describe(name: str, project: Path, scope: str) -> str:
    """Answer brief or layout. Neither loads a model."""
    from harness.scan.layout import render_layout
    from harness.scan.project_brief import (
        classify_project,
        render_brief_for_person,
        resolve_scope,
    )

    if name == "brief":
        return render_brief_for_person(
            classify_project(project, scope), scope=scope
        )
    base = resolve_scope(project, scope) if scope else project
    return render_layout(base)


def handle_rpc(
    message: dict[str, Any],
    *,
    project: Path,
    allow_writes: bool,
    model: str,
) -> dict[str, Any] | None:
    """One JSON-RPC message. Notifications return None."""
    method = str(message.get("method") or "")
    rpc_id = message.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {}, "prompts": {}},
                "serverInfo": {"name": "py-harness", "version": "0.1.0"},
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": list(TOOLS)}}
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"prompts": list(PROMPTS)}}
    if method == "prompts/get":
        params = message.get("params") or {}
        name = str(params.get("name") or "")
        args = params.get("arguments") or {}
        task = str(args.get("task") or "").strip() or "what does this project do?"
        if name not in {"ask", "run"}:
            return _error(rpc_id, f"unknown prompt {name}")
        verb = "ask" if name == "ask" else "run"
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "description": f"Call the py-harness {verb} tool",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": f"Use the py-harness {verb} tool with task: {task}",
                        },
                    }
                ],
            },
        }
    if method == "tools/call":
        params = message.get("params") or {}
        name = str(params.get("name") or "")
        args = params.get("arguments") or {}
        scope = str(args.get("scope") or "").strip()
        if name in {"brief", "layout"}:
            return _text(rpc_id, _describe(name, project, scope))
        task = str(args.get("task") or "").strip()
        if not task:
            return _error(rpc_id, "task required")
        if name == "run" and not allow_writes:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "this server is read-only. Restart it with "
                                "--allow-writes, or run py-harness run in the terminal."
                            ),
                        }
                    ],
                    "isError": True,
                },
            }
        if name not in {"ask", "run"}:
            return _error(rpc_id, f"unknown tool {name}")
        options = AgentOptions(
            project=project,
            task=task,
            model=model,
            scope=str(args.get("scope") or ""),
            allow_writes=allow_writes and name == "run",
        )
        try:
            result = Agent(options).run()
        except (ValueError, OSError) as exc:
            return _error(rpc_id, str(exc))
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "content": [{"type": "text", "text": describe(result)}],
                "isError": not result.ok,
            },
        }
    if rpc_id is None:
        return None
    return _error(rpc_id, f"unknown method {method}")


def describe(result) -> str:
    """What to show in the editor: the answer, and what it left behind.

    The summary alone is not enough when a run stops early. A person who
    asked for a feature and got a question back also needs to know that
    files were changed and that the tests no longer pass, or they will
    find out later and blame the wrong thing.
    """
    lines = [result.summary or "done"]
    if result.writes:
        changed = ", ".join(sorted(set(result.writes)))
        lines.append(f"\nChanged: {changed}")
    if not result.ok:
        if result.stopped == "question":
            lines.append(
                "This run stopped to ask. Nothing further was done, so the "
                "change above may be half finished — run the tests before "
                "relying on it."
            )
        elif result.stopped == "steps":
            lines.append(
                "This run ran out of steps before it finished. Check what "
                "changed above."
            )
    return "\n".join(lines)


def _error(rpc_id: Any, text: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32600, "message": text}}


def _read_message(stdin: TextIO) -> dict[str, Any] | None:
    """Read one message. Lines are the transport; headers are tolerated."""
    first = stdin.readline()
    if first == "":
        return None
    if first.lstrip().startswith("{"):
        return json.loads(first)
    headers: dict[str, str] = {}
    line = first
    while line not in ("", "\r\n", "\n"):
        key, _, value = line.partition(":")
        headers[key.strip().lower()] = value.strip()
        line = stdin.readline()
        if line == "" and "content-length" not in headers:
            return None
    length = int(headers.get("content-length") or "0")
    raw = stdin.read(length) if length else ""
    return json.loads(raw) if raw else None


def _write_message(stdout: TextIO, payload: dict[str, Any]) -> None:
    """One message per line, as the stdio transport requires.

    The specification says messages are delimited by newlines and must not
    contain embedded newlines. Content-Length headers are the convention in
    the Language Server Protocol, not this one, and a client that expects
    lines cannot read them.
    """
    # json.dumps escapes a newline inside a value, so the serialized form is
    # already a single line.
    stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    stdout.flush()


def serve_stdio(
    project: Path, *, allow_writes: bool = False, model: str = ""
) -> int:
    print(
        f"py-harness mcp  project {project}  "
        f"{'read-write' if allow_writes else 'read-only'}",
        file=sys.stderr,
        flush=True,
    )
    while True:
        try:
            message = _read_message(sys.stdin)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"bad mcp message: {exc}", file=sys.stderr)
            continue
        if message is None:
            return 0
        reply = handle_rpc(
            message, project=project, allow_writes=allow_writes, model=model
        )
        if reply is not None:
            _write_message(sys.stdout, reply)
