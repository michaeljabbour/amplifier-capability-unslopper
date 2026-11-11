# contrast

WCAG 2 contrast between two hex colours and the levels it passes. Deterministic: no agent provider, no network.
`direct` runs it on every direction's light-on-ground pair; call it directly when you already hold the colours.

## Library

```python
def contrast(foreground: str, background: str) -> ContrastResult
```

- `foreground`, `background`: `#RGB` or `#RRGGBB`, with or without the hash. The order does not change the ratio, only which colour is reported under which name.

Returns `ContrastResult`: `foreground` and `background` normalized to `#RRGGBB`, `ratio` from 1.0 to 21.0 rounded to two decimals, and `aa_body` (4.5 or more), `aa_large` (3 or more), `aaa_body` (7 or more).

Raises `UnslopperError` when a value is not a hex colour, naming the shape wanted. Named colours, `rgb()` and `oklch()` are not parsed.

The maths lives in `unslopper.color`, which also exposes `contrast_ratio`, `relative_luminance`, `normalize_hex` and `to_oklch` for callers that want the numbers without the result model.

## CLI

```bash
unslopper contrast FOREGROUND BACKGROUND
```

`lib.contrast(foreground, background)`, printed as JSON. A bad hex prints the error to stderr and exits 1.

```bash
unslopper contrast "#E8EEF2" "#000412"
```

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
