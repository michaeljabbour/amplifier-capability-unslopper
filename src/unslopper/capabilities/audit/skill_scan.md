`scan` reads HTML or CSS as text and reports which of the twenty slop indicators static heuristics
can see, each with evidence a person can check: the selector or element, its line number, and the
quoted text or CSS value. No model or credentials. Network access is limited to URL input and its
eligible linked CSS. Use it as a free first pass before `unslopper audit` or to re-check candidates
after a fix. The score counts candidate indicators, not visual quality; never use it alone as a rewrite gate.

It is conservative: a false positive is worse than a miss, so slight tracking on display type,
monospace inside code, one gradient in warm colours, and a single terminal block are left alone.
What it cannot see, such as copy that restates a heading in other words or a screenshot, is the
`audit` capability's job. URL input includes same-origin linked CSS, up to 16 assets of 1 MiB each
(page limit: 4 MiB). Cross-origin, conditional, alternate, disabled and imported CSS is skipped
with reasons. Local and inline inputs stay offline and disclose unloaded linked CSS. HTML checks
use DOM context and basic cascade handling, not a browser or runtime; unsupported CSS produces warnings.

## Arguments

Exactly one of the three:

- `PATH`: an `.html`, `.htm` or `.css` file.
- `--url TEXT`: fetch HTML or CSS over http(s); HTML also gathers bounded same-origin linked CSS.
- `--source TEXT`: inline HTML or CSS; the kind is told from its shape.
- `--prose`: instead review a local `.txt`, `.md` or `.markdown` file, or inline prose from `--source`.
  URL input is rejected in this mode. No model or credentials are needed.

A `.css` file or inline stylesheet runs only the rule-based checks. Without `--prose`, plain text that is neither fails
naming what to pass instead.

```bash
unslopper scan landing.html
unslopper scan --url https://example.com
unslopper scan --source '<div class="pill">NEW</div><div class="pill">BETA</div>'
unslopper scan draft.md --prose
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
hits call for, in the course's priority order and without repeats. The legacy `verdict` is retained
for compatibility, not a visual-quality judgment. Coverage fields: `analysis_kind` is
`static_candidates`, `source_kind` is `html` or `css`, `assets` lists `url`, `status`, `reason` and
`bytes_read`, and `warnings` lists limitations. Disclose partial coverage when reporting results.
A lower count alone proves no improvement: check rendered desktop/mobile views and interactions.

With `--prose`, the result is `ProseScanReport`, not `ScanReport`: exact anchored source spans,
objective problems separated from context-sensitive review cues, `authorship: "not_assessed"` and no
score. Code, quotes and references need conservative handling; protection is incomplete. A stylistic
pattern requires contextual review and cannot establish authorship. Read `prose-quality.md` from the
skill resources for the shared policy.

## Failures

Exit 1 with the reason on stderr: no input or more than one, a path that is not a file, a URL that
could not be fetched, or, without `--prose`, text that is neither HTML nor CSS. Prose mode rejects
URL input and unsupported file types.
