"""Top level entry point for the Unslopper library.

Every capability is reachable from here. Deterministic ones run with no model provider configured;
model-backed ones go through the `Intelligence` interface and say so in their docstrings.
"""

from pathlib import Path

from unslopper.capabilities.antislop.capability import antislop as _antislop
from unslopper.capabilities.audit.capability import audit as _audit
from unslopper.capabilities.audit.capability import scan as _scan
from unslopper.capabilities.direct.capability import contrast as _contrast
from unslopper.capabilities.direct.capability import direct as _direct
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
    ReasoningEffort,
    ReferenceResult,
    RouteResult,
    ScanReport,
    TextureResult,
    Topic,
    TutorMode,
    TutorTurn,
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


def scan(source: str | None = None, path: Path | None = None, url: str | None = None) -> ScanReport:
    """The slop indicators static heuristics can see in HTML or CSS, with evidence and a score. Deterministic."""
    return _scan(source, path, url)


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
    """Review a design against the twenty indicators and report what shows, with evidence. Model-backed."""
    return _audit(path, url, image, source, agent_provider, model, reasoning_effort, intelligence)


def unslop(
    path: Path,
    write: bool = False,
    audit_report: AuditReport | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> UnslopResult:
    """Apply the fixes to a file as a diff, writing only when asked. Model-backed."""
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
