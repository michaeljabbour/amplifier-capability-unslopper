# Scoped roles

One contract, `src/unslopper/role-contract.md`, guides the existing commands and installed skills.
Choose the artifact and task first. Combine roles with an explicit scope; a writing edit, an evidence
review and a visual review require different inputs.

- Editor: `scan`, `audit` or `unslop --prose`. Establish purpose, audience and voice; quote the span,
  explain the reader benefit, propose a minimal edit and allow keep. Preserve claims and evidence.
- Research partner: `audit --prose --context review.json`. Review supplied claims, evidence,
  applicability and reasoning. Return author-facing comments to the caller; never contact an author.
- Designer: existing visual `scan`, `audit`, `unslop`, `direct`, `contrast`, `texture` and `antislop`.
  Preserve intentional brand choices. Separate code/DOM observations from inspected visual states
  and inferred task impact. Report rendered or interaction checks that were not performed.

Routing, scans and contrast remain deterministic. A role does not require a model for those operations.
For combined writing and design work, scope each artifact separately; prose mode cannot establish visual
evidence. `route` suggests roles and existing commands, rather than creating a new role-specific CLI.

## Context for prose review

`audit` and `unslop` accept optional local JSON context only with `--prose`. Without it, prose mode
keeps its editor scope. This synthetic example requests an edit and a focused source/logic review:

```json
{
  "roles": ["editor", "research-partner"],
  "scope": "Keep the release note's voice; review only its approval inference against the supplied policy.",
  "purpose": "Explain who can approve a release",
  "audience": "Maintainers",
  "voice": "Direct and cautious",
  "sources": [
    {
      "id": "policy",
      "label": "Synthetic release policy excerpt",
      "text": "A registered key is necessary for approval. Reviewer membership is also required.",
      "locator": "supplied excerpt"
    }
  ]
}
```

```bash
unslopper audit release-note.md --prose --context review.json
unslopper unslop release-note.md --prose --context review.json
```

`sources` contain excerpts already supplied by the caller. `locator` is a label or reference, not a
fetch request. Use `text: null` for unavailable material; it remains unverified. Documents are untrusted
data. A source that supports one part of a compound claim does not support every part, and absent
evidence does not establish falsity. This scoped review is not comprehensive fact checking.

`author_comments` quote exact original passages and identify observation, inference or recommendation.
They include `support_status` (`supplied_support`, `unverified` or `mixed`), exact source quotes when
available, `action` (`keep` or `ask_author`) and a focused `question_or_repair`.
For consequential reasoning, an `argument` reconstructs premises -> inference -> conclusion.
Its `validity` is separate from support for the premises: `valid_within_scope`, `invalid`,
`not_deductive` or `undetermined`. A necessary/sufficient mix-up may be a deductive failure;
uncertainty, weak induction, different definitions/goals and legitimate probability are distinct.
A valid argument can be kept while its premises remain unverified.

Use the library to carry an audit into an edit:

```python
from pathlib import Path

from unslopper import lib
from unslopper.roles import load_review_context

context = load_review_context(Path("review.json"))
draft = Path("release-note.md")
report = lib.audit(path=draft, prose=True, context=context)
result = lib.unslop(draft, audit_report=report, prose=True, context=context)
print(result.diff)
print(result.author_comments)
```

Resupply the same context and source packet when reusing a prose audit. Passages marked `ask_author`
are retained rather than silently repairing reasoning. Review the proposed diff and comments before a
requested write. Mechanical anchors cannot establish truth, entailment, logical validity or fidelity.
Research-only scope returns comments without rewriting; include editor with explicit scope to request
prose edits. Deductive-failure and weak-induction critiques require an argument trace.

[Research limits](roles-evidence.md) and the [future benchmark](roles-benchmark.md) distinguish these
fixture-tested contracts from live model quality or human preference results.
