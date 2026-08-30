# Security Policy

## Reporting a vulnerability

Open a **public** GitHub issue on this repo. Label it `security` if you can.

Include:

- what the issue is and where in the code it lives
- how to reproduce it
- what an attacker could do with it

Do **not** paste live API keys, tokens, or `.env` contents into the issue.
Redact secrets and describe them instead.

## Scope

In scope:

- the HTTP sidecar (`scripts/run/serve.py`) — unbounded body size, binding
  `0.0.0.0` by default, SSRF if `OLLAMA_HOST` is attacker-controlled
- harness misses that ship a **blocked** class of output (`pass` on a leaked
  key or `curl|sh`)
- secrets committed to the repository
- dependency issues reachable from `scripts/run/serve.py` or the harness

Out of scope (still a normal issue is fine):

- paraphrase evasion of string rules
- model quality / ugly Python
- needing a Hugging Face token to train

## Data safety

- Never commit `.env`, `HF_TOKEN`, or adapter folders
- Never paste a real API key into an issue, even as a "repro"
