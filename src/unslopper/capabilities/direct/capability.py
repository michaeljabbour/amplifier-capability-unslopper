"""Direct: turn a brief into a committed visual direction, and check colour contrast on the way."""

from pathlib import Path
import re

from liquid import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict

from unslopper import color, knowledge
from unslopper.intelligence.interface import Intelligence, select_intelligence
from unslopper.intelligence.schemas import AgentRequest
from unslopper.schemas import (
    DEFAULT_INTELLIGENCE_MODELS,
    AgentProvider,
    Color,
    ContrastResult,
    Direction,
    DirectResult,
    ReasoningEffort,
    Role,
    Typography,
    UnslopperError,
)

PROMPT_PATH = Path(__file__).parent / "direct.md.liquid"
RETRY_PATH = Path(__file__).parent / "retry.md.liquid"
TIMEOUT_SECONDS = 600
SIGNAL_SHARE = 10  # percent of the screen the signal colour may cover
ROLES: tuple[Role, ...] = ("ground", "light", "signal")

# OKLCH hue bands, in degrees. A gradient with one stop in each is the gradient every generated page has.
BLUE_HUES = (225.0, 285.0)
PURPLE_HUES = (285.0, 345.0)
GREY_CHROMA = 0.04
# The CSS colour names a model reaches for when it writes that gradient without hex.
NAMED_COLORS = {
    "blue": "#0000FF",
    "royalblue": "#4169E1",
    "slateblue": "#6A5ACD",
    "indigo": "#4B0082",
    "blueviolet": "#8A2BE2",
    "mediumpurple": "#9370DB",
    "purple": "#800080",
    "violet": "#EE82EE",
}
HEX = re.compile(r"#(?:[0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})(?![0-9A-Fa-f])")
CUSTOM_PROPERTY = re.compile(r"(--[\w-]+)\s*:\s*([^;}]+)")
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,[^)]*)?\)")
OKLCH_HUE = re.compile(r"oklch\([^ ]+ ([^ ]+) ([^)]+)\)")


class ColorAnswer(BaseModel):
    """One colour as the model names it; the library adds the OKLCH value."""

    model_config = ConfigDict(extra="forbid")

    role: Role
    name: str
    hex: str


class DirectionAnswer(BaseModel):
    """One direction as the model answers it; contrast is computed, never asked for."""

    model_config = ConfigDict(extra="forbid")

    scene: str
    colours: list[ColorAnswer]
    display: str
    body: str
    rationale: str
    hero: str
    css: str


class DirectAnswer(BaseModel):
    """The model's whole answer: one direction for a specific brief, three for an open one."""

    model_config = ConfigDict(extra="forbid")

    directions: list[DirectionAnswer]


def contrast(foreground: str, background: str) -> ContrastResult:
    """WCAG 2 contrast ratio between two hex colours and the levels it passes. Deterministic."""
    return color.contrast(foreground, background)


def direct(
    brief: str,
    directions: int | None = None,
    dark_and_light: bool = False,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> DirectResult:
    """A scene, three colours with roles, a type pairing, a hero idea and CSS tokens; three when the brief is open."""
    if not brief.strip():
        raise UnslopperError("The brief is empty. Describe the product or brand in a sentence or two.")
    if directions is not None and directions < 1:
        raise UnslopperError(f"--directions must be 1 or more, not {directions}.")
    intelligence, model = select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)
    intelligence.preflight()

    prompt = _render(PROMPT_PATH, brief=brief, directions=directions, dark_and_light=dark_and_light)
    answer, session_id = _ask(intelligence, model, reasoning_effort, prompt)
    problems = _problems(answer, directions)
    if problems:
        # One retry in the same session, so the model keeps the directions that passed and fixes the ones named.
        retry = _render(RETRY_PATH, problems=problems)
        answer, _ = _ask(intelligence, model, reasoning_effort, retry, resume=session_id)
        problems = _problems(answer, directions)
    if problems:
        raise UnslopperError(
            "The direction still fails after one retry: "
            + " ".join(problems)
            + " Run again, raise --reasoning-effort, or name the ground and light colours in the brief."
        )
    return DirectResult(brief=brief, directions=[_direction(entry) for entry in answer.directions])


def _render(path: Path, **variables: object) -> str:
    environment = Environment(undefined=StrictUndefined)
    studies = [study.model_dump() for study in knowledge.PALETTE_STUDIES]
    return environment.from_string(path.read_text(encoding="utf-8")).render(
        banned=list(knowledge.BANNED_ADJECTIVES),
        default_faces=list(knowledge.DEFAULT_FACES),
        studies=studies,
        signal_share=SIGNAL_SHARE,
        aa_body=color.AA_BODY,
        **variables,
    )


