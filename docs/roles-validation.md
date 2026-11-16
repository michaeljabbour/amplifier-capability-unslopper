# Three-role extension validation

Validated 2026-11-16 against approved draft PR #3 base
`f10c52e845be18d02609ecc1d39cccb1e5d17ca0` on `feat/stop-slop-prose-20261116`.
This records the incremental role extension; `prose-validation.md` records the preceding integration.

## Inventory and implementation

The existing eleven capabilities, nine routes and seven manual skills already covered deterministic
scan/contrast/reference, model-backed copy editing and design generation. Stop-Slop supplied the
prose-preservation policy. The gap was explicit task scope, evidence-to-claim review and author-facing
reasoning comments, rather than another command or blacklist. Repository instructions and available
skill locations were inspected; no installed skills were changed.

One canonical `src/unslopper/role-contract.md` now reaches the relevant model prompts and command-help
resources. The installed router's identical reference copy is regression-checked. Existing commands
remain the entry points; no three-role CLI split, catalog duplication, new scores, badges, branding,
watermark removal or watermark-verification features were added.

- Editor: optional local JSON context supplies purpose, audience and voice for existing prose audit/edit
  commands. Exact passages, minimal edits, keep decisions and prior Stop-Slop fidelity guards remain.
- Research partner: supplied documents stay untrusted; locators are never fetched. Author comments
  separate observation/inference/recommendation, exact claim/source passages, support and applicability.
  Unavailable evidence remains unverified. Premises -> inference -> conclusion distinguish validity
  from premise support, including necessary/sufficient errors and legitimate induction. Questions and
  narrow repairs are returned to the caller without outreach. Research-only scope cannot rewrite.
  Reviewed arguments and passages awaiting an author response are retained in proposed edits.
- Designer: source/DOM evidence, captured visual state and inferred task impact remain distinct.
  Coherent monochrome/system-font identity may stay. All pipeline stages and generation retries receive
  the same scoped contract. An existing texture claim was corrected: a same-ground scrim cannot fix an
  already failing solid text/ground pair. The measured failure is disclosed without claiming rendered QA.

## Validation

- Before changes: 368 tests passed.
- After changes: 402 tests passed, including 34 added role regressions; all prior Stop-Slop fixtures pass.
- Required prek lock, lint, format and type checks passed.
- Official Smart Tool conformance: 17/17 passed using inspected runner
  `13b7e760685c1beb1f5da4bff56058ce63f8f7b8`.
- Wheel and source archive build passed. An isolated extracted wheel exercised role routing, context
  schema, command-help resources, preserved prose scan, policy and notice packaging.
- Existing site build/download/link checks and JavaScript syntax check passed without publication.

New controls include a voiced numeric memo; a half-supported compound claim; unknown, invented and
unavailable source evidence; an invalid necessary/sufficient inference and its valid twin; valid inference
with unavailable premises; calibrated probability; and intentional monochrome/system-font design.
Cross-role tests reject visual claims through prose context, preserve offline scans, enforce combined
scope and prevent research-only or author-query argument rewrites. Mocked image input checks evidence
boundaries; it does not show that a real screenshot was inspected.

## Limits and future evidence

These are deterministic or mocked-provider contract regressions. No live model comparison, blinded
preference evaluation, actual usability study or paid provider call ran. The guards establish source
anchors and scope, not truth, entailment, logical validity, author intent or semantic fidelity. A combined
editor/research pass still needs human diff review, and a model can omit a reasoning issue. The role
contract cannot turn uninspected states into evidence. Direct's existing course-constrained generation
remains separate from preserving an existing brand through audit/edit/pipeline decisions.

`roles-evidence.md` records verified primary-source guidance. `roles-benchmark.md` proposes blinded,
order-balanced comparisons of unchanged, same-model direct and Unslopper outputs, ties and insufficient
context, role-specific outcomes and non-regression judged independently from improvement. No frontier-tool
advantage is claimed.

## Exact incremental changed paths

```text
CHANGELOG.md
README.md
docs/00-vision.md
docs/01-library.md
docs/02-cli.md
docs/capabilities/audit.md
docs/capabilities/route.md
docs/capabilities/unslop.md
docs/roles-benchmark.md
docs/roles-evidence.md
docs/roles-validation.md
docs/roles.md
skills/design-antislopper/SKILL.md
skills/design-slop-audit/SKILL.md
skills/unslop-pass/SKILL.md
skills/unslopper/SKILL.md
skills/unslopper/references/role-contract.md
src/unslopper/SMART_TOOL.md
src/unslopper/capabilities/antislop/capability.py
src/unslopper/capabilities/antislop/direction.md.liquid
src/unslopper/capabilities/antislop/polish.md.liquid
src/unslopper/capabilities/audit/audit.md.liquid
src/unslopper/capabilities/audit/capability.py
src/unslopper/capabilities/audit/skill_audit.md
src/unslopper/capabilities/direct/capability.py
src/unslopper/capabilities/direct/direct.md.liquid
src/unslopper/capabilities/prose/audit.md.liquid
src/unslopper/capabilities/prose/capability.py
src/unslopper/capabilities/prose/unslop.md.liquid
src/unslopper/capabilities/route/capability.py
src/unslopper/capabilities/route/skill_route.md
src/unslopper/capabilities/texture/capability.py
src/unslopper/capabilities/texture/texture.md.liquid
src/unslopper/capabilities/unslop/capability.py
src/unslopper/capabilities/unslop/skill_unslop.md
src/unslopper/capabilities/unslop/unslop.md.liquid
src/unslopper/cli.py
src/unslopper/core/skill.py
src/unslopper/lib.py
src/unslopper/role-contract.md
src/unslopper/roles.py
src/unslopper/schemas.py
tests/fixtures/role-arguments.json
tests/test_designer_role.py
tests/test_research_role.py
tests/test_role_context.py
tests/test_texture.py
```
