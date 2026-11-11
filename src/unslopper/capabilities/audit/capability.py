"""Audit: which of the twenty slop indicators a design shows, deterministically and with a model's judgment.

`scan` is static heuristics over HTML or CSS with no model involved. `audit` runs the scan, then asks a model to
confirm or reject each hit, find what static code cannot see, and judge whether a choice was deliberate.
"""

from pathlib import Path
from typing import Literal

import liquid
from pydantic import BaseModel, Field, JsonValue, ValidationError

from unslopper import knowledge
from unslopper.capabilities.audit.document import parse_css, parse_html
from unslopper.capabilities.audit.scan import scan_document
from unslopper.intelligence.interface import Intelligence, select_intelligence
from unslopper.intelligence.schemas import AgentRequest, HostWorkspace
from unslopper.schemas import (
    DEFAULT_INTELLIGENCE_MODELS,
    AgentProvider,
    AuditReport,
    Finding,
    Layer,
    ReasoningEffort,
    ScanAsset,
    ScanReport,
    UnslopperError,
)
from unslopper.sources import Source, load_source

HERE = Path(__file__).parent
INDICATORS_FILE = HERE / "indicators.md"
PROMPT_TEMPLATE = "audit.md.liquid"
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})
# Long enough for a whole landing page; past this a model's attention, not its context window, is the limit.
MAX_SOURCE_CHARS = 80_000
TIMEOUT_SECONDS = 600
IMPACT_ORDER = {"high": 0, "medium": 1, "low": 2}
INDICATOR_NAMES = [entry.name for entry in knowledge.INDICATORS]
# The schema the model answers to only admits catalog names, so a misspelt indicator is rejected before it reaches us.
INDICATOR_ENUM: dict[str, JsonValue] = {"enum": list(INDICATOR_NAMES)}

Impact = Literal["high", "medium", "low"]


class AnswerFinding(BaseModel):
    """One indicator the model judged present, with how much it hurts the design."""

    indicator: str = Field(
        description="The indicator's name, exactly as in the catalog", json_schema_extra=INDICATOR_ENUM
    )
    layer: Layer
    location: str = Field(description="Element, selector, line or region of the image")
    evidence: str = Field(description="The quoted text, CSS value or visual description")
    deliberate: bool = Field(description="True when it repeats consistently and belongs to the subject's world")
    rationale: str = Field(description="One or two sentences")
    impact: Impact = Field(description="How much removing it would improve the design")


class AuditAnswer(BaseModel):
    """The model's structured answer; the report is assembled from it in code."""

    summary: str = Field(description="One line")
    findings: list[AnswerFinding]
    score: int = Field(ge=0, le=20, description="Distinct indicators present as defaults, deliberate ones excluded")
    fixes_first: list[str] = Field(description="The three fix names to make first, from the catalog")


def scan(source: str | None = None, path: Path | None = None, url: str | None = None) -> ScanReport:
    """Static heuristics over HTML or CSS: the indicators code alone can see, with evidence. Deterministic."""
    return scan_source(load_source(path, url, source))


def audit(
    path: Path | None = None,
    url: str | None = None,
    image: Path | None = None,
    source: str | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> AuditReport:
    """Review a design and report which defaults show, with evidence, a score out of twenty and three fixes first."""
    given = [
        name
        for name, value in (("path", path), ("url", url), ("image", image), ("source", source))
        if value is not None
    ]
    if len(given) != 1:
        raise UnslopperError(
            "Give exactly one of a file path, a URL, an image, or inline source text. "
            f"Got {', '.join(given) if given else 'none'}."
        )
    intelligence, model = select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)
    intelligence.preflight()
    if image is not None:
        return _audit_image(image, intelligence, model, reasoning_effort)
    loaded = load_source(path, url, source)
    scanned = scan_source(loaded)
    prompt = render_prompt(loaded, scanned)
    answer = _ask(
        intelligence,
        AgentRequest(
            prompt=prompt,
            model=model,
            output_schema=AuditAnswer.model_json_schema(),
            reasoning_effort=reasoning_effort,
            timeout_seconds=TIMEOUT_SECONDS,
        ),
    )
    return build_report(loaded.label, answer, scanned)


def scan_source(loaded: Source) -> ScanReport:
    """The deterministic reading of loaded text: HTML runs every check, CSS the rule-based ones."""
    match loaded.kind:
        case "html":
            document = parse_html(loaded.text, loaded.stylesheets)
        case "css":
            document = parse_css(loaded.text)
        case "text":
            raise UnslopperError(
                f"{loaded.label} is neither HTML nor CSS. Pass an .html or .css file, a URL, or inline markup or "
                "stylesheet text that starts with a tag or contains rules."
            )
    hits = scan_document(document)
    names = [hit.indicator for hit in hits]
    return ScanReport(
        source=loaded.label,
        score=len(hits),
        verdict=knowledge.verdict(len(hits)),
        hits=hits,
        fixes_first=[fix.name for fix in knowledge.fixes_for(names)],
        source_kind=loaded.kind,
        assets=[ScanAsset(**asset._asdict()) for asset in loaded.assets],
        warnings=list(
            dict.fromkeys(
                [
                    "Static candidates only: no rendered layout, JavaScript state, or complete browser cascade was evaluated.",
                    *loaded.warnings,
                    *document.warnings,
                ]
            )
        ),
    )