def _ask(
    intelligence: Intelligence, model: str, reasoning_effort: ReasoningEffort, prompt: str, resume: str | None = None
) -> tuple[DirectAnswer, str | None]:
    result = intelligence.run(
        AgentRequest(
            prompt=prompt,
            model=model,
            output_schema=DirectAnswer.model_json_schema(),
            reasoning_effort=reasoning_effort,
            timeout_seconds=TIMEOUT_SECONDS,
            resume=resume,
        )
    )
    if result.error is not None or result.output is None:
        raise UnslopperError(
            f"The model did not return a direction: {result.error or 'no structured output'}. "
            "Run again, try a different --model, or raise --reasoning-effort."
        )
    return DirectAnswer.model_validate(result.output), result.session_id


def _problems(answer: DirectAnswer, directions: int | None) -> list[str]:
    """What stops the answer being returned, one sentence each, naming the direction and the remedy."""
    problems: list[str] = []
    if directions is not None and len(answer.directions) != directions:
        problems.append(f"{directions} directions were asked for and {len(answer.directions)} came back.")
    for index, entry in enumerate(answer.directions, start=1):
        label = f"Direction {index} ({entry.scene.strip()[:60]})"
        roles = {swatch.role for swatch in entry.colours}
        if len(entry.colours) != len(ROLES) or roles != set(ROLES):
            problems.append(f"{label}: give exactly three colours, one each for ground, light and signal.")
            continue
        swatch = _swatches(entry)
        ratio = color.contrast(swatch["light"].hex, swatch["ground"].hex)
        if not ratio.aa_body:
            problems.append(
                f"{label}: light {ratio.foreground} on ground {ratio.background} is {ratio.ratio} to 1 and body text "
                f"needs {color.AA_BODY} to 1. Lighten the light or darken the ground until it passes."
            )
        if ":root" not in entry.css:
            problems.append(f"{label}: the CSS has no :root block for the tokens.")
        if has_purple_blue_gradient(entry.css):
            problems.append(
                f"{label}: the CSS has a gradient between purple and blue hues. Remove it; a flat ground or a "
                "gradient inside one hue is fine."
            )
    return problems


def _direction(entry: DirectionAnswer) -> Direction:
    swatch = _swatches(entry)
    return Direction(
        scene=entry.scene,
        palette=[
            Color(role=role, name=swatch[role].name, hex=swatch[role].hex, oklch=color.to_oklch(swatch[role].hex))
            for role in ROLES
        ],
        contrast=color.contrast(swatch["light"].hex, swatch["ground"].hex),
        typography=Typography(display=entry.display, body=entry.body, rationale=entry.rationale),
        hero=entry.hero,
        css=entry.css,
    )


def _swatches(entry: DirectionAnswer) -> dict[Role, ColorAnswer]:
    return {swatch.role: swatch.model_copy(update={"hex": color.normalize_hex(swatch.hex)}) for swatch in entry.colours}


def has_purple_blue_gradient(css: str) -> bool:
    """Whether any gradient in the CSS runs between a blue and a purple stop, after resolving `var()` tokens."""
    tokens = {name: value.strip() for name, value in CUSTOM_PROPERTY.findall(css)}
    for arguments in _gradient_arguments(css):
        resolved = VAR.sub(lambda match: tokens.get(match.group(1), ""), arguments)
        hues = [hue for hue in map(_hue, _stop_colors(resolved)) if hue is not None]
        blue = any(BLUE_HUES[0] <= hue < BLUE_HUES[1] for hue in hues)
        purple = any(PURPLE_HUES[0] <= hue < PURPLE_HUES[1] for hue in hues)
        if blue and purple:
            return True
    return False


def _gradient_arguments(css: str) -> list[str]:
    """The text inside every `*-gradient(...)`, with nested parentheses kept whole."""
    found: list[str] = []
    for match in re.finditer(r"gradient\(", css):
        depth, start = 1, match.end()
        for position in range(start, len(css)):
            depth += {"(": 1, ")": -1}.get(css[position], 0)
            if depth == 0:
                found.append(css[start:position])
                break
    return found


def _stop_colors(arguments: str) -> list[str]:
    colors = HEX.findall(arguments)
    colors += [NAMED_COLORS[word] for word in re.findall(r"[a-z]+", arguments.lower()) if word in NAMED_COLORS]
    return colors


def _hue(value: str) -> float | None:
    """The OKLCH hue of a colour, or None when it is too grey to belong to any hue."""
    match = OKLCH_HUE.match(color.to_oklch(value))
    if match is None or float(match.group(1)) < GREY_CHROMA:
        return None
    return float(match.group(2))
