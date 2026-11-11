---
name: texture-backgrounds
description: >-
  Replaces a flat fill or a purple gradient with a textured background from the subject's own world, as self-contained CSS or a small seeded canvas script in the design's palette, under 3 KB, with text on top kept at WCAG AA. Knows the course's twenty-two textures (felt, fluted glass, blueprint grids, paper, halftone, contour lines, water ripples and the rest), recommends two or three for a subject and says why, and warns when dithering, ASCII or a gradient is used as decoration. Use when a page background is flat, when a design shows the purple-to-blue gradient, when someone asks for a background texture, grain, noise, pattern or a textured hero. Triggers on "background texture", "textured background", "grainy gradient", "noise texture", "background pattern".
license: MIT
metadata:
  repository: https://github.com/michaeljabbour/amplifier-capability-unslopper
  source: Unslop School, lesson 6, after Charles Liu's short videos on AI design
---

# Texture backgrounds

Flat fills read as unfinished and a purple gradient reads as AI. Texture is the middle path, and
it works when it comes from the subject's world: a blueprint grid for engineering, paper for
publishing, felt for games. This skill is that method. Run it by hand, or let the tool run it.

## Prefer the tool

When `unslopper` is installed, use it: it recommends from the catalog, generates the code through
a model, measures light-on-ground contrast, checks the size, motion, external references and
code kind, and retries a failing answer once. Read `unslopper texture --help` first.

```bash
unslopper texture --name blueprint --subject "a developer tools landing page" \
  --ground "#1C4E8A" --light "#F5F7FA" --signal "#FFB020"
unslopper texture --subject "a small press publishing poetry"      # recommends, proposes a palette, draws the first
unslopper reference textures                                        # the catalog as JSON
```

Install it once with `uv tool install "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"`.
Without it, work through the steps below; `references/textures.md` carries the catalog and the
course's canvas code for every texture.

## The five steps

1. **Get the palette.** Ask for ground, light and signal, or infer them from the subject: ground
   is the background the texture is drawn in, light is the text colour that will sit on it, signal
   is the accent. Check light on ground passes WCAG AA, 4.5 to 1, with any contrast calculator.
2. **Recommend two or three textures.** Pick from the catalog in `references/textures.md` by the
   subject's world, not by taste, and say why in one sentence each. Engineering and hardware get
   blueprint grids or square-dot grids; publishing gets paper; games and kids get felt or pixel
   mosaics; wellness and travel get water ripples or cloud sky; finance and tools get speckled
   graphite; outdoors gets contour lines, grass or single-hue landscapes; beauty gets iridescent
   shapes; food and hospitality get impressionist brushwork; print and zines get halftone.
3. **Generate the code.** Prefer pure CSS on one selector: layered and repeating gradients, and
   SVG noise as a `data:image/svg+xml` URI with `feTurbulence`. Fall back to a small canvas script
   with its own seeded random only for what CSS cannot draw (brush strokes, grass blades, felt
   fibres), so it draws the same every load. No external images, fonts or scripts.
4. **Keep the text readable.** Text in the light colour sits on top. Keep the texture's marks close
   to the ground's lightness so the measured contrast holds; otherwise add a scrim of the ground
   colour at 85 percent or more behind the text, or lower the texture's contrast, and say which.
5. **Keep it light.** Under 3 KB of code. No animation unless asked, and then slow and inside
   `@media (prefers-reduced-motion: no-preference)`.

## The warning

Dithering, ASCII art and gradients are in the catalog and in the course's list of slop
indicators. Both are right: a technique is craft when chosen for the subject and slop when the
model chose it. A dithered hero for a retro games studio is a choice; a dithered hero for a law
firm is a default. When the request is dithering, ASCII or a gradient and nothing in the subject
calls for it, say that it reads as an AI default and name the texture from the subject's world
to use instead.

## Worked example

Subject: a developer tools landing page. Palette: ground `#1C4E8A`, light `#F5F7FA`, signal
`#FFB020`. Light on ground measures 10.9 to 1, passes AA and AAA.

Recommendations: Blueprint grids, because engineering drawings are what developer tools come
from; Square-dot grids as a quieter technical ground for the docs pages; Speckled graphite for a
darker, more serious variant.

```css
.texture {
  background-color: #1C4E8A;
  background-image:
    linear-gradient(rgba(245,247,250,.35) 1px, transparent 1px),
    linear-gradient(90deg, rgba(245,247,250,.35) 1px, transparent 1px),
    linear-gradient(rgba(245,247,250,.12) 1px, transparent 1px),
    linear-gradient(90deg, rgba(245,247,250,.12) 1px, transparent 1px);
  background-size: 50px 50px, 50px 50px, 10px 10px, 10px 10px;
}
```

Contrast: the lines are the light colour at 12 and 35 percent, so the ground stays dark behind
`#F5F7FA` text; no scrim needed. 420 bytes, pure CSS, no motion. The warning field stays empty,
because a blueprint grid is the subject's own material.

## Hand it on

Give whatever builds the page the code, the selector it targets, the text colour to use on it
and the contrast note. A model that receives a named texture and a reason stops reaching for the
gradient.
