# Cursor

Three steps. No tunnel. No Override OpenAI Base URL.

```bash
pip install -e .          # from a py-harness clone, once
ollama pull llama3.1:8b
py-harness editors cursor --allow-writes
```

That writes `.cursor/mcp.json` and `.vscode/tasks.json` in the folder you
are in. `${workspaceFolder}` is filled by Cursor, so the file has no
machine path and you can commit it.

Then:

1. Command Palette → **Developer: Reload Window**
2. **Customize → MCP** → enable `py-harness`
3. In chat: “ask py-harness what compute_total returns”

Tools: `ask` (never writes) and `run` (writes only with `--allow-writes`).

Every workspace on this machine:

```bash
py-harness editors cursor --global --allow-writes
```

That merges into `~/.cursor/mcp.json` and leaves your other servers alone.

Do not set Models → Override OpenAI Base URL to `http://127.0.0.1:…`.
Many builds send that request from another machine, which cannot see
your loopback. A public tunnel would expose the jail. Use MCP or
**Tasks: Run Task → py-harness: ask**.
