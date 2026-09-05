---
name: new-package
description: Scaffolds pkg/ + tests/ with exports-only __init__. Use when the task is create a package or project structure. Do not use for one function on an existing module.
---

Action: edit
Path: pkg/__init__.py
```python
"""Public exports only. Implementation lives in sibling modules."""
```

New code goes in `pkg/<noun>.py`, not `__init__.py` and not
`scripts/`. One noun per module. A CLI uses argparse. HTTP uses
urllib. Token from the environment. No curl.
