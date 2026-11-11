# texture

Recommends textures for a subject from the course's twenty-two and generates one as self-contained CSS or canvas code in a palette, under 3 KB, with text contrast checked. Model-backed.

The method is lesson 6 of the course: flat fills read as unfinished and a purple gradient reads as AI, so the background comes from the subject's world instead (blueprint grid for engineering, paper for publishing, felt for games). The prompt carries `knowledge.TEXTURES` with each texture's use and the course's own canvas drawing of the relevant textures from `textures-reference.md`, as a reference for the look.

## Library

```python
def texture(
    name: str | None = None,
    subject: str | None = None,
    ground: str | None = None,
    light: str | None = None,
    signal: str | None = None,
    animated: bool = False,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> TextureResult
```

- `name`: the texture to draw, matched against `knowledge.TEXTURES` case-insensitively or by substring. `None` lets the model recommend two or three for the subject and draw the first.
- `subject`: what the design is for, in a phrase. Required when no palette is given.
- `ground`, `light`, `signal`: the palette, all three or none, as `#RGB` or `#RRGGBB`. With none, the model proposes one from the subject.
- `animated`: allow motion. Off, the code may not contain `@keyframes`, `animation`, `transition` or `requestAnimationFrame`; on, motion sits inside `@media (prefers-reduced-motion: no-preference)`.
- `agent_provider`, `model`, `reasoning_effort`, `intelligence`: as every model-backed capability; see [Intelligence](../01-library.md#intelligence).

Returns `TextureResult`:

- `palette`: `Palette` with `ground`, `light`, `signal` normalized to `#RRGGBB`, the given one or the proposed one.
- `recommendations`: two or three `TextureRecommendation` (`name`, `why`), the drawn texture first.
- `texture`: the catalog name of the texture drawn.
- `kind`: `css`, a rule set on `.texture` built from gradients and SVG feTurbulence noise as a `data:` URI; or `canvas`, a `<canvas class="texture">` and a `<script>` with its own seeded random.
- `code`, `size_bytes`: the code and its length in bytes, under 3072.
- `contrast`: how text in `light` stays at WCAG AA on the texture. `unslopper.color.contrast(light, ground)` is measured in code; when it fails 4.5 to 1 and the model's note names no scrim or adjustment, one is appended.
- `warning`: `None`, or one sentence when the texture drawn is dithering, ASCII or a gradient with no link to the subject, which the course counts as an AI default.

One plain completion with structured output, no workspace, from the Liquid template `texture.md.liquid` beside the code. The answer is checked in code: size, motion when not allowed, `http(s)` or `url()` to anything but a `data:` URI (the SVG namespace excepted), `kind` against the code (`css` carries no `<script>` or `<canvas>`, `canvas` carries a `<script>`), the drawn texture against the catalog and the requested name, the first recommendation against the drawn texture, and the inferred palette when none was given. On any failure the model is sent back once in the same session with the failures named.

Raises `UnslopperError`:

- when one or two of the three palette colours are given, when neither a palette nor a subject is given, or when a colour is not hex, before any model call;
- when `name` matches no texture, naming the twenty-two, or several, naming them;
- when the agent provider is missing or its preflight fails, when the run errors, or when the answer still fails a check after the retry, naming the check.

## CLI

```bash
unslopper texture [--name TEXT] [--subject TEXT] [--ground HEX --light HEX --signal HEX] [--animated]
                  [--agent-provider amplifier-agent|claude] [--model TEXT] [--reasoning-effort low|medium|high|xhigh|max]
```

`lib.texture(name, subject, ground, light, signal, animated, agent_provider, model, reasoning_effort)`, printed as JSON. A failure the library names prints to stderr and exits 1.

```bash
unslopper texture --name blueprint --subject "a developer tools landing page" --ground "#1C4E8A" --light "#F5F7FA" --signal "#FFB020"
unslopper texture --subject "a small press publishing poetry" --agent-provider claude
```
