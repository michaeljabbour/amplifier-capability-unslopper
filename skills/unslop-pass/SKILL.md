---
name: unslop-pass
description: >-
  Removes AI design defaults from an existing HTML or CSS page or component by applying twenty fixes
  in four moves (Subtract, Focus, Systematize, Respond) while keeping the content, brand colours,
  layout intent and every link and form. Shows a diff before writing. Use when a page or component "looks AI
  generated", "reads as design slop", needs "unslopping", or a design audit scored it three or more out of twenty.
license: MIT
metadata:
  repository: https://github.com/michaeljabbour/amplifier-capability-unslopper
---

# Unslop pass

An unslop pass takes a page a model wrote and removes the choices nobody made. The content stays,
the brand colours stay, the layout intent stays, every link and form keeps working. What goes is
the filler, and what arrives is one clear focus and a small system that holds the rest together.

## Prefer the tool when it is installed

If `unslopper` is on the path, let it do the pass. It scans the file, runs an agent that edits a
copy in a scratch directory, validates that every `href`, `src`, `action`, `<a>` and `<form>` (stylesheet and font `<link>` hrefs excepted)
survived, and returns a unified diff with a before and after score.

```bash
unslopper unslop page.html                      # propose: review the diff and the plan
unslopper unslop page.html --write              # apply, once the diff looks right
```

Read `unslopper unslop --help` first for the arguments and the result shape. When the file was
already audited, call the library so the audit guides the plan:

```python
from pathlib import Path
from unslopper.lib import audit, unslop

page = Path("page.html")
report = audit(path=page)
result = unslop(page, audit_report=report)
print(result.diff)
```

Always run without `--write` first, read the diff, then rerun with `--write`. Never skip the review
unless the user has asked for an unattended run. Report the before and after score from the result.

Install, if missing: `uv tool install "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"`.

## Doing the pass by hand

When the tool is not available, work the file yourself in this order. Finish one move before
starting the next. The canonical text of each fix is `unslopper reference fixes`, or
`knowledge.py` in the repository.

### 1. Subtract

Most slop is additive, so deleting is the cheapest work and comes first.

- Delete filler badges: a pill saying New, Beta or AI-powered on every item says nothing. Keep badges only for real state.
- Drop redundant labels: eyebrows that repeat the heading, section numbers on content with no order, all-caps lines of adjectives.
- Unitalicize random words: italics are for one word of genuine stress or a title.
- Mono only where needed: monospace belongs to code, data and terminals. Remove code breadcrumbs used as decoration.
- Remove embellishments: sparkles, glows, decorative arrows, extra nodes in diagrams. If it carries no meaning, cut it.

### 2. Focus

Decide what matters most and say it specifically.

- Show the actual product: replace abstract illustrations and fake dashboards with the real output.
- Enlarge the main feature: the one thing the page exists for is clearly bigger than everything else.
- Make headlines specific: say what the thing does for this reader, using facts already on the page.
- Emphasize the CTA: one solid primary action per view; every other action becomes a quiet link.
- Wrap headlines properly: `text-wrap: balance` and a max width in `ch` on headings.

### 3. Systematize

Replace one-off choices with a few rules applied everywhere.

- Use a design system: 4 to 6 colours, 2 to 3 fonts and one spacing scale as CSS custom properties; replace every one-off value.
- Group with spacing: related things closer, unrelated things further apart. Remove the borders and dividers that were doing this job.
- Add an accent colour: one saturated colour, used only for the thing to click or notice.
- Keep icons consistent: one family, one stroke weight, one size grid.
- Inner radius = outer radius minus padding, so nested corners stay concentric.
- Improve text contrast to WCAG AA: 4.5 to 1 for body text, 3 to 1 for large text. No grey at low opacity on a gradient.
- Use tabular nums (`font-variant-numeric: tabular-nums`) wherever numbers stack or change.
- Align by eye: nudge round shapes, triangles and type until they look aligned.

### 4. Respond

Design the moments between states.

- Add loading, empty and error states wherever the markup shows data, so the layout holds still.
- Animate useful feedback only: motion confirms an action (saved, added, moved) and nothing else. Wrap it in `@media (prefers-reduced-motion: no-preference)`.

## Rules that hold through every move

- Never invent new content claims. Rewrite copy only to be shorter and more specific.
- Keep every existing link and form behaviour working. Before and after, list the `href`, `src` and `action` values and the `<a>` and `<form>` counts; nothing may go missing. A `<link>` to a stylesheet or font is the one exception: it may change when a fix replaces the font.
- Keep scripts and the ids and classes they rely on.
- Respect `prefers-reduced-motion`.
- Show the diff and wait for approval before writing, unless told to run unattended.
- Finish by re-scanning (`unslopper scan page.html` when available) and reporting the before and after score.

## A worked example

Before:

```html
<div class="eb">02 - PLAN <span class="pill">NEW</span></div>
<h5>Plans <em>first</em>. Acts <em>second</em>.</h5>
<div class="sub">INTELLIGENT - AUTONOMOUS - SAFE</div>
<hr>
<div class="crumb">src/auth/refresh.py -> tests/auth/</div>
<p>Our powerful AI-driven planning engine lets you seamlessly see the plan before any changes are made, empowering you to edit, reorder, or reject it with confidence.</p>
<div class="ctas"><a href="/docs">Learn more -></a><a href="/start">Get started -></a></div>
```

After:

```html
<h5>Read the plan before it touches a file</h5>
<p>The agent lists every step and the files it will change. Edit a step, reorder it, or reject the plan and nothing runs.</p>
<pre class="shot">reproduce failing test
find the race in session refresh
patch auth/refresh.py</pre>
<a class="cta" href="/start">Try it on your repo</a> <a class="sec" href="/docs">See an example plan</a>
```

Subtract removed the number, eyebrow, pill, all-caps line, breadcrumb and dividers. Focus made the
headline specific, cut thirty words to twenty, showed the plan as the product and kept one solid
call to action. Systematize moved the card off the gradient onto a calm ground with one accent and
mono only inside the real plan. Both links survived.
