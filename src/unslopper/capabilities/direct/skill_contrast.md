`contrast` gives the WCAG 2 contrast ratio between two hex colours and which levels it passes:
AA for body text (4.5 to 1), AA for large text (3 to 1) and AAA for body text (7 to 1). Deterministic
and needs no credentials. Use it to check a text colour on a background before committing to it, to
verify the `light` on `ground` pair of a direction, or to answer "does this grey pass" without guessing.
`direct` runs the same check itself, so call this when you already have the colours.

## Arguments

- `FOREGROUND`: the text colour as hex, `#RGB` or `#RRGGBB`, with or without the hash. Required.
- `BACKGROUND`: the ground colour as hex, same forms. Required.

The order does not change the ratio; it only decides which colour is reported as `foreground`.

```bash
unslopper contrast "#E8EEF2" "#000412"
unslopper contrast 767676 ffffff
```

```python
from unslopper.lib import contrast

result = contrast("#E8EEF2", "#000412")
if not result.aa_body:
    print(f"{result.ratio} to 1 fails AA body text; lighten the text or darken the ground")
```

## Result

`ContrastResult` with `foreground` and `background` normalized to `#RRGGBB`, `ratio` from 1.0 to 21.0
rounded to two decimals, and the flags `aa_body` (4.5 or more), `aa_large` (3 or more) and
`aaa_body` (7 or more).

```json
{
  "foreground": "#E8EEF2",
  "background": "#000412",
  "ratio": 17.49,
  "aa_body": true,
  "aa_large": true,
  "aaa_body": true
}
```

## Failures

A value that is not a hex colour fails before any maths, naming the shape wanted
(`'navy' is not a hex colour. Use #RGB or #RRGGBB, like #2BF08A.`). Named CSS colours, `rgb()` and
`oklch()` are not accepted: convert them to hex first.
