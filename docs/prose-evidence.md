# Prose evidence and limits

Reviewed 2026-11-16. Unslopper reviews writing quality; it does not establish authorship or return an AI probability.

## What the evidence supports

- [Liang et al. (2023)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10382961/) found false accusations concentrated in non-native English essays in their detector evaluation. Simpler vocabulary is not evidence of AI use, and editing must preserve dialect and author voice.
- [RAID (2024)](https://aclanthology.org/2024.acl-long.674/) tested detectors across models, domains, decoding strategies and attacks. Performance degraded under these changes. A detector score is not a quality target.
- [Reinhart et al. (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874169/) found noun-heavy and participial patterns in the models studied. Effects varied by model: GPT-4o used agentless passive less often than human texts. This supports contextual review of dense prose, not a passive-voice ban.
- [Kobak et al. (2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12219543/) measured excess vocabulary in biomedical abstracts at corpus level. Their method cannot identify individual AI-assisted abstracts. Word occurrence alone is not a defect.
- [Rallapalli et al. (2026)](https://aclanthology.org/2026.findings-emnlp.1375/) found genre influenced style more strongly than source across 11 models and eight genres. [Shan et al. (2026)](https://aclanthology.org/2026.emnlp-main.1725/) found generation and editing left different stylistic traces. Neither study supports a universal list of forbidden constructions.
- [Park et al. (2026)](https://aclanthology.org/2026.emnlp-industry.109/) compared professional edits of non-native academic writing while holding content and authorship constant. Detector responses changed inconsistently, identifying editing style as a confound.

These are findings about particular corpora, models and tasks. They motivate conservative, genre-aware review; they do not validate Unslopper's individual rules or prove a sentence was generated.

## Editorial choices

Empty announcements, performative emphasis, unsupported generality and repeated setup/reveal scaffolding are editorial review cues. Report the passage and its cost to the reader, then allow keeping it when the context justifies it. Exact repetition is observable; whether it is accidental still needs judgment. Voice, rhythm and punctuation preferences belong to the author.

Do not ban hedges, adverbs, passive voice, contrast, tricolons or dashes. Preserve calibrated uncertainty such as "most" and "may". Never invent an actor, number, anecdote or concrete detail to make prose sound specific. Keep quotations, attribution, citations, references and factual details intact.

Industry offers useful distinctions: [Vale](https://vale.sh/features/markup) scopes linting to markup-aware spans; [Grammarly Authorship](https://support.grammarly.com/hc/en-us/articles/29548735595405-Introducing-Authorship) records the writing process; [SynthID](https://deepmind.google/models/synthid/) embeds watermarks in supported generated content. Unslopper adopts scope-aware review, and does not implement provenance tracking or watermark detection.

## Lineage

Adapted mechanisms come from Michael J. Jabbour's [Stop-Slop v0.5.0 behavior](https://github.com/michaeljabbour/amplifier-capability-research/blob/b91be99dd8ebbebb0736c469764b60eba97df2e1/behaviors/stop-slop.md) and its [prose-quality catalogs](https://github.com/michaeljabbour/amplifier-capability-research/tree/b91be99dd8ebbebb0736c469764b60eba97df2e1/context/prose-quality), pinned at `b91be99dd8ebbebb0736c469764b60eba97df2e1`. That work credits [Hardik Pandya's Stop-Slop](https://github.com/hardikpandya/stop-slop). Both use MIT terms; bundled third-party notices retain their copyrights and license. The catalogs' blanket bans and claim-strengthening rewrites were not adopted.

## Evaluation boundary

Paired synthetic regressions test candidate detection, appropriate abstention, protected spans and fidelity guards. They measure these cases only. Mocked agent tests verify contracts, not live rewriting quality. No live model comparison was run. A future quality evaluation should compare blinded outputs on identical samples by genre, allow ties, and assess factual fidelity separately from reader preference. No private writing or paid detector service is needed for the current checks.
