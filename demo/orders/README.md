# orders — the demo project

A deliberately imperfect little app, used by `scripts/run/demo.py` to show what
python-vibe does on ordinary daily tasks. Every problem here is planted:

- `src/orders.py` has a latent `NameError` in `total_with_tax`, which no
  test covers.
- `src/util.py` has `calc`, a name that says nothing.
- `src/report.py` and `src/render.py` import each other.
- Nothing tests `apply_discount`.
- `src/orders_service.py` (`OrderService`) and `src/orders_controller.py`
  (`OrdersController`) have no tests. The controller has an opaque `fn`
  and a `NameError` in `status` (`stauts`).

The demo copies this directory before each case, so a run never changes it.

From the python-vibe checkout:

```bash
source .venv/bin/activate
cd demo/orders
python-vibe brief
python-vibe ask  "what does compute_total return?"
python-vibe run  "find the NameError and fix it"
```

If the shell says `command not found: python-vibe`, the venv is not
active. Activate it in every new terminal. Do not run `brief` on the
checkout root — that briefs the whole tree.
