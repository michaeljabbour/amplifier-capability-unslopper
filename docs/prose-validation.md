# Prose integration validation

Validated 2026-11-16 on `feat/stop-slop-prose-20261116`, based on main
`bb8bba498e061958b011a3340efd2742395dc9cc`. Version stays 0.2.0; this is an unreleased proposal.

## Result

Existing `scan`, `audit` and `unslop` expose explicit `--prose` / `prose=True` for local text and
Markdown. The deterministic report anchors each finding to the original text and separates mechanical
observations from editorial review cues, with no quality score or AI probability. Model review/editing
uses the existing Intelligence interface. Design audit, fixing and pipeline polish share one prose policy.

The Stop-Slop material is pinned, adapted selectively and credited in full MIT notices. Its blanket
style bans, invented examples and claim-strengthening rewrites are excluded. No installed skills were
replaced, no unrelated local work was changed, and no merge, deployment or release was performed.

## Checks

- Before edits: `uv run --frozen pytest -q`, 294 passed; all required prek checks passed.
- After edits: `uv run --frozen pytest -q`, 368 passed, including 74 added regressions.
- `uv tool run prek run --all-files`: lock, lint, formatting and type checks passed.
- Official Smart Tool conformance: 17/17 passed using inspected runner at
  `microsoft/amplifier-smart-tools` commit `13b7e760685c1beb1f5da4bff56058ce63f8f7b8`.
- `uv build --no-sources`: wheel and source archive built. An isolated extracted-wheel smoke test
  confirmed prose scanning, installed command-help bodies, shared policy, prompts and MIT notices.
- Existing site-build/download/link checks and all skill/manifest/version tests pass in the suite.
  The seven skill versions, package and manifest remain synchronized at 0.2.0.

## Identical-sample comparison

`docs/prose-comparison.json` records all rows and source/fixture fingerprints. Reproduce with:

```bash
uv run --frozen python scripts/compare_prose.py --baseline /path/to/main-checkout --output /tmp/prose-comparison.json
```

The same 12 paired synthetic cases (24 samples) ran through each checkout's real library facade.
Main has no prose mode and rejects all 24 as unsupported input; those are not detector misses.
The feature supports all 24 and matches all 24 fixture expectations: 12 targeted samples produce
14 review candidates; none of the 12 legitimate twins is flagged. These are narrow editorial
regressions, not a general accuracy or writing-quality estimate.

Tests also cover legitimate technical terms, dialect, calibrated scientific claims, deliberate
rhetoric, multiline/lazy quotations, contractions, citations, references and code. Mocked audits
exercise keep/uncertain decisions and exact evidence validation. Mocked edits exercise dry runs,
requested writes, newline preservation, concurrent source changes and rejection of altered protected
material, numbers, calibration or retained audit evidence. Changed CLI and provider-option paths
are covered without live model calls.

## Limits

No live model comparison was authorized or run, no private writing was submitted to an external
service, and no paid API was called. Mocked provider tests establish contracts, not rewrite quality.
Markdown and citation parsing is conservative and partial; the English phrase rules miss many possible
problems. Mechanical token/span guards can reject legitimate edits and cannot verify all names, units,
relationships, attribution, factual truth, semantic equivalence or author voice. Human diff review is
still needed. Fewer cues is not a quality target and stylistic evidence does not establish authorship.

See `docs/prose-evidence.md` for verified research, industry distinctions and the proposed blinded,
genre-aware evaluation with separate fidelity judgments and ties.

## Exact changed paths

```text
CHANGELOG.md
README.md
THIRD_PARTY_NOTICES.md
docs/00-vision.md
docs/01-library.md
docs/02-cli.md
docs/capabilities/audit.md
docs/capabilities/scan.md
docs/capabilities/unslop.md
docs/prose-comparison.json
docs/prose-evidence.md
docs/prose-validation.md
pyproject.toml
scripts/compare_prose.py
skills/design-antislopper/SKILL.md
skills/design-antislopper/THIRD_PARTY_NOTICES.md
skills/design-slop-audit/SKILL.md
skills/design-slop-audit/THIRD_PARTY_NOTICES.md
skills/unslop-pass/SKILL.md
skills/unslop-pass/THIRD_PARTY_NOTICES.md
skills/unslopper/SKILL.md
skills/unslopper/THIRD_PARTY_NOTICES.md
src/unslopper/SMART_TOOL.md
src/unslopper/THIRD_PARTY_NOTICES.md
src/unslopper/capabilities/antislop/capability.py
src/unslopper/capabilities/antislop/polish.md.liquid
src/unslopper/capabilities/audit/audit.md.liquid
src/unslopper/capabilities/audit/capability.py
src/unslopper/capabilities/audit/skill_audit.md
src/unslopper/capabilities/audit/skill_scan.md
src/unslopper/capabilities/prose/__init__.py
src/unslopper/capabilities/prose/audit.md.liquid
src/unslopper/capabilities/prose/capability.py
src/unslopper/capabilities/prose/unslop.md.liquid
src/unslopper/capabilities/route/capability.py
src/unslopper/capabilities/unslop/capability.py
src/unslopper/capabilities/unslop/skill_unslop.md
src/unslopper/capabilities/unslop/unslop.md.liquid
src/unslopper/cli.py
src/unslopper/core/skill.py
src/unslopper/lib.py
src/unslopper/prose-quality.md
src/unslopper/prose.py
src/unslopper/schemas.py
tests/fixtures/prose-pairs.json
tests/test_prose.py
tests/test_prose_integration.py
```
