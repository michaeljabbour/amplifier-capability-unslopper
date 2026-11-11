---
name: design-slop-audit
description: >-
  Reviews a visual design (a screenshot, an HTML or CSS file, or a live URL) against twenty indicators of AI
  design defaults and reports which show, with evidence, whether each looks deliberate or default, a score out
  of twenty and the three fixes to make first. Read-only, so it is safe to run on anything. Use when asked
  whether a design looks AI-generated, to audit or review a landing page or mockup for slop, or before fixing
  one. Triggers on "design slop", "this design looks AI generated", "audit this design for AI defaults", "AI slop page".
license: MIT
metadata:
  repository: https://github.com/michaeljabbour/amplifier-capability-unslopper
---

# Design slop audit

Slop is what happens when every design choice is a default. None of the twenty indicators below is wrong in
itself; each becomes a tell when it appears without a reason, and when it appears alongside four others. The
audit names which ones show, points at the evidence, and separates defaults from deliberate choices. It never
rewrites the design.

## Prefer the tool when it is installed

If `unslopper` is on the path, use it: it runs the method below with the course material as data and
returns JSON. Read `unslopper audit --help` before calling it.

```bash
unslopper scan page.html                      # deterministic, free: what static heuristics can see
unslopper audit page.html                     # model-backed: confirms, rejects and adds judgment
unslopper audit --url https://example.com
unslopper audit --image screenshot.png --agent-provider claude
```

Install it with `uv tool install "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"`.
Without it, or without a model provider, do the audit by hand as follows. `references/indicators.md`
carries one paragraph per indicator: what it looks like, why models produce it, and when it is fine.
Label this a manual review, not a successful model-backed tool run. Missing credentials do not block `scan`.

## The method

1. Load the design. Read HTML and CSS as text, including inline styles and font links. View a screenshot.
   For a URL, include linked CSS where available and disclose unloaded assets, unsupported CSS and truncation.
   Source inspection is partial evidence, not a rendered-page or runtime test.
2. Scan one layer at a time, in this order. Look at the letters before anything else, then fills, edges and
   effects, then the scaffolding around the content, and finally what is actually said and shown.
   - Type: Instrument Serif (or another trend display serif), Excessive italics, Negative kerning,
     Excessive mono fonts, ALL CAPS subtitles, Periods in titles.
   - Surface: Gradient backgrounds, Color shades and opacities, Squircles, Containers with borders,
     Overusing dividers, Dithering, ASCII images.
   - Structure: Tags and pills, Eyebrows, Section numbering, Code breadcrumbs.
   - Content: Verbose, redundant text, Over-the-top detailed UI, Overly detailed diagrams.
3. For each indicator you see, record where it appears (element, selector, line, or region of the image)
   and the evidence (quote the text or CSS value, or describe the visual). Do not report an indicator you
   cannot point at. Functional navigation, filters, real status badges and hidden empty/loading/error states
   are not filler. Intentional sentence headings may keep their periods. Flat backgrounds and coherent
   palettes do not need replacement simply because they are restrained.
4. Decide deliberate or default. A choice is deliberate when it repeats consistently across the design and
   connects to the subject's world: a serif with wide-tracked small caps for a watchmaker, dithering for a
   retro game, a real file path inside a terminal tool's own output. Flag it as a default otherwise.
   Deliberate findings are reported and left alone; they do not count toward the score.
5. Score: the number of distinct indicators present as defaults, out of 20. Read it on the course's scale:
   0 "No defaults showing"; 1 to 2 "Mostly intentional. Check those were choices"; 3 to 5 "Some defaults
   showing"; 6 to 9 "Reads as generated"; 10 or more "Pure default output".
   These are legacy course labels, not a visual-quality grade. The deterministic `scan` counts candidates,
   not confirmed defaults. Neither count is an automatic rewrite gate; verify the actual problem first.
6. Order the findings by impact, highest first, and name the three fixes to make first. Most slop is
   additive, so subtraction comes first: delete filler badges, drop redundant labels, unitalicize random
   words, keep mono only where needed, remove embellishments. Then focus: make headlines specific,
   emphasize one call to action, enlarge the main feature, show the actual product. Then systematize:
   group with spacing, use a design system, add one accent colour, improve text contrast, make nested
   radii concentric (inner radius equals outer radius minus padding).

## Output

A short verdict line, then the findings ordered by impact, then the three fixes to make first, then the
score out of 20. For each finding: the indicator, where it appears, the evidence, and whether it looks
deliberate or default with a one-sentence reason. State coverage limits and whether rendered desktop/mobile
views and interactions were checked. Do not claim improvement from a lower count alone. Keep it terse; the
reader decides what to change.
