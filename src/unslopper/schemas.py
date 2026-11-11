from pathlib import Path
from typing import Literal, NamedTuple

from pydantic import BaseModel, Field

ReasoningEffort = Literal["low", "medium", "high", "xhigh", "max"]
AgentProvider = Literal["amplifier-agent", "claude"]
# Also the order an agent provider is picked in when none is named.
AGENT_PROVIDERS: tuple[AgentProvider, ...] = ("amplifier-agent", "claude")

DEFAULT_INTELLIGENCE_MODELS: dict[AgentProvider, str] = {
    "amplifier-agent": "openai/gpt-6-astra",
    "claude": "claude-opus-5-5",
}

SEMVER_PATTERN = r"^\d+\.\d+\.\d+$"
SLUG_PATTERN = r"^[a-z0-9]+(-[a-z0-9]+)*$"


class UnslopperError(Exception):
    """Raised for any failure the library can name and explain how to fix."""


# region: Manifest


class ManifestRequirement(BaseModel):
    """One environment prerequisite; `install` references documentation, never a command."""

    name: str
    purpose: str
    install: str
    optional: bool = False


class Manifest(BaseModel):
    """The structured form of SMART_TOOL.md."""

    smart_tool_format: int
    name: str = Field(pattern=SLUG_PATTERN)
    version: str = Field(pattern=SEMVER_PATTERN)
    description: str
    use_cases: list[str]
    platforms: list[str]
    requires: list[ManifestRequirement] = Field(default_factory=list)
    body: str = Field(description="The Markdown below the frontmatter: the skill `--help` renders")


# endregion

# region: Skill


class Capability(NamedTuple):
    """One capability of the tool: its line in the skill's capability list and its own skill."""

    name: str
    summary: str
    model_backed: bool
    skill: str  # the capability's skill body, a Markdown file relative to the skill directory
    resources: tuple[str, ...] = ()  # the files that skill refers to, relative to the skill directory


# endregion

# region: Design knowledge

Layer = Literal["Type", "Surface", "Structure", "Content"]
Move = Literal["Subtract", "Focus", "Systematize", "Respond"]
Role = Literal["ground", "light", "signal"]
Topic = Literal["terms", "indicators", "fixes", "textures", "palettes"]


class Term(BaseModel):
    """One of the twenty design terms a person needs to direct a model."""

    name: str
    meaning: str
    ai_note: str = Field(description="Why generated designs tend to get this wrong")


class Indicator(BaseModel):
    """One of the twenty slop indicators: a default that is a tell when it appears without a reason."""

    name: str
    layer: Layer
    description: str
    fix_ids: list[int] = Field(description="The fixes that remove it, by id")


class Fix(BaseModel):
    """One of the twenty fixes, grouped into four moves."""

    id: int
    name: str
    how: str
    move: Move


class Texture(BaseModel):
    """One of the twenty-two background textures, with the subjects it belongs to."""

    name: str
    use: str


class Swatch(BaseModel):
    """One colour in a three-role palette."""

    role: Role
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    note: str


class PaletteStudy(BaseModel):
    """A fictional brand committed to a ground, a light and a signal colour."""

    name: str
    mood: str
    swatches: list[Swatch]
    typography: str


class ReferenceResult(BaseModel):
    """What `reference` returns: one topic's entries, or the single entry a name selected."""

    topic: Topic
    items: list[Term | Indicator | Fix | Texture | PaletteStudy]


# endregion

# region: Scan and audit


class Evidence(BaseModel):
    """Where an indicator shows and what proves it."""

    location: str = Field(description="Element, selector, line or region")
    detail: str = Field(description="The quoted text, CSS value or visual description")


class ScanHit(BaseModel):
    """One indicator a deterministic scan found in HTML or CSS."""

    indicator: str
    layer: Layer
    evidence: list[Evidence]
    fix_ids: list[int]


class ScanReport(BaseModel):
    """The deterministic reading of a source: which indicators static heuristics can see."""

    source: str = Field(description="What was scanned: a path, a URL or 'inline'")
    score: int = Field(ge=0, le=20, description="Indicators present, out of twenty")
    verdict: str
    hits: list[ScanHit]
    fixes_first: list[str] = Field(description="Fix names in priority order")


class Finding(BaseModel):
    """One indicator the audit judged present, with its evidence and whether it looks chosen."""

    indicator: str
    layer: Layer
    location: str
    evidence: str
    deliberate: bool = Field(description="True when it repeats consistently and belongs to the subject's world")
    rationale: str


