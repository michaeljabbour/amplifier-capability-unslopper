`antislop` is the one entry point that chains the other capabilities over a single HTML or CSS file
and reports a before and after score. Reach for it when the ask is "make this page not look
generated" and you do not want to drive `audit`, `unslop`, `direct`, `texture` and a polish pass by
hand; reach for the single steps when you want only one of them, want to read a result between steps,
or are working on a screenshot or a URL (this capability takes a file).

It works on a copy, so nothing on disk changes unless `--write` is given. Without it, the `diff` in the
result is the deliverable: review it, then apply it or rerun with `--write`.

## Pipeline

1. `audit`: the model-backed audit of the file, the `before` score.
2. `unslop`: when the score is 3 or more, the four moves (Subtract, Focus, Systematize, Respond) are
   applied to the copy. Below 3 the step is skipped and says so.
3. `direct`: one model read of the page's CSS custom properties, fonts and backgrounds decides whether
   it commits to a direction (a clear ground, light and signal colour and non-default type). When it does
   not, `direct` is run with a brief inferred from the title and headings, and the chosen tokens, fonts
   and signal colour are applied to the copy.
4. `texture`: only with `--with-texture`, and only when the background is flat; `texture` draws a
   background from the subject's world in the page's palette, and it replaces the flat fill.
5. `polish`: tabular numbers where numbers stack or change, touch targets of at least 44px, no layout
   shift, loading and empty states where there is data, origin-aware and interruptible animation,
   `text-wrap: balance` on headings, 45 to 75 character lines; plus a copy pass over all visible text
   (shorter, more specific, no buzzwords, never a new claim).
6. `audit` again: the `after` score.

Every `href`, `src` and `action` of the original must survive (a `<link>` stylesheet or font href is the exception, since fonts may change); the run fails otherwise and the original is
left alone. It makes several model calls (two audits, the unslop pass, a direction read and up to three
edit passes) and takes minutes on a long page.

## Arguments

- `PATH`: an existing `.html`, `.htm` or `.css` file. Required.
- `--write`: replace the file with the result. Otherwise only the diff comes back.
- `--with-texture`: also add a textured background when the page is flat.
- `--agent-provider [amplifier-agent|claude]`: the agent provider to run through; the first installed
  when omitted.
- `--model TEXT`: the model to run on; the agent provider's default when omitted.
- `--reasoning-effort [low|medium|high|xhigh|max]`: how hard the model thinks. Default `medium`.

Credentials come from the environment (`ANTHROPIC_API_KEY` for `claude`, the provider's variables for
`amplifier-agent`); nothing reads a `.env` file.

```bash
unslopper antislop landing.html --agent-provider claude
unslopper antislop landing.html --with-texture --write --reasoning-effort high
```

```python
from pathlib import Path

from unslopper.lib import antislop

report = antislop(Path("landing.html"), with_texture=True)
print(report.summary)
for step in report.steps:
    print(step.name, "ran" if step.ran else "skipped", step.note)
Path("landing.diff").write_text(report.diff)
```

## Result

`AntislopReport`:

- `path`: the file given.
- `before`, `after`: the two `AuditReport`s, each with `score` out of twenty, `verdict`, `summary`,
  `findings` and `fixes_first`.
- `steps`: six `PipelineStep`s in order (`audit`, `unslop`, `direct`, `texture`, `polish`, `audit`), each
  with `name`, `ran` and a one-line `note` saying what happened or why it was skipped.
- `diff`: a unified diff from `a/<name>` to `b/<name>`; empty when nothing changed.
- `written`: whether the file was replaced.
- `summary`: exactly three lines: the scores, the biggest moves, what to check by hand.

## Failures

`UnslopperError`, exit 1 from the CLI, naming the step that failed: the path is not an HTML or CSS file; no
agent provider is installed or its credentials are missing (the message carries the install command or the
variable to set); a step's agent failed or timed out; a step returned no structured answer; or the result
dropped a link target (the message lists them). On every failure the original file is untouched; rerun,
or with `--reasoning-effort high` when the agent gave up.
