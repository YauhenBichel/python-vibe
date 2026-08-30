---
name: merge-pr
description: Merges one pull request, and refuses the ones a person should read. Use only when the task says merge. Do not force. Do not use for add.
---

Action: merge
Number: 16

The merge is refused, with the reason, when GitHub says a check is
failing or still running, when the branch conflicts or is blocked, or
when a bot's title says a first version number changed.

`Bump actions/github-script from 7 to 9` reads like every other weekly
bump. Its release notes say `require('@actions/github')` stops working.
A major bump is where breaking changes are allowed to live, so that one
goes to a person. Report the reason and stop; do not try again with
force, and do not merge a different number instead.
