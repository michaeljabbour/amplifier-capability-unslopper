# scan

The slop indicators static heuristics can see in HTML or CSS, with evidence and a score. Deterministic: no model
provider, no credentials. The cheap first pass before `audit`, and the before-and-after measure `unslop` uses.

## Library

```python
def scan(source: str | None = None, path: Path | None = None, url: str | None = None) -> ScanReport
```

Exactly one of the three. `path` is an `.html`, `.htm` or `.css` file; `url` is fetched over http(s) and read as
HTML; `source` is inline text whose kind is told from its shape. Inline `<style>` blocks, `style` attributes and
Google Fonts `<link>` hrefs are read; external stylesheets are not fetched. A stylesheet runs only the rule-based
checks.

Returns a `ScanReport`: `source` (the path, the URL or `inline`), `score` (distinct indicators hit, 0 to 20),
`verdict` from `knowledge.verdict`, `hits` (one `ScanHit` per indicator, each with `layer`, up to eight
`Evidence` entries of `location` and `detail`, and `fix_ids`) and `fixes_first` (fix names from
`knowledge.fixes_for`, in priority order).

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
