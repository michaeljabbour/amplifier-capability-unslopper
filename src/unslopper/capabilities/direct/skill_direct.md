`direct` turns a short product or brand brief into a committed visual direction before any layout
is built: one concrete scene from the subject's world, three colours with roles (ground, light,
signal), a display and a body face from Google Fonts the subject would use on its own signage, one
hero image idea, and a `:root` CSS block with the tokens. It follows the four-step method from the
Unslop School palette lesson and carries its three studies as examples of commitment. Use it when a
page has no direction of its own, when a model keeps reaching for the same gradient and faces, or
before asking anything to design a page. It is model-backed and needs an agent provider with
credentials.

The library does the checking: light on ground is measured with `contrast` and must pass WCAG AA
for body text, every colour gets an OKLCH value, and a gradient between purple and blue hues in
the CSS is rejected. When a direction fails, the model is sent back once, in the same session, with
the exact direction and ratio that failed. The adjectives modern, clean, sleek and minimal are
banned from the scene; Instrument Serif, Inter and Space Grotesk are avoided unless the brief asks.

## Arguments

- `BRIEF`: the product or brand in a sentence or two. Name the world it lives in and the result is
  specific; name only a category and you get three directions to choose from. Required.
- `--directions INTEGER`: how many directions to return. Omitted, the model gives three for an open
  brief and one for a specific one. Given, exactly that many come back, each with its own scene,
  palette and type.
- `--dark-and-light`: also emit the other colour scheme in the CSS, under
  `@media (prefers-color-scheme: ...)`, redefining the same token names.
- `--agent-provider [amplifier-agent|claude]`: which agent provider to run through. The first
  installed when omitted.
- `--model TEXT`: the model to run on. Defaults to the agent provider's entry in
  `DEFAULT_INTELLIGENCE_MODELS`.
- `--reasoning-effort [low|medium|high|xhigh|max]`: how hard the model thinks. `medium` by default;
  `high` helps when a retry still fails.

```bash
unslopper direct "a mechanical watch brand lit like the aurora" --directions 1
unslopper direct "a coffee roaster" --dark-and-light --agent-provider claude
```

```python
from unslopper.lib import direct

result = direct("a silent retreat in Kyoto, golden hour on water", directions=1)
for entry in result.directions:
    print(entry.scene)
    for swatch in entry.palette:
        print(swatch.role, swatch.name, swatch.hex, swatch.oklch)
    print(entry.contrast.ratio, entry.typography.display, entry.typography.body)
    print(entry.css)
```

## Result

`DirectResult` with the `brief` as given and `directions`, a list of `Direction`:

- `scene`: one sentence, a place or a moment from the subject's world.
- `palette`: three `Color` entries in the order ground, light, signal, each with `role`, a human
  `name`, `hex` as `#RRGGBB` and `oklch` as a CSS `oklch()` value computed by the library.
- `contrast`: the `ContrastResult` for light on ground; `aa_body` is always true in a returned
  direction.
- `typography`: `display`, `body` and a one-sentence `rationale`.
- `hero`: one image idea that carries the scene in the palette, ideally the product itself.
- `css`: a `:root` block with `--ground`, `--light`, `--signal`, `--font-display` and `--font-body`,
  plus the other scheme when `--dark-and-light` was given. Paste it as it is; the tokens are the
  direction.

## Failures

- No agent provider installed, or one named that is not: the error carries the install command.
- No credentials for the agent provider: `preflight` names the variable to set.
- The model's answer fails contrast or carries a purple-to-blue gradient twice in a row: the error
  names the direction, the ratio and the remedy. Run again, raise `--reasoning-effort`, or name the
  ground and light colours in the brief.
- The model errors or times out: the error quotes the agent and suggests a different `--model`.
- An empty `BRIEF` or `--directions` below 1 fails before any model call.
