# reference

The course material as data. Deterministic.

```python
def reference(topic: Topic, name: str | None = None) -> ReferenceResult
```

- `topic`: `terms`, `indicators`, `fixes`, `textures` or `palettes`.
- `name`: only the entry whose name matches, case-insensitively and by substring. Raises `UnslopperError` naming every entry when nothing matches.

Returns `ReferenceResult(topic, items)`; items are `Term`, `Indicator`, `Fix`, `Texture` or `PaletteStudy` from `unslopper.schemas`.

```bash
unslopper reference TOPIC [--name TEXT]
```

Prints the result as JSON. Exit 1 when `--name` matches nothing, 2 for an unknown topic.
