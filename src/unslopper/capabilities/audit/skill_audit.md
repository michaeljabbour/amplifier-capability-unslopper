`audit` reviews a design against the twenty slop indicators and reports which defaults show, with
evidence, whether each looks deliberate or default, a score out of twenty and the three fixes to make
first. It never rewrites the design. For HTML, CSS or a URL it first runs the deterministic `scan`,
then makes one model call carrying the indicator catalog, the source, the scan as evidence to confirm
or reject, and the rule for deliberate versus default: a choice counts as deliberate when it repeats
consistently and connects to the subject's world. For a screenshot the model reads the image itself.

Reach for `unslopper scan` instead when there is no model provider or the question is only what
static code can see. Reach for `unslopper unslop` when the fixes should be applied.

## Arguments

Exactly one input:

- `PATH`: an `.html`, `.htm` or `.css` file.
- `--url TEXT`: fetch a page over http(s) and audit its HTML.
- `--image PATH`: a screenshot (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`). The agent runs read-only
  in the image's directory and views the file with its Read tool. Image audits work best on the
  `claude` agent provider, whose Read tool views images natively.
- `--source TEXT`: inline HTML or CSS.

Model options, as on every model-backed capability:

- `--agent-provider [amplifier-agent|claude]`: the agent provider to run through; the first installed
  when omitted.
- `--model TEXT`: the model to run on; defaults to the agent provider's entry in
  `DEFAULT_INTELLIGENCE_MODELS`.
- `--reasoning-effort [low|medium|high|xhigh|max]`: how hard the model thinks. Default `medium`.

```bash
unslopper audit landing.html
unslopper audit --url https://example.com --reasoning-effort high
unslopper audit --image hero.png --agent-provider claude
```

```python
from pathlib import Path

from unslopper.lib import audit

report = audit(path=Path("landing.html"), agent_provider="claude")
print(report.score, report.verdict, report.summary)
for finding in report.findings:
    flag = "deliberate" if finding.deliberate else "default"
    print(flag, finding.indicator, finding.location, finding.evidence)
print(report.fixes_first)
```

## Result

`AuditReport` as JSON: `source`, `score` (distinct indicators present as defaults, deliberate ones
excluded, 0 to 20), `verdict` (from the course's scale), `summary` (one line), `findings` ordered
by impact, `fixes_first` (at most three fix names) and `scan` (the `ScanReport` the model was given,
`null` for an image). Each `Finding` has `indicator`, `layer`, `location`, `evidence`, `deliberate`
and `rationale`. Very long sources are truncated before the model sees them and the summary says so.

## Failures

Exit 1 with the reason on stderr: no input or more than one, a path that is not a file or an image
that is not one of the listed formats, text that is neither HTML nor CSS, no agent provider
installed or no credentials (the message names what to install or set), a model run that errored or
timed out, or an answer that did not match the report's shape (run again or name another `--model`).
