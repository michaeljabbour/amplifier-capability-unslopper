`scan` reads HTML or CSS as text and reports which of the twenty slop indicators static heuristics
can see, each with evidence a person can check: the selector or element, its line number, and the
quoted text or CSS value. No model, no credentials, no network beyond fetching `--url`. Use it as a
free first pass before `unslopper audit`, as a gate in a script, or to re-check a file after a fix.

It is conservative: a false positive is worse than a miss, so slight tracking on display type,
monospace inside code, one gradient in warm colours, and a single terminal block are left alone.
What it cannot see, such as copy that restates a heading in other words or a screenshot, is the
`audit` capability's job. Only inline `<style>` blocks, `style` attributes and Google Fonts
`<link>` hrefs are read; external stylesheets are not fetched.

## Arguments

Exactly one of the three:

- `PATH`: an `.html`, `.htm` or `.css` file.
- `--url TEXT`: fetch a page over http(s) and scan its HTML.
- `--source TEXT`: inline HTML or CSS; the kind is told from its shape.

A `.css` file or inline stylesheet runs only the rule-based checks. Plain text that is neither fails
naming what to pass instead.

```bash
unslopper scan landing.html
unslopper scan --url https://example.com
unslopper scan --source '<div class="pill">NEW</div><div class="pill">BETA</div>'
```

```python
from pathlib import Path

from unslopper.lib import scan

report = scan(path=Path("landing.html"))
print(report.score, report.verdict)
for hit in report.hits:
    print(hit.indicator, hit.evidence[0].location, hit.evidence[0].detail)
```

## Result

`ScanReport` as JSON: `source` (the path, the URL or `inline`), `score` (distinct indicators hit, out
of 20), `verdict` (the course's reading of that count), `hits` and `fixes_first`. Each hit is a
`ScanHit` with `indicator`, `layer` (Type, Surface, Structure or Content), `evidence` (up to eight
`Evidence` entries with `location` and `detail`) and `fix_ids`. `fixes_first` lists the fix names the
hits call for, in the course's priority order and without repeats.

## Failures

Exit 1 with the reason on stderr: no input or more than one, a path that is not a file, a URL that
could not be fetched, or text that is neither HTML nor CSS.
