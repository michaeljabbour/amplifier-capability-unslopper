# Skill security scans

Every Agent Skill under `skills/` is scanned with NVIDIA's
[SkillSpector](https://github.com/NVIDIA/skillspector) before it is published, with both the
static analyzers and the semantic (model-backed) analyzer enabled. The reports here are the
output of the scan on the date in the file name, with the absolute checkout path replaced by `.` and nothing else changed. Rerun it from the repository root:

```bash
uv tool install 'skillspector[mcp] @ git+https://github.com/NVIDIA/skillspector.git'
SKILLSPECTOR_PROVIDER=anthropic skillspector scan skills/ --recursive --format markdown --output docs/security/skillspector-$(date -u +%F).md
```

## 2026-11-10

Seven skills, all rated SAFE. What the scan found during the build and what changed:

- An "anti-refusal" hit on the phrase "No warning:" in texture-backgrounds, which described the
  result's empty `warning` field. Reworded.
- An unpinned `npx skills` update command and an instruction to keep tools up to date by default
  in the router skill, flagged as a rug-pull and output-handling risk, then as self-modification
  after a first rewrite. The skill now compares versions, tells the user, and upgrades only when
  they agree; it no longer updates itself.
- Vague trigger phrases in five skills ("slop", "palette", "background", "quiz me" and the like).
  Each trigger list now names design-specific phrases.

The final scan, saved here as the dated JSON and Markdown reports, reports zero findings and a
score of 0 of 100 for every skill. Earlier passes had raised LOW and MEDIUM notes about broad
trigger phrases and about skills that run the `unslopper` CLI; the wording above resolved them.
Two tiny later edits to unslop-pass and design-antislopper (naming the stylesheet-link exception to
the link check) were re-checked with the static analyzers only.
