# Drop-in editor settings

One command. You do not need a GPU to copy these files.

| Path | What it does | Localhost works? |
| --- | --- | --- |
| Cursor | `.cursor/mcp.json` + `.vscode/tasks.json` | Yes. Cursor starts the jail as a child process. No tunnel. |
| VS Code tasks | Command Palette → Run Task → `py-harness: ask` / `run` | Yes. Uses the jail in the integrated terminal. |
| Continue (VS Code) | Chat talks to `http://127.0.0.1:8081/v1` (Ollama proxy) | Yes. This changes the **brain**, not the jail. |
| Zed | Merges `context_servers` into `.zed/settings.json` | Yes. Same stdio jail. Existing Zed keys stay. |

```bash
py-harness editors cursor                 # this folder (default)
py-harness editors cursor --allow-writes  # let chat edit files
py-harness editors cursor --global        # every workspace, merge only
py-harness editors vscode
py-harness editors continue
py-harness editors zed
```

`--project` defaults to `.`. Then:

1. `ollama pull llama3.1:8b`
2. Reload the window. Customize → MCP → enable `py-harness`
3. Cursor Chat override of `127.0.0.1` is the hard path. Do not use a tunnel.

## What each file is

- `vscode/tasks.json` — `py-harness ask` and `py-harness run` with an input prompt
- `vscode/continue.yaml` — Continue `config.yaml` for the everyday 8B
- `cursor/mcp.json` — portable template (`${workspaceFolder}`, no machine path)
