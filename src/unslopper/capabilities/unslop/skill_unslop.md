`unslop` takes one HTML or CSS file and applies the twenty fixes in four moves, Subtract, Focus,
Systematize, Respond, through an agent that edits a copy of the file in a scratch directory. It
keeps the content, brand colours, layout intent and every link and form, shortens copy without
inventing claims, and returns the change as a unified diff with a deterministic scan of the file
before and after. Without `--write` nothing on disk changes: the diff is the deliverable, to review
before running again with `--write`. Reach for it after confirming problems worth fixing, not merely
a scan score; for the whole pipeline with direction and texture, use `antislop` instead.

## Arguments

- `PATH`: the `.html`, `.htm` or `.css` file to fix. Required; must exist.
- `--write`: replace the file with the edited text, keeping its newline style. Off by default.
- `--agent-provider [amplifier-agent|claude]`: the agent provider to run through. The first
  installed when omitted.
- `--model TEXT`: the model to run on. The agent provider's default when omitted.
- `--reasoning-effort [low|medium|high|xhigh|max]`: how hard the model thinks. Default `medium`.
  A long page deserves `high`.

```bash
unslopper unslop landing.html                      # propose: prints the plan, diff and scores
unslopper unslop landing.html --write              # apply, once the diff looks right
unslopper unslop styles.css --agent-provider claude --reasoning-effort high
```

```python
from pathlib import Path

from unslopper.lib import audit, unslop

page = Path("landing.html")
report = audit(path=page)
result = unslop(page, audit_report=report)  # the audit's findings guide the plan
print(result.diff)
for change in result.plan:
    print(change.move, change.fix, change.change)
# Review the diff, coverage warnings, rendered layouts and interactions before writing.
```

## Result

`UnslopResult` with `path`, `plan` (a list of `PlannedChange`: `move`, `fix_id`, `fix`, `change`),
`diff` (unified, labelled `a/<name>` and `b/<name>`), `before` and `after` (`ScanReport`s with
`score`, `verdict`, `hits`, `fixes_first`; `after` is a scan of the edited text), `written` (true
only with `--write`) and `notes` (what to check by hand: shortened copy, the accent chosen, states
that need real data). The deterministic score counts candidates. A drop is not proof of better
design or working behavior; compare equivalent coverage and verify the rendered result.

## Failures

Fails with a message naming the fix, and never changes the file, when: `PATH` is missing or not
`.html`, `.htm` or `.css`; no agent provider is installed or its credentials are not set; the agent
errors or times out (thirty minutes); the edited file is empty, dropped an `href`, `src` or
`action` value (a `<link>` stylesheet or font href may change), or has fewer `<a>` or `<form>`
elements than the original. The message names
the missing link targets, so the run can be retried or the file fixed by hand.
