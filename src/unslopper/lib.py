"""Top level entry point for the Unslopper library.

Every capability is reachable from here. Deterministic ones run with no model provider configured;
model-backed ones go through the `Intelligence` interface and say so in their docstrings.
"""

from pathlib import Path
from typing import Literal, overload

from unslopper.capabilities.antislop.capability import antislop as _antislop
from unslopper.capabilities.audit.capability import audit as _audit
from unslopper.capabilities.audit.capability import scan as _scan
from unslopper.capabilities.direct.capability import contrast as _contrast
from unslopper.capabilities.direct.capability import direct as _direct
from unslopper.capabilities.prose.capability import audit_prose, scan_prose, unslop_prose
from unslopper.capabilities.reference.capability import reference as _reference
from unslopper.capabilities.route.capability import route as _route
from unslopper.capabilities.texture.capability import texture as _texture
from unslopper.capabilities.tutor.capability import tutor as _tutor
from unslopper.capabilities.unslop.capability import unslop as _unslop
from unslopper.core import manifest
from unslopper.core import skill as skill_module
from unslopper.intelligence.interface import Intelligence
from unslopper.schemas import (
    AgentProvider,
    AntislopReport,
    AuditReport,
    ContrastResult,
    DirectResult,
    Manifest,
    ProseAuditReport,
    ProseEditResult,
    ProseScanReport,
    ReasoningEffort,
    ReferenceResult,
    ReviewContext,
    RouteResult,
    ScanReport,
    TextureResult,
    Topic,
    TutorMode,
    TutorTurn,
    UnslopperError,
    UnslopResult,
)


def load_manifest() -> Manifest:
    """The tool's manifest as structured data, read from the SMART_TOOL.md shipped inside the package."""
    return manifest.load_manifest()


def skill(capability: str | None = None) -> str:
    """The tool's skill, or the named capability's own skill, wrapped so a reader knows where the tool's files are."""
    return skill_module.skill(capability)


def version() -> str:
    """The installed package's version, from its metadata."""
    return skill_module.version()


def reference(topic: Topic, name: str | None = None) -> ReferenceResult:
    """The course material for one topic, or the single entry `name` selects. Deterministic."""
    return _reference(topic, name)


def route(intent: str) -> RouteResult:
    """The capability and Agent Skill a job calls for, from a sentence about the job. Deterministic."""
    return _route(intent)


@overload
def scan(
    source: str | None = None, path: Path | None = None, url: str | None = None, prose: Literal[False] = False
) -> ScanReport: ...


@overload
def scan(
    source: str | None = None, path: Path | None = None, url: str | None = None, prose: Literal[True] = True
) -> ProseScanReport: ...


@overload
def scan(
    source: str | None = None, path: Path | None = None, url: str | None = None, prose: bool = False
) -> ScanReport | ProseScanReport: ...


def scan(
    source: str | None = None, path: Path | None = None, url: str | None = None, prose: bool = False
) -> ScanReport | ProseScanReport:
    """Static candidates in HTML/CSS, or scoped writing cues with `prose=True`. Deterministic."""
    if prose:
        if url is not None:
            raise UnslopperError("Prose mode accepts a local text/Markdown path or inline source, not a URL.")
        return scan_prose(source=source, path=path)
    return _scan(source, path, url)


@overload
def audit(
    path: Path | None = None,
    url: str | None = None,
    image: Path | None = None,
    source: str | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    prose: Literal[False] = False,
    context: ReviewContext | None = None,
) -> AuditReport: ...


@overload
def audit(
    path: Path | None = None,
    url: str | None = None,
    image: Path | None = None,
    source: str | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    prose: Literal[True] = True,
    context: ReviewContext | None = None,
) -> ProseAuditReport: ...


@overload
def audit(
    path: Path | None = None,
    url: str | None = None,
    image: Path | None = None,
    source: str | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    prose: bool = False,
    context: ReviewContext | None = None,
) -> AuditReport | ProseAuditReport: ...


