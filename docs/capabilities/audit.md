# audit

Which of the twenty slop indicators a design shows, with evidence, whether each looks deliberate, a score out of
twenty and the three fixes to make first. Model-backed. It never rewrites the design; that is `unslop`.

## Library

```python
def audit(
    path: Path | None = None,
    url: str | None = None,
    image: Path | None = None,
    source: str | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> AuditReport
```

Exactly one of `path`, `url`, `image` or `source`. For HTML, CSS or a URL the deterministic `scan` runs first,
then one plain completion (no tools) whose prompt carries the indicator catalog from `knowledge`, the notes in
`capabilities/audit/indicators.md`, the deliberate-versus-default rule, the source (truncated past
`MAX_SOURCE_CHARS`, and the prompt says so), the scan as evidence to confirm or reject, and the answer contract.
For an `image` (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`) the agent runs read-only in the image's directory and
is told to view the file by name with its Read tool; the `claude` agent provider does this best.

`agent_provider`, `model`, `reasoning_effort` and `intelligence` behave as on every model-backed capability:
`select_intelligence` resolves the implementation, and `model` defaults to the agent provider's entry in
`DEFAULT_INTELLIGENCE_MODELS`. The prompt is `capabilities/audit/audit.md.liquid`, rendered with strict
undefined variables.

Returns an `AuditReport`: `source`, `score` (distinct indicators present as defaults, 0 to 20), `verdict` from
`knowledge.verdict`, `summary` (one line), `findings` ordered by impact (each a `Finding` with `indicator`,
`layer`, `location`, `evidence`, `deliberate` and `rationale`), `fixes_first` (at most three fix names; from
`knowledge.fixes_for` when the model named none) and `scan` (the `ScanReport` the model saw, `None` for an
image). The model answers in `AuditAnswer`, whose `indicator` field only admits catalog names, and the report is
assembled from it in code.

Raises `UnslopperError` when the input is not exactly one, the path is not a file or the image not an image,
the text is neither HTML nor CSS, no agent provider or credentials are available, the run returned an error or
timed out (`TIMEOUT_SECONDS`), or the answer did not match the shape. Every message names the remedy.

## CLI

```bash
unslopper audit [PATH] [--url TEXT] [--image PATH] [--source TEXT]
                [--agent-provider amplifier-agent|claude] [--model TEXT]
                [--reasoning-effort low|medium|high|xhigh|max]
```

Calls `lib.audit(path, url, image, source, agent_provider, model, reasoning_effort)` and prints the
`AuditReport` as JSON. Exits 1 with the message on stderr for any `UnslopperError`, 2 for a bad invocation.
