# direct

Turns a brief into a committed visual direction: one concrete scene, three colours with roles, a type pairing from Google Fonts, a hero image idea and a `:root` block of CSS tokens. Model-backed.

The method is lesson 5 of the course: name the feeling as a scene, pick ground, light and signal, let type follow, choose one hero image. The prompt carries the three palette studies from `knowledge.py` as examples of commitment, bans `BANNED_ADJECTIVES` from the scene and steers away from `DEFAULT_FACES` unless the brief asks for them.

## Library

```python
def direct(
    brief: str,
    directions: int | None = None,
    dark_and_light: bool = False,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> DirectResult
```

- `brief`: the product or brand in a sentence or two. A named world gives a specific direction; a bare category gives three.
- `directions`: `None` lets the model decide, three for an open brief and one for a specific one. A number asks for exactly that many, each with its own scene, palette and type.
- `dark_and_light`: also emit the other colour scheme in the CSS under `@media (prefers-color-scheme: ...)`, redefining the same token names.
- `agent_provider`, `model`, `reasoning_effort`, `intelligence`: as every model-backed capability; see [Intelligence](../01-library.md#intelligence).

Returns `DirectResult` with the `brief` and `directions`, a list of `Direction`:

- `scene`: one sentence, a place or a moment from the subject's world.
- `palette`: three `Color` entries, ground then light then signal, each with `role`, `name`, `hex` as `#RRGGBB` and `oklch` computed by `unslopper.color.to_oklch`.
- `contrast`: `ContrastResult` for light on ground, computed by `unslopper.color.contrast`; `aa_body` is true in every returned direction.
- `typography`: `display`, `body`, one-sentence `rationale`.
- `hero`: one image idea in the palette, ideally the product.
- `css`: a `:root` block with `--ground`, `--light`, `--signal`, `--font-display`, `--font-body`, plus the variant when asked for.

One plain completion with structured output, no workspace. The model answers hex and names only; the library normalizes the hex, computes OKLCH and contrast, and checks the CSS for a gradient between purple and blue hues. When any direction fails contrast, lacks a `:root` block, carries that gradient, or the count is wrong, the model is sent back once in the same session with the failures named. Both prompts are Liquid templates beside the code: `direct.md.liquid` and `retry.md.liquid`.

Raises `UnslopperError`:

- when the brief is empty or `directions` is below 1, before any model call;
- when no agent provider is installed or the named one has no credentials, with the install command or the variable to set;
- when the model errors or times out, quoting the agent;
- when a direction still fails after the retry, naming the direction, the ratio against 4.5 to 1, and the remedy.

## CLI

```bash
unslopper direct BRIEF [--directions INTEGER] [--dark-and-light]
                 [--agent-provider amplifier-agent|claude] [--model TEXT]
                 [--reasoning-effort low|medium|high|xhigh|max]
```

`lib.direct(brief, directions, dark_and_light, agent_provider, model, reasoning_effort)`, printed as JSON. A failure the library names prints to stderr and exits 1.

```bash
unslopper direct "a mechanical watch brand lit like the aurora" --directions 1
unslopper direct "a coffee roaster" --dark-and-light --agent-provider claude
```
