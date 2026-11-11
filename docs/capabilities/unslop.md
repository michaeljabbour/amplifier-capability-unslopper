# unslop

Applies the twenty fixes to one HTML or CSS file, in four moves: Subtract, Focus, Systematize, Respond. Model-backed.
An agent edits a copy of the file in a scratch directory, guided by the deterministic scan and, when given, an audit; the library validates the result, diffs it against the original and scans it again.
Nothing on disk changes unless `write` is true, so the diff is the deliverable to review first.

Reach for it when `scan` or `audit` shows a score worth fixing on a file you can edit.
For a whole pass with direction and texture, use `antislop`, which calls this.

## Library

```python
def unslop(
    path: Path,
    write: bool = False,
    audit_report: AuditReport | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> UnslopResult
```

- `path`: an existing `.html`, `.htm` or `.css` file.
- `write`: replace the file with the edited text, keeping its newline style. Off by default.
- `audit_report`: an `AuditReport` of the same file, when one was made. Its findings and `fixes_first` guide the plan; findings marked deliberate are left alone.
- `agent_provider`, `model`, `reasoning_effort`, `intelligence`: as every model-backed capability, see the [library reference](../01-library.md). The agent gets a writable workspace holding only the copy, and thirty minutes.

Returns `UnslopResult`:

- `path`: the file given.
- `plan`: `PlannedChange` entries in the order the agent made them, each with `move`, `fix_id`, `fix` and a one-sentence `change`.
- `diff`: a unified diff from the original to the edited text, labelled `a/<name>` and `b/<name>`. Empty when the agent changed nothing.
- `before`: `scan(path=path)`, taken before the agent ran.
- `after`: `scan(source=edited)`, so the drop in score is deterministic evidence.
- `written`: whether the file was replaced.
- `notes`: what to check by hand: shortened copy, the accent chosen, states that need real data.

Raises `UnslopperError`, leaving the file as it was, when the path is not an existing HTML or CSS file, when no agent provider is installed or configured, when the agent errors or times out, or when the edited file is empty, dropped an `href`, `src` or `action` value, or has fewer `<a>` or `<form>` elements than the original. The message names what failed, what to configure or retry, and the missing link targets when that is the cause.

The prompt is `capabilities/unslop/unslop.md.liquid`, rendered from `knowledge.MOVES` and `knowledge.FIXES` so the moves and fixes cannot drift from the course material.

```python
from pathlib import Path

from unslopper.lib import audit, unslop

page = Path("landing.html")
report = audit(path=page)
result = unslop(page, audit_report=report)
print(result.before.score, "->", result.after.score)
print(result.diff)
if result.after.score < result.before.score:
    unslop(page, write=True, audit_report=report)
```

## CLI

```bash
unslopper unslop PATH [--write] [--agent-provider amplifier-agent|claude] [--model TEXT] [--reasoning-effort low|medium|high|xhigh|max]
```

Calls `lib.unslop(path, write, None, agent_provider, model, reasoning_effort)` and prints the `UnslopResult` as JSON to stdout. The CLI cannot pass an audit report; use the library for that.
A failure the library can name prints its message to stderr and exits 1; a bad invocation exits 2.

```bash
unslopper unslop landing.html                      # propose: plan, diff and scores as JSON
unslopper unslop landing.html --write              # apply
unslopper unslop styles.css --agent-provider claude --reasoning-effort high
```
