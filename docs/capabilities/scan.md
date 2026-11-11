# scan

Candidate slop indicators static heuristics can see in HTML or CSS, with evidence and a count. Deterministic:
no model provider or credentials. Use before `audit` and to compare candidates before and after `unslop`.
The score is not a visual-quality grade or an automatic rewrite gate; the legacy `verdict` labels remain
for compatibility. A lower count does not prove a better design.

## Library

```python
def scan(source: str | None = None, path: Path | None = None, url: str | None = None) -> ScanReport
```

Exactly one of the three. `path` is an `.html`, `.htm` or `.css` file; `url` is fetched over http(s) and classified
as HTML or CSS; `source` is inline text whose kind is told from its shape. Inline `<style>` blocks, `style` attributes and
Google Fonts `<link>` hrefs are read. URL scans also gather same-origin linked stylesheets, bounded to 16
stylesheet occurrences (including repeated links), 16 fetch attempts and 1 MiB per asset; the page limit is 4 MiB. Cross-origin, conditional, alternate and disabled stylesheets
and `@import` dependencies are skipped with reasons. Local files and inline inputs stay offline and disclose
linked CSS that was not loaded. Source text is not rewritten to embed fetched CSS. A stylesheet alone runs
only the rule-based checks, without page context.

Returns a `ScanReport`: `source` (the path, the URL or `inline`), `score` (distinct indicators hit, 0 to 20),
`verdict` from `knowledge.verdict`, `hits` (one `ScanHit` per indicator, each with `layer`, up to eight
`Evidence` entries of `location` and `detail`, and `fix_ids`) and `fixes_first` (fix names from
`knowledge.fixes_for`, in priority order). Coverage fields are `analysis_kind` (`static_candidates`),
`source_kind` (`html` or `css`), `assets` (each with `url`, `status`, `reason`, `bytes_read`) and `warnings`.
Read these before interpreting the count: skipped or failed assets and unsupported CSS mean partial coverage.
HTML checks use DOM context and basic cascade handling to reduce candidates from absent, hidden or overridden
rules conservatively. This is not a browser cascade, runtime execution or rendered visibility check.
Supported selectors are tags, IDs, classes, descendants and children. Pseudo-classes, attribute and sibling
selectors, conditional rules, complete shorthand resets and scoped custom-property cascades need browser review.
Confirm findings in rendered desktop and mobile views and exercise interactions before claiming improvement.

Raises `UnslopperError` when no input or more than one is given, the path is not a file, the URL cannot be
fetched, or the text is neither HTML nor CSS.

The checks live in `capabilities/audit/scan.py`, one function per indicator, named after the entry in
`knowledge.INDICATORS` so layer and fixes are read from there. Each errs toward silence: slight negative tracking
on display type, monospace inside code, one warm gradient and a multi-line terminal block are left alone.

## CLI

```bash
unslopper scan [PATH] [--url TEXT] [--source TEXT]
```

Calls `lib.scan(source, path, url)` and prints the `ScanReport` as JSON. Exits 1 with the message on stderr for
any `UnslopperError`, 2 for a bad invocation.
