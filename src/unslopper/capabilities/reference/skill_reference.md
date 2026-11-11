`reference` prints the course material the other capabilities reason from, as JSON: the twenty
design terms, the twenty slop indicators with the fixes each calls for, the twenty fixes grouped
into four moves, the twenty-two background textures, or the three palette studies. Deterministic
and needs no credentials, so it is the cheapest way to look a term up or to hand an agent the
vocabulary before it designs anything.

## Arguments

- `TOPIC`: one of `terms`, `indicators`, `fixes`, `textures`, `palettes`. Required.
- `--name TEXT`: return only the entry whose name matches, case-insensitively and by substring.
  Fails naming every entry when nothing matches.

```bash
unslopper reference indicators
unslopper reference terms --name "tabular"
unslopper reference fixes --name "radius"
```

```python
from unslopper.lib import reference

fixes = reference("fixes")
for fix in fixes.items:
    print(fix.id, fix.move, fix.name)
```

## Result

`ReferenceResult` with `topic` and `items`. Items are `Term` (`name`, `meaning`, `ai_note`),
`Indicator` (`name`, `layer`, `description`, `fix_ids`), `Fix` (`id`, `name`, `how`, `move`),
`Texture` (`name`, `use`) or `PaletteStudy` (`name`, `mood`, `swatches`, `typography`).