class AuditReport(BaseModel):
    """The model-backed reading of a design: findings ordered by impact and the three fixes to make first."""

    source: str
    score: int = Field(ge=0, le=20)
    verdict: str
    summary: str = Field(description="One line")
    findings: list[Finding]
    fixes_first: list[str] = Field(max_length=3)
    scan: ScanReport | None = Field(
        default=None, description="The deterministic scan the audit was given, when the input was HTML or CSS"
    )


# endregion

# region: Unslop


class PlannedChange(BaseModel):
    """One change in an unslop plan, tied to the fix it applies."""

    move: Move
    fix_id: int
    fix: str
    change: str = Field(description="What changes, in one sentence")


class UnslopResult(BaseModel):
    """A proposed or applied unslop pass over one file."""

    path: Path
    plan: list[PlannedChange]
    diff: str = Field(description="Unified diff from the original to the proposed file")
    before: ScanReport
    after: ScanReport
    written: bool = Field(description="Whether the proposed file replaced the original")
    notes: list[str] = Field(default_factory=list, description="Anything the caller should check by hand")


# endregion

# region: Direction


class ContrastResult(BaseModel):
    """WCAG 2 contrast between two colours."""

    foreground: str
    background: str
    ratio: float
    aa_body: bool = Field(description="At least 4.5 to 1")
    aa_large: bool = Field(description="At least 3 to 1")
    aaa_body: bool = Field(description="At least 7 to 1")


class Color(BaseModel):
    """One colour in a committed direction."""

    role: Role
    name: str = Field(description="A human name, like 'aurora green'")
    hex: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    oklch: str


class Typography(BaseModel):
    """A display and a body face the subject would use on its own signage."""

    display: str
    body: str
    rationale: str = Field(description="One sentence")


class Direction(BaseModel):
    """One visual direction: a scene, three colours with roles, type, a hero idea and CSS tokens."""

    scene: str = Field(description="One concrete sentence from the subject's world")
    palette: list[Color]
    contrast: ContrastResult = Field(description="Light on ground")
    typography: Typography
    hero: str
    css: str = Field(description="A :root block with the tokens, and a variant when asked for")


class DirectResult(BaseModel):
    """What `direct` returns: one direction for a specific brief, three for an open one."""

    brief: str
    directions: list[Direction]


# endregion

# region: Tutor

TutorMode = Literal["teach", "quiz", "explain"]


class TutorTurn(BaseModel):
    """One short turn from the tutor; the caller carries `progress` into the next call."""

    mode: TutorMode
    term: str | None = Field(default=None, description="The term this turn is about")
    text: str = Field(description="What the tutor says, kept short")
    demo_html: str | None = Field(default=None, description="A tiny self-contained wrong-versus-right demo")
    prompt_line: str | None = Field(
        default=None, description="One sentence to paste into a prompt to ask for it by name"
    )
    question: str | None = Field(default=None, description="In quiz mode, what the learner is asked")
    answer_correct: bool | None = Field(default=None, description="In quiz mode, when an answer was given")
    progress: list[str] = Field(default_factory=list, description="Terms answered correctly so far")
    next_term: str | None = None


# endregion

# region: Texture


class Palette(BaseModel):
    """Three colours with roles, as hex."""

    ground: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    light: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    signal: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class TextureRecommendation(BaseModel):
    """A texture that fits the subject, and why."""

    name: str
    why: str


class TextureResult(BaseModel):
    """Generated background code in the caller's palette."""

    palette: Palette
    recommendations: list[TextureRecommendation]
    texture: str = Field(description="The texture the code draws")
    kind: Literal["css", "canvas"]
    code: str = Field(description="Self-contained CSS, or a small seeded canvas script")
    size_bytes: int
    contrast: str = Field(description="How text on top was kept at WCAG AA, or that it already was")
    warning: str | None = Field(default=None, description="Set when the texture reads as a default for this subject")


# endregion

# region: Antislop


class PipelineStep(BaseModel):
    """One stage of the antislop pipeline and what it did."""

    name: str
    ran: bool
    note: str


class AntislopReport(BaseModel):
    """The whole pipeline over one file: before, after, and what happened in between."""

    path: Path
    before: AuditReport
    after: AuditReport
    steps: list[PipelineStep]
    diff: str
    written: bool
    summary: str = Field(description="Three lines")


# endregion

# region: Route


class RouteOption(BaseModel):
    """One capability and the Agent Skill that teaches its method, with the job it is for."""

    capability: str
    skill: str
    when: str


class RouteResult(BaseModel):
    """Which capability fits a job, and the whole table for when the choice is not clear-cut."""

    intent: str
    capability: str | None = Field(description="The best match, or None when nothing in the intent points anywhere")
    skill: str
    command: str = Field(description="An example invocation to start from")
    reason: str
    alternatives: list[RouteOption] = Field(description="Every route, so the caller can override the choice")


# endregion
