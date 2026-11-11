`texture` replaces a flat fill or a purple gradient with a background from the subject's world,
as self-contained code under 3 KB that keeps text on top at WCAG AA. It knows the course's
twenty-two textures (`unslopper reference textures` lists them). Given a subject, it recommends
two or three that fit and says why, then draws the first; given a name, it draws that one. One
model call, no workspace, checked in code afterwards: size, no motion unless asked, no external
resources, `kind` agreeing with the code, and light-on-ground contrast measured. A failing
answer is sent back once with the failures named.

## Arguments

- `--name TEXT`: the texture to draw, matched case-insensitively or by substring (`blueprint`,
  `paper`). Fails naming all twenty-two when nothing matches, or the matches when several do.
  Omitted, the model recommends from the subject and draws its first pick.
- `--subject TEXT`: what the design is for, in a phrase: `a developer tools landing page`,
  `a small press publishing poetry`. The texture comes from this world. Required when no palette
  is given; without it the model has nothing to propose a palette from.
- `--ground HEX`, `--light HEX`, `--signal HEX`: the palette, all three together or none.
  `ground` is the background the texture is drawn in, `light` the text colour that will sit on
  it, `signal` the accent. `#RGB` or `#RRGGBB`. Omitted, the model proposes a palette from the
  subject and it is returned normalized.
- `--animated`: allow slow motion, wrapped in `@media (prefers-reduced-motion: no-preference)`.
  Off by default, and then any `@keyframes`, `animation`, `transition` or
  `requestAnimationFrame` in the answer is rejected.
- `--agent-provider`, `--model`, `--reasoning-effort`: the model-backed options. `medium`
  effort is enough; the code is small.

```bash
unslopper texture --name blueprint --subject "a developer tools landing page" \
  --ground "#1C4E8A" --light "#F5F7FA" --signal "#FFB020"
unslopper texture --subject "a small press publishing poetry"
unslopper texture --name "water ripples" --subject "a sleep app" \
  --ground "#0B2A3A" --light "#E6F2F5" --signal "#7FD3C9" --animated --agent-provider claude
```

```python
from unslopper.lib import texture

result = texture(name="paper", subject="a small press", ground="#EFE8D9", light="#2B2118", signal="#C0392B")
print(result.kind, result.size_bytes)
print(result.code)
```

## Using the code

When `kind` is `css`, `code` is a rule set on the selector `.texture`: paste it into a
stylesheet and give the container the class. Pure CSS, gradients and inline SVG noise as a
`data:` URI only, so it needs no files and resizes with the element. When `kind` is `canvas`,
`code` is a `<canvas class="texture">` plus a `<script>` with its own seeded random: paste it
where the background goes and position it behind the content; it draws the same every load.
Set text in `palette.light`, and do what `contrast` says when it names a scrim.

## Result

`TextureResult`: `palette` (`ground`, `light`, `signal` as `#RRGGBB`, the given one or the one
proposed); `recommendations`, two or three `{name, why}` with the drawn one first; `texture`,
the catalog name drawn; `kind`, `css` or `canvas`; `code`; `size_bytes`, under 3072;
`contrast`, how text in `light` stays at WCAG AA on the texture, with a scrim or adjustment
added when light on ground alone measures under 4.5 to 1; `warning`, null unless the texture
drawn is dithering, ASCII or a gradient with no link to the subject, in which case one sentence
says it reads as an AI default and names what to use instead. Dithering, ASCII and gradients are
in the catalog on purpose: craft when chosen for the subject, slop when the model chose them.

## Failures

Each raises `UnslopperError` (exit 1) naming the remedy: a palette with one or two of the three
colours; neither palette nor subject; a value that is not a hex colour; a `--name` that matches
no texture or several; a missing agent provider or credentials; a model run that errored; an
answer that still fails its checks after the one retry, naming which check (size, motion,
external resource, kind, texture, recommendations, inferred palette).