def audit(
    path: Path | None = None,
    url: str | None = None,
    image: Path | None = None,
    source: str | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    prose: bool = False,
    context: ReviewContext | None = None,
) -> AuditReport | ProseAuditReport:
    """Review design defaults, or writing quality with `prose=True`. Model-backed; never infer authorship."""
    if context is not None and not prose:
        raise UnslopperError(
            "Review context is scoped to prose. Use prose=True or a separate design brief and artifact."
        )
    if prose:
        if url is not None or image is not None:
            raise UnslopperError("Prose mode accepts a local text/Markdown path or inline source, not a URL or image.")
        return audit_prose(source, path, agent_provider, model, reasoning_effort, intelligence, context)
    return _audit(path, url, image, source, agent_provider, model, reasoning_effort, intelligence)


@overload
def unslop(
    path: Path,
    write: bool = False,
    audit_report: AuditReport | ProseAuditReport | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    prose: Literal[False] = False,
    context: ReviewContext | None = None,
) -> UnslopResult: ...


@overload
def unslop(
    path: Path,
    write: bool = False,
    audit_report: AuditReport | ProseAuditReport | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    prose: Literal[True] = True,
    context: ReviewContext | None = None,
) -> ProseEditResult: ...


@overload
def unslop(
    path: Path,
    write: bool = False,
    audit_report: AuditReport | ProseAuditReport | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    prose: bool = False,
    context: ReviewContext | None = None,
) -> UnslopResult | ProseEditResult: ...


def unslop(
    path: Path,
    write: bool = False,
    audit_report: AuditReport | ProseAuditReport | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    prose: bool = False,
    context: ReviewContext | None = None,
) -> UnslopResult | ProseEditResult:
    """Apply the fixes to a file as a diff, writing only when asked. Model-backed."""
    if context is not None and not prose:
        raise UnslopperError(
            "Review context is scoped to prose. Use prose=True or a separate design brief and artifact."
        )
    if prose:
        if isinstance(audit_report, AuditReport):
            raise UnslopperError("Prose mode needs a prose audit report. Run audit(..., prose=True) or omit it.")
        return unslop_prose(path, write, audit_report, agent_provider, model, reasoning_effort, intelligence, context)
    if isinstance(audit_report, ProseAuditReport):
        raise UnslopperError("A prose audit needs unslop(..., prose=True). Omit it for an HTML/CSS pass.")
    return _unslop(path, write, audit_report, agent_provider, model, reasoning_effort, intelligence)


def contrast(foreground: str, background: str) -> ContrastResult:
    """WCAG 2 contrast ratio between two hex colours and the levels it passes. Deterministic."""
    return _contrast(foreground, background)


def direct(
    brief: str,
    directions: int | None = None,
    dark_and_light: bool = False,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> DirectResult:
    """Turn a brief into one or more committed directions with CSS tokens. Model-backed."""
    return _direct(brief, directions, dark_and_light, agent_provider, model, reasoning_effort, intelligence)


def tutor(
    mode: TutorMode = "teach",
    term: str | None = None,
    image: Path | None = None,
    answer: str | None = None,
    progress: list[str] | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> TutorTurn:
    """One short teaching, quiz or explanation turn about the design terms. Model-backed."""
    return _tutor(mode, term, image, answer, progress, agent_provider, model, reasoning_effort, intelligence)


def texture(
    name: str | None = None,
    subject: str | None = None,
    ground: str | None = None,
    light: str | None = None,
    signal: str | None = None,
    animated: bool = False,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> TextureResult:
    """Recommend textures for a subject and generate one as CSS or canvas code in a palette. Model-backed."""
    return _texture(
        name, subject, ground, light, signal, animated, agent_provider, model, reasoning_effort, intelligence
    )


def antislop(
    path: Path,
    write: bool = False,
    with_texture: bool = False,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> AntislopReport:
    """The whole pipeline over one file: audit, fix, direct, texture, polish and re-audit. Model-backed."""
    return _antislop(path, write, with_texture, agent_provider, model, reasoning_effort, intelligence)
