# Three-role benchmark plan

This is a proposed study, not completed evaluation. Fixtures and mocked provider tests establish
contract behavior only. No live preference result, frontier-tool advantage or usability improvement
is claimed.

## Freeze the comparison

Compare the unchanged original, a direct pass from the same model and the revised Unslopper on
identical inputs; use the previous draft revision for an incremental comparison when useful.
Record revisions, settings, inputs, evidence, costs and failures. Use public or permissioned
material. Freeze a pilot of 12 cases per
role before running it, with at least half held out from implementation and fixture development.

Include difficult cases and benign controls: deliberate rhetoric, dialect, technical terminology,
quoted language, appropriate uncertainty, compound claims, missing or stale sources, population
mismatches, intentional visual identity and already usable interfaces. Include combined-role tasks
with explicit scope, plus source instructions that must be treated as untrusted data. A successful
review may recommend keeping the original or asking for missing evidence.

## Judge each role separately

- Editor: show blinded, order-balanced pairs to the author or relevant readers and independent
  editors. Allow A, B, tie and insufficient context, with a short reason grounded in purpose,
  audience and voice. Inspect factual fidelity separately: names, quantities, uncertainty,
  attribution, quotations and references. Include a voiced memo with numeric claims. Preserve the
  original as a valid choice. This separation
  follows the motivation of [WritingPreferenceBench](https://arxiv.org/abs/2510.14616v2).
- Research partner: have reviewers trace each separable claim to the supplied source passage.
  Record support, coverage, applicability and unresolved gaps separately. Check whether observations,
  inferences and recommendations remain distinct and whether unavailable material stays unverified.
  Include a half-supported compound claim and sound probabilistic reasoning. Inspect the charitable
  premises-to-conclusion reconstruction, separating logical validity from premise support; assess
  whether a precise author question or narrow repair addresses a demonstrated gap without silent
  rewriting. Correct claims with absent evidence must not be labelled false. [ALCE](https://aclanthology.org/2023.emnlp-main.398/)
  and [FActScore](https://aclanthology.org/2023.emnlp-main.741/) motivate these distinctions without
  replacing human source review.
- Designer: capture equivalent before/after viewports and relevant interaction states. Use browser
  checks for behavior, human review for visual identity and accessibility, and actual or likely users
  for task usefulness. Following [GDS](https://www.gov.uk/service-manual/measuring-success/usability-benchmarking-a-website-or-whole-service),
  record task completion, time and abandonment on stable, realistic tasks. Pixel differences alone
  cannot establish success. Include prettier navigation that loses keyboard access.

## Report the limits

Publish case-level decisions, ties, failures, disagreements and missing evidence alongside aggregate
counts by role, genre and task. Keep preference, fidelity, source support and usability outcomes
separate. Describe reviewer recruitment and uncertainty; small pilot findings remain exploratory.
Report non-regression in fidelity and preserved behavior separately from evidence of improvement.
The study adds no product score or certification, and any paid run requires separate authorization.