def render_prompt(loaded: Source | None, scanned: ScanReport | None, image_name: str | None = None) -> str:
    """The audit prompt: the catalog, the deliberate-versus-default rule, the source or image, the scan and the contract."""
    text = loaded.text if loaded is not None else ""
    linked_stylesheets: list[dict[str, str]] = []
    total_chars = len(text)
    remaining = max(0, MAX_SOURCE_CHARS - len(text))
    for stylesheet in loaded.stylesheets if loaded is not None else ():
        total_chars += len(stylesheet.text)
        linked_stylesheets.append({"label": stylesheet.label, "text": stylesheet.text[:remaining]})
        remaining = max(0, remaining - len(stylesheet.text))
    truncated = total_chars > MAX_SOURCE_CHARS
    environment = liquid.Environment(loader=liquid.FileSystemLoader(HERE), undefined=liquid.StrictUndefined)
    return environment.get_template(PROMPT_TEMPLATE).render(
        indicators=[entry.model_dump() for entry in knowledge.INDICATORS],
        layers=[{"name": name, "note": note} for name, note in knowledge.LAYERS.items()],
        indicator_notes=INDICATORS_FILE.read_text(encoding="utf-8").strip(),
        fixes=[fix.model_dump() for fix in knowledge.FIXES],
        source_label=loaded.label if loaded is not None else "",
        source_kind=loaded.kind if loaded is not None else "",
        source_text=text[:MAX_SOURCE_CHARS],
        truncated=truncated,
        total_chars=total_chars,
        kept_chars=MAX_SOURCE_CHARS,
        linked_stylesheets=linked_stylesheets,
        scan_json=scanned.model_dump_json(indent=2) if scanned is not None else "",
        image_name=image_name or "",
    )


def build_report(label: str, answer: AuditAnswer, scanned: ScanReport | None) -> AuditReport:
    """The report from the model's answer: verdict from the course, findings by impact, three fixes at most."""
    try:
        findings = [
            Finding(
                indicator=knowledge.indicator(found.indicator).name,
                layer=found.layer,
                location=found.location,
                evidence=found.evidence,
                deliberate=found.deliberate,
                rationale=found.rationale,
            )
            for found in sorted(answer.findings, key=lambda found: IMPACT_ORDER[found.impact])
        ]
    except KeyError as error:
        raise UnslopperError(
            f"The model named an indicator that is not in the catalog: {error}. Run the audit again; "
            f"the catalog is {', '.join(INDICATOR_NAMES)}."
        ) from None
    defaults = [finding.indicator for finding in findings if not finding.deliberate]
    fixes_first = answer.fixes_first[:3] or [fix.name for fix in knowledge.fixes_for(defaults)][:3]
    return AuditReport(
        source=label,
        score=answer.score,
        verdict=knowledge.verdict(answer.score),
        summary=answer.summary,
        findings=findings,
        fixes_first=fixes_first,
        scan=scanned,
    )


def _audit_image(image: Path, intelligence: Intelligence, model: str, reasoning_effort: ReasoningEffort) -> AuditReport:
    if not image.is_file() or image.suffix.lower() not in IMAGE_SUFFIXES:
        raise UnslopperError(
            f"{image} is not an image file. Pass a screenshot as one of {', '.join(sorted(IMAGE_SUFFIXES))}."
        )
    image = image.resolve()
    prompt = render_prompt(None, None, image.name)
    request = AgentRequest(
        prompt=prompt,
        model=model,
        workspace=HostWorkspace(path=image.parent),
        output_schema=AuditAnswer.model_json_schema(),
        reasoning_effort=reasoning_effort,
        timeout_seconds=TIMEOUT_SECONDS,
    )
    return build_report(str(image), _ask(intelligence, request), None)


def _ask(intelligence: Intelligence, request: AgentRequest) -> AuditAnswer:
    result = intelligence.run(request)
    if result.error:
        raise UnslopperError(
            f"The audit's model call through {intelligence.implementation} failed: {result.error}. "
            "Check the agent provider's credentials and network, then run the audit again; a smaller source or a "
            "lower --reasoning-effort finishes faster."
        )
    try:
        return AuditAnswer.model_validate(result.output)
    except ValidationError as error:
        raise UnslopperError(
            f"The model's answer did not match the audit's shape: {error.error_count()} problem(s), first: "
            f"{error.errors()[0]['msg']} at {'.'.join(str(part) for part in error.errors()[0]['loc'])}. "
            "Run the audit again, or name a different --model."
        ) from None
