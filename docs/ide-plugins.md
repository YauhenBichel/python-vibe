---
title: IDE plugins
description: How to use python-vibe from an editor, and which packages to use if you write a plugin. The harness stays standard-library.
permalink: /ide-plugins/
date: 2026-08-29
---

# IDE plugins

python-vibe is already a plugin target. You do **not** need a new Python
dependency to call it. The harness is the standard library. An editor
starts `python-vibe mcp` or `python-vibe serve` as a child process.

Related: [local editor]({{ '/local-editor/' | relative_url }}) ·
[Commands]({{ '/api/' | relative_url }}).

## Use it (no plugin to write)

```bash
pip install -e .
ollama pull llama3.1:8b
python-vibe editors cursor --allow-writes
```

Cursor: [use python-vibe in Cursor]({{ '/cursor/' | relative_url }}).
`--project` defaults to this folder.

| You want | Command | Package to install |
| --- | --- | --- |
| Cursor chat + tasks | `editors cursor` | none. Writes `.cursor/mcp.json` and `.vscode/tasks.json` |
| Tasks only | `editors vscode` | none (uses `.vscode/tasks.json`). Walkthrough: [VS Code]({{ '/vscode/' | relative_url }}) |
| Chat that hits Ollama | `editors continue` | the Continue extension, already on the marketplace |
| Zed | `editors zed` | none. Merges `context_servers` |
| HTTP OpenAI shape | `python-vibe serve --project ~/app` | any OpenAI-compatible client |

Do not add the official MCP Python SDK to *this* repo. The write limit stays
stdlib so `pip install -e .` builds nothing on Windows, macOS, or Linux.

## Write a plugin (other repo)

Treat python-vibe as a **subprocess**, not as a library you re-implement.

1. **Require** `python-vibe` on PATH (`pip install python-vibe` or
   `-e .` from a clone).
2. **Spawn** one of:
   - `python-vibe mcp --project <abs>` — JSON-RPC on stdin/stdout
   - `python-vibe serve --project <abs>` — `127.0.0.1` only
   - `python-vibe run <abs> "<task>" --json` — one-shot
3. **Never** expose it to the internet. Hosted chat that cannot see loopback
   should use tasks or a local child process.

### Packages that are actually useful

| Job | Package | Why |
| --- | --- | --- |
| VS Code / compatible extension | `@types/vscode` + `vsce` | Register a task, or register an MCP server definition |
| Register MCP from an extension | VS Code `lm.registerMcpServerDefinitionProvider` | Points at `python-vibe mcp`. Do not rewrite the write limit in TypeScript |
| Talk MCP from TypeScript | `@modelcontextprotocol/sdk` | Only if you write a *different* server. To wrap us, spawn stdio |
| Talk MCP from Python | `mcp` (PyPI, official SDK) | Same: other servers. Our server is already stdlib JSON-RPC |
| OpenAI-shaped HTTP | official `openai` client | Base URL `http://127.0.0.1:8090/v1`, model `llama3.1:8b` |
| Language Server | `pygls` | Only if you want diagnostics in the editor. Not required for the agent loop |
| JetBrains | that IDE’s MCP / external tool | Spawn the same `python-vibe mcp` command |

Do **not** pull `mlx-lm` or `huggingface_hub` into an editor plugin.
Those are `[train]` / `[hub]` extras. The everyday loop does not need
them.

### Minimal VS Code-shaped extension

The extension’s only job is to find `python3` / `python-vibe` and
register:

```
command: <sys.executable>
args: ["-m", "harness", "mcp", "--project", "<workspace>"]
```

That is what `python-vibe editors cursor` and `editors zed` already
write. A marketplace extension is the same spawn, plus a setting for
`--allow-writes`.

### What not to build

- A second agent loop in TypeScript
- A public HTTPS tunnel “so hosted chat works”
- Extra tools (browser, free shell) for the 8B
- A rewrite of `mcp_stdio.py` on top of the `mcp` SDK just to add a
  dependency

The easy package is **this one**. Plugins are a thin spawn around it.
