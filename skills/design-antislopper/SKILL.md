---
name: design-antislopper
description: >-
  Takes any HTML or CSS design through the whole de-sloppping method, end to end: audit against the twenty AI
  design defaults, apply the four fixing moves, commit to a three-colour direction when there is none, add a
  textured background when the page is flat, polish the craft and the copy, then re-audit and report the before
  and after score. Use when asked to make a page "not look AI-generated", "unslop this design", "clean up this
  landing page", or to run the visual twin of a writing antislop pass. Prefers the `unslopper antislop` command
  when it is installed and runs the same method by hand otherwise.
license: MIT
metadata:
  repository: https://github.com/michaeljabbour/amplifier-capability-unslopper
---

# Design antislopper

One entry point for a design artifact: it goes in generic and comes out committed, with a short account of what
changed. The visual counterpart to a writing antislop tool; the two run well together, and the copy pass here
covers the words that live inside the page.

## Prefer the tool

When `unslopper` is installed, run the pipeline rather than driving it by hand:

```bash
unslopper antislop --help                     # the capability's skill, read it first
unslopper antislop page.html                  # the diff is the deliverable; nothing on disk changes
unslopper antislop page.html --with-texture --write
```

Install: `uv tool install "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"`.
Credentials come from the environment (`ANTHROPIC_API_KEY` for the `claude` agent provider, the provider's own
variables for `amplifier-agent`). Never read a `.env` file to find them.

The result carries `before` and `after` audits, six `steps` (each says whether it ran and why not), the unified
`diff`, and a three-line `summary`. Relay the summary and hand over the diff. It makes several model calls and
takes minutes on a long page.

## The method, by hand

Without the tool, run the same six stages with the sibling skills: `design-slop-audit`, `unslop-pass`,
`palette-director` and `texture-backgrounds`. Work on a copy. Never write over the original until the end, and
then only when asked.

1. Audit. Score the file against the twenty indicators with `design-slop-audit`. Keep the score, the verdict
   and the three fixes to make first; that is the "before".

2. Four moves. If the score is 3 or more, run `unslop-pass` in this order: Subtract (filler badges, redundant
   labels, random italics, mono where it means nothing, embellishments), Focus (show the product, enlarge the
   main feature, make the headline specific, one emphasised CTA, headlines that wrap), Systematize (a small
   token set, grouping by spacing not borders, one accent, consistent icons, inner radius = outer minus padding,
   AA contrast, tabular numbers, optical alignment), Respond (loading, empty and error states; motion only where
   it confirms an action). Below 3, skip and say so.

3. Direction. Read the page's custom properties, `font-family` and `background` declarations. It has a direction
   only when all three hold: a clear ground, light and signal colour; type the subject would use rather than a
   default (system stack, Inter alone, Instrument Serif because a model likes it); colours declared as tokens.
   When it does not, infer a brief from the title and headings (what it is, who it is for, no invented
   features), run `palette-director` for one direction, and apply it: add the `:root` tokens, switch the fonts,
   put the signal colour on the one thing to notice and nowhere else. Change no copy and no layout in this pass.

4. Texture, only when asked and only when the background is a flat fill or plain gradient. Run
   `texture-backgrounds` for the subject in the page's three colours, replace the flat fill with its code, and
   keep text on top at WCAG AA (a solid panel from the tokens beats a lightened texture).

5. Polish. Tabular numbers where numbers stack or change; touch targets of at least 44 by 44 px; no layout shift
   (image dimensions, `font-display: swap`, reserved space); loading and empty states where there is data;
   origin-aware and interruptible animation behind `prefers-reduced-motion`; `text-wrap: balance` on headings;
   body lines of 45 to 75 characters. Then the copy: shorter, more specific, no buzzwords, never a new claim;
   names, prices, legal text and code stay exactly as they are.

6. Re-audit with `design-slop-audit`; that is the "after".

Before handing anything over, confirm every `href`, `src` and `action` of the original (stylesheet and font `<link>` hrefs excepted) is still present and
no link, form, image or section was added or removed. If one is missing, fix it or start the stage again; never
deliver a page that lost a link.

## Report

Three lines, always:

```
Score 11/20 before, 2/20 after.
Biggest moves: 9 fixes (Delete filler badges, Group with spacing, Emphasize the CTA); a committed direction (#000412/#E8EEF2/#2BF08A, Fraunces); 4 polish edits.
Check by hand: the hero image still loads; open the result in a browser, confirm the signal colour sits on one element, and read the copy aloud.
```

Then the diff. Offer to write it; do not write it unasked.

## Edges

- Screenshots and URLs: audit them with `design-slop-audit`, but the moves need the source. Ask for the file.
- A page whose "slop" repeats consistently and belongs to the subject's world (a zine in halftone, a terminal
  product in mono) is deliberate. Report it as such and leave it alone.
- A CSS file has no title or headings; infer the brief from its selectors and comments, and apply direction and
  polish through declarations only.
- Never invent a claim in the copy pass. When a sentence cannot be made specific from what the page already
  says, cut it.
