# antislop

The whole pipeline over one HTML or CSS file: audit, the four fixing moves when the score is three or more, a
committed direction when the page has none, a textured background on request, a polish and copy pass, and a
second audit. Model-backed. Reach for it when the ask is the whole job; reach for `audit`, `unslop`, `direct` and
`texture` when you want one step, or want to read a result between steps.

It works on a copy in a temporary directory and pulls its siblings through the same agent provider, model and
reasoning effort; an injected `Intelligence` drives every step. Nothing on disk changes unless `write` is true.

## Library

```python
def antislop(
    path: Path,
    write: bool = False,
    with_texture: bool = False,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> AntislopReport
```

- `path`: an existing `.html`, `.htm` or `.css` file.
- `write`: replace the file with the result. Otherwise the `diff` is the deliverable.
- `with_texture`: also run `texture` and apply its code when the page's background is a flat fill or plain
  gradient. Off by default; a texture is a choice, not a fix.
- `agent_provider`, `model`, `reasoning_effort`, `intelligence`: as every model-backed capability, documented
  under Intelligence in [the library reference](../01-library.md).

The steps, each recorded as a `PipelineStep` with `name`, `ran` and a one-line `note`:

1. `audit`: `audit(path=<copy>)`, the `before` report.
2. `unslop`: when `before.score >= 3`, `unslop(<copy>, write=True, audit_report=before)`; the note carries the
   plan length and the scan scores either side. Skipped below 3.
3. `direct`: one plain model call reads the copy's CSS custom properties, `font-family` and `background`
   declarations, title and headings, and answers whether the page commits to a direction (a clear ground, light
   and signal colour and non-default type), whether the background is flat, the brief the content implies and
   the palette if any. Without a direction, `direct(<brief>, directions=1)` is run and one writable agent pass
   adds the `:root` tokens, switches the fonts and puts the signal colour on the one thing to notice. Skipped
   when the page has a direction.
4. `texture`: with `with_texture`, a flat background and a palette (the applied direction's or the page's own),
   `texture(subject=<brief>, ground=..., light=..., signal=...)` and one writable pass that puts its code on the
   main background. Skipped otherwise, with the reason.
5. `polish`: one writable pass over the checklist (tabular numbers, 44px touch targets, no layout shift,
   loading and empty states, origin-aware and interruptible animation, `text-wrap: balance` on headings, 45 to
   75 character lines) and over the visible copy (shorter, more specific, no buzzwords, never a new claim).
6. `audit`: the `after` report.

Returns `AntislopReport`:

- `path`, `before`, `after`, `steps` as above.
- `diff`: a unified diff labelled `a/<name>` and `b/<name>`; empty when nothing changed.
- `written`: whether the file was replaced.
- `summary`: exactly three lines: the two scores, the biggest moves, what to check by hand.

Raises `UnslopperError` when the path is not an HTML or CSS file; when no agent provider is installed or its
preflight fails; when a step fails, naming the step and carrying the sibling's or the agent's own message; and
when the result dropped an `href`, `src` or `action` the original had (stylesheet and font `<link>` hrefs excepted), listing them. On every failure the
original is untouched.

Prompts live beside the code in `capabilities/antislop/`: `direction.md.liquid` (the read),
`apply-direction.md.liquid`, `apply-texture.md.liquid` and `polish.md.liquid` (the edit passes).

## CLI

```bash
unslopper antislop PATH [--write] [--with-texture]
                   [--agent-provider amplifier-agent|claude] [--model TEXT]
                   [--reasoning-effort low|medium|high|xhigh|max]
```

Calls `lib.antislop(path, write, with_texture, agent_provider, model, reasoning_effort)` and prints the
`AntislopReport` as JSON. A failure prints its message to stderr and exits 1. Expect several model calls and
minutes on a long page.

```bash
unslopper antislop landing.html --agent-provider claude > report.json
unslopper antislop landing.html --with-texture --write --reasoning-effort high
```
