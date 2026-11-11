---
name: palette-director
description: >-
  Turns a short product or brand brief into a committed visual direction before any layout is built: one concrete scene, three colours with roles (ground, light, signal) that pass WCAG AA, a display and body face from Google Fonts the subject would use on its own signage, one hero image idea, and a :root block of CSS tokens. Use before asking a model to design a page, when a page has no committed visual direction, or when a product, brand or page needs its colours and type chosen for it. Triggers when a product, brand or page needs a colour palette, a visual direction, brand colours, a colour scheme, a type pairing or design tokens chosen for it.
license: MIT
metadata:
  repository: https://github.com/michaeljabbour/amplifier-capability-unslopper
  source: Unslop School, lesson 5, after Charles Liu's short videos on AI design
---

# Palette director

A generic design could belong to any product. A committed one comes from the subject's own world:
one scene, three colours pulled from it, type the subject would print on its own packaging, one
image. This skill is that method. Run it by hand, or let the tool run it for you.

## Prefer the tool

When `unslopper` is installed, use it: it runs this method through a model, measures the contrast,
computes OKLCH, rejects the purple-to-blue gradient and retries a failing direction once. Read
`unslopper direct --help` first.

```bash
unslopper direct "a mechanical watch brand lit like the aurora" --directions 1
unslopper direct "a coffee roaster"                      # open brief: three directions
unslopper direct "a coffee roaster" --dark-and-light     # both colour schemes in the CSS
unslopper contrast "#E8EEF2" "#000412"                   # check any pair yourself
```

Install it once with `uv tool install "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"`.
Without it, direct by hand below and check every light-on-ground pair against WCAG AA (4.5 to 1)
with any contrast calculator.

## The four steps

Work through them in order, for every direction. Offer three distinct directions when the brief
is open (a category, a mood, a product with no stated world) and one when it is specific.

1. **Name the feeling.** One sentence about a place or a moment from the subject's world: "aurora
   over a watch dial", "a crowd surge at a festival", "golden hour on still water". Never the words
   modern, clean, sleek or minimal; they name a feeling without committing to one.
2. **Pick three roles.** Ground covers most of the screen. Light is for text and key shapes. Signal
   covers under 10 percent of the screen and is used only for the one thing to notice. Give each a
   human name, a hex value and an OKLCH value, all pulled from the scene. Light on ground must pass
   WCAG AA for body text, 4.5 to 1; report the ratio.
3. **Let type follow.** A display face and a body face from Google Fonts that the subject would use
   on its own signage, packaging or posters, with the reason in one sentence. Avoid Instrument
   Serif, Inter and Space Grotesk unless the brief asks for them; they read as generated.
4. **One hero image.** Describe one image that carries the scene and uses the palette, ideally
   showing the product itself.

Then write the tokens: a `:root` block with `--ground`, `--light`, `--signal`, `--font-display`
and `--font-body`, and a second block under `@media (prefers-color-scheme: ...)` when the brief
needs both schemes. Never a gradient between purple and blue hues; it is the one gradient every
generated page has.

## Three studies

Fictional brands from the course. Copy their commitment, not their colours.

```text
Northern Time      a mechanical watch brand, lit like the aurora
  ground #000412   black with a trace of blue, like a night sky
  light  #E8EEF2   ice white for text and the steel case
  signal #2BF08A   aurora green, used only in the light trails
  type             a high-contrast serif with wide-tracked small caps, luxury watchmaking's own vernacular

Three Days Louder  a music festival that wants to feel like a crowd surge
  ground #C9EF35   lime, loud enough to read from across a field
  light  #111111   near-black for heavy display type
  signal #FF2E93   hot pink as confetti in the photo
  type             a fat, chunky display face set huge and tight, poster style

Still Waters       a silent retreat in Kyoto, golden hour on water
  ground #603E1E   brown, warm and low like wood
  light  #F1D9A8   pale gold for quiet text
  signal #FFC34D   glowing gold as light rays on the heron
  type             a refined serif with generous tracking and lots of air
```

Two of these use italics, wide-tracked caps and serif display faces, which an audit would flag.
They work because every choice belongs to the brand's world and repeats with discipline. That is
the test for any direction you write.

## Worked example

Brief: "a mechanical watch brand lit like the aurora". Specific, so one direction.

```text
Scene    Aurora over a watch dial at 2 a.m., steel catching the green.
Ground   night sky      #000412   oklch(11.0% 0.039 257.1)
Light    ice white      #E8EEF2   oklch(94.6% 0.008 236.6)
Signal   aurora green   #2BF08A   oklch(84.2% 0.204 153.8)
Contrast light on ground 17.49 to 1, passes AA and AAA
Type     Cormorant Garamond for display, Source Serif 4 for body: watchmakers set their own name in a high-contrast serif
Hero     The watch face lit from one side, a single green trail across the crystal
```

```css
:root {
  --ground: #000412;
  --light: #E8EEF2;
  --signal: #2BF08A;
  --font-display: "Cormorant Garamond", Georgia, serif;
  --font-body: "Source Serif 4", Georgia, serif;
}
```

## Hand it on

Give the direction to whatever builds the page as the tokens plus the scene sentence. A model that
receives `--ground`, `--light` and `--signal` by name, and a sentence about where they came from,
stops reaching for its defaults.
