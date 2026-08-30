---
title: Everyday skills
description: Skills for the everyday 8B are one copy-paste Action. Publish only after skill_probe.py shows the intended first Action.
date: 2026-08-29
type: article
---

# Investigation: skills written for the everyday 8B

The everyday brain is small. It does not follow a 7-step essay. It copies
**one `Action:` block** — often the first example in the system prompt, or
it pastes the whole menu. Skills are published only after
`scripts/skill_probe.py` on this machine.

Related: [everyday-laptop](./everyday-laptop.md).

## Experiments (29 Aug 2026, `llama3.1:8b`)

Verbose skills (when-to / numbered steps):

| Task | First action | Result |
| --- | --- | --- |
| `what does apply_source refuse?` | `read` random file | Missed `code.py` |
| same + “start with grep” | `read` then `grep` then `done` | No refuse rules |
| `add … multiply` | `Find: def add(left` | Syntax break (harness now refuses) |
| same | `Action: write-tests` | Not an action |

Tiny skills + harness prelude + short system prompt
(`scripts/skill_probe.py`):

| Task | prelude | First parsed action | Notes |
| --- | --- | --- | --- |
| apply_source refuse | yes | **`done`** | Summary named empty draft, 2/3 length, syntax |
| apply_source refuse | no | `grep` + wrong `read` | Invented a non-ASCII story |
| add multiply | yes, long system prompt | `skill` (menu dump) | 8B pasted every Action example |
| add multiply | yes, short system prompt | **`patch` + Append** | Intended first step |

Then: if the model still dumps a menu, `parse_turn_smart` keeps **one**
block — `done`/`locate` on a question, `patch`/`edit` on an add.

Third-party small tree (33 `.py`/`.md`, Mode: small, `src/harness` scope),
same day, after locate shipped:

| Task | First action | Result |
| --- | --- | --- |
| `what does listen_addr return?` | `read` the already auto-read file | Correct tuple answer after a wasted step. `start_hint` still said grep/read. |
| `what does complete do after two blocked drafts?` (probe) | `read` + `Append:` body | Would have edited a question if applied. |

Harness now: `start_hint(..., located=True)` says done only; questions
refuse `patch`/`edit`/`run`; a second `read` of the auto-read file is
refused. `File:` is an alias for `Path:`. A `done` that omits the `->`
type (for example `tuple[str, int]`) is refused once so the 8B quotes
the signature instead of “a tuple”.

Add-feature on the kit fixture (29 Aug 2026): `multiply` landed, but the
test was `Append:` after `if __name__` with no import, so unittest ran
**1** test. Harness now inserts `def test_` before `if __name__`, adds
the import, refuses a second `locate` after prelude, and injects the
write-tests skill after the implementation patch.

## What to publish

These kit skills, each a **single copy-paste Action** (no essays):

- `skills/answer-question/SKILL.md`
- `skills/add-feature/SKILL.md`
- `skills/write-paths/SKILL.md` — one `pathlib` helper. Both venv
  layouts. `Path.home()`. No `os.path.join`.
- `skills/write-tests/SKILL.md` — one AAA method named
  `test_<unit>_<result>` (`got = multiply(...)`, then assert `got`).
  A single new test that asserts without arranging is refused, as is an
  opaque name such as `test_it_works`. A short name that still says what it
  covers, such as `test_health`, is allowed: the rule is calibrated so that
  none of this project's own 26 test files is refused by it.
- `skills/stay-scoped/SKILL.md`
- `skills/new-package/SKILL.md` — `pkg/__init__.py` exports only, then
  `pkg/<noun>.py`. SoC, not a SOLID lecture.
- `skills/fix-smell/SKILL.md` — one `Find:` / `Replace:` to a readable
  snake_case name (`total_price`, not `calc`).
- `skills/read-issue/SKILL.md` — `Action: issue Number: N` (or `Action: pr Number: N`). Brief names files in this project and comments from other users on the ticket, using the signed-in `gh` user.
- `skills/open-pr/SKILL.md` — `Action: pr Title:` + `Body: Closes #N`
- `skills/merge-pr/SKILL.md` — `Action: merge Number: N` only when the
  task says merge

Ship is limited (`src/harness/ship/git_ship.py`): no `--force`, not
`main`/`master`, unstage `.env` / `credentials.json`. Order: issue →
branch → patch → commit → push → pr.

Harness: `refuse_opaque_names` (`calc`/`tmp`/`x`, CamelCase functions,
snake_case classes) and `refuse_layout` (no impl in `__init__.py` or
`scripts/`; split a module with 4+ functions).

Plus harness: `prelude()` locate before the model, `Action: locate`,
`parse_turn_smart`, syntax reject, skill-name-as-action.

Live `create a package for total_price` (empty dir, 29 Aug 2026):
`pkg/__init__.py` (export only) → `pkg/total_price.py` → a `TestCase` →
`unittest` OK → done. A bare `def test_*(self)` is wrapped. `done`
before a passing run is refused.

Do not publish a new skill until `skill_probe.py` shows the intended
`action` with `"prelude": true`.

## Do not

- Do not train more 0.5B to “learn skills”.
- Do not put hostnames or personal paths on Pages.
- Do not name third-party products in skill text.
