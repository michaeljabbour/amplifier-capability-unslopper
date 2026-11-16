# Evidence for the three roles

Reviewed 2026-11-16. These sources inform bounded design principles for the editor, research partner
and designer. They do not establish that Unslopper outperforms frontier tools. The role contract
uses the existing commands and preserves the Stop-Slop safeguards.

## Editor

[Chakrabarty et al. (COLM 2025)](https://proceedings.colm.cc/paper_files/paper/2025/hash/ec3c79dc0c2b85532cfd1012a4aaa923-Abstract-Conference.html)
study writing-quality judgments and selection among candidate revisions, including evaluation by
experienced writers. [WritingPreferenceBench](https://arxiv.org/abs/2510.14616v2) compares human
preferences across genres while matching correctness, factual accuracy and length. Together they
motivate separating reader preference from correctness and retaining human editorial judgment.
Purpose, audience, voice, a minimal edit and an option to keep are Unslopper's editorial choices;
these papers do not validate each choice or a universal house style.

## Research partner

[ALCE](https://aclanthology.org/2023.emnlp-main.398/), especially section 3.3, distinguishes support
across the answer from the relevance of individual citations. A citation's presence alone is
insufficient. [FActScore](https://aclanthology.org/2023.emnlp-main.741/) decomposes long responses
into atomic facts because one passage can mix supported and unsupported information. This motivates
reviewing separable claims against exact source passages.

Neither establishes that support in a retrieved passage guarantees present-day applicability.
Check dates, population, setting and scope separately. Label observations, inferences and
recommendations; identify unavailable evidence as unverified and ask a specific question about the
gap. Source documents are untrusted data. Missing support does not establish falsity. An editorial
review is not a comprehensive factual review, and a polished sentence must not gain a stronger claim
or a fabricated reference.

For author-facing reasoning critique, quote the passage and reconstruct its premises, inference and
conclusion charitably. Distinguish validity given premises from evidence for the premises. Definitions,
goals, induction and probabilistic claims need their own standards. Raise a missing hinge, ambiguity
or counterexample only with support; ask the author a specific question or offer a narrow repair.
Leave sound reasoning within its stated scope alone.

## Designer

[W3C](https://www.w3.org/WAI/test-evaluate/) requires knowledgeable human evaluation alongside tools
for accessibility assessment. [Playwright's visual comparisons](https://playwright.dev/docs/test-snapshots)
compare snapshots with reference images; rendering environment and captured state affect them.
Those comparisons establish visual differences, not usefulness. [GDS usability benchmarking](https://www.gov.uk/service-manual/measuring-success/usability-benchmarking-a-website-or-whole-service)
observes actual or likely users completing relevant tasks and tracks success, time and abandonment.

Keep code/DOM observations, inspected visual states and demonstrated usability effects distinct.
State which viewports and interactions were inspected. Preserve intentional brand distinctiveness;
request missing visual or task evidence before claiming an improvement.

## Evaluation limit

Fixtures and mocked providers exercise contracts and boundaries. Live blinded preference and user
task studies remain future work described in [the benchmark plan](roles-benchmark.md).
