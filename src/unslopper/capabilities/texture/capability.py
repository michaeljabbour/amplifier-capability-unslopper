"""Texture: background treatments as self-contained CSS or canvas code, in the caller's palette."""

from pathlib import Path
import re
from typing import Literal

from liquid import Environment, StrictUndefined
from pydantic import BaseModel, Field

from unslopper import color, knowledge
from unslopper.intelligence.interface import Intelligence, select_intelligence
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.schemas import (
    DEFAULT_INTELLIGENCE_MODELS,
    AgentProvider,
    Palette,
    ReasoningEffort,
    Texture,
    TextureRecommendation,
    TextureResult,
    UnslopperError,
)

DIRECTORY = Path(__file__).parent
PROMPT_PATH = DIRECTORY / "texture.md.liquid"
REFERENCE_PATH = DIRECTORY / "textures-reference.md"
MAX_BYTES = 3072
TIMEOUT_SECONDS = 600

MOTION = re.compile(r"@keyframes|animation|transition|requestAnimationFrame")
# The SVG namespace is the one http URL a data-URI texture legitimately carries.
EXTERNAL_URL = re.compile(r"https?://(?!www\.w3\.org/)")
# What url() points at; anything but a data: URI or a fragment fetches something from outside the code.
URL_TARGET = re.compile(r"url\(\s*['\"]?\s*([^'\")]*)")
SCRIPT_OR_CANVAS = re.compile(r"<script|<canvas", re.IGNORECASE)
SCRIPT = re.compile(r"<script", re.IGNORECASE)
# What a contrast note has to say when light on ground alone fails AA body text.
REMEDY_WORDS = re.compile(r"scrim|overlay|lower|reduce|opacit|adjust|darken|lighten|raise", re.IGNORECASE)


class Answer(BaseModel):
    """The model's answer, flat so every agent provider can emit it; code checks it before it becomes a result."""

    recommendations: list[TextureRecommendation] = Field(
        description="Two or three textures from the catalog that fit the subject, the drawn one first, each with why"
    )
    texture: str = Field(description="The catalog name of the texture the code draws")
    kind: Literal["css", "canvas"]
    code: str = Field(description="The self-contained CSS rule set, or the canvas element with its script")
    contrast: str = Field(description="How text in the light colour stays at WCAG AA on this texture")
    warning: str = Field(description="Empty, or one sentence when the texture reads as an AI default for this subject")
    ground: str = Field(description="#RRGGBB when a palette was inferred, else empty")
    light: str = Field(description="#RRGGBB when a palette was inferred, else empty")
    signal: str = Field(description="#RRGGBB when a palette was inferred, else empty")


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
    """Recommend textures for the subject and generate one, checked for text contrast and kept under 3 KB."""
    palette = _palette(ground, light, signal)
    if palette is None and subject is None:
        raise UnslopperError(
            "Pass a subject, like 'a developer tools landing page', or a palette as --ground, --light and --signal. "
            "Without either there is nothing to draw the texture from."
        )
    requested = None if name is None else match_texture(name)
    prompt = render_prompt(requested, subject, palette, animated)
    intelligence, model = select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)
    intelligence.preflight()
    request = AgentRequest(
        prompt=prompt,
        model=model,
        output_schema=Answer.model_json_schema(),
        reasoning_effort=reasoning_effort,
        timeout_seconds=TIMEOUT_SECONDS,
    )
    result = _run(intelligence, request)
    answer = _answer(result)
    problems = check(answer, requested, palette, animated)
    if problems:
        # One retry in the same session, so the model corrects its own answer rather than starting over.
        retry = request.model_copy(update={"prompt": retry_prompt(problems), "resume": result.session_id})
        answer = _answer(_run(intelligence, retry))
        problems = check(answer, requested, palette, animated)
        if problems:
            raise UnslopperError(
                "The texture answer failed its checks twice: " + "; ".join(problems) + ". "
                "Try again, name a texture with --name, or pass a palette."
            )
    return _result(answer, palette)


def match_texture(name: str) -> Texture:
    """The catalog texture `name` selects, case-insensitively or by substring; raises naming the twenty-two."""
    wanted = name.strip().lower()
    for entry in knowledge.TEXTURES:
        if entry.name.lower() == wanted:
            return entry
    matches = [entry for entry in knowledge.TEXTURES if wanted in entry.name.lower()]
    if len(matches) == 1:
        return matches[0]
    known = ", ".join(entry.name for entry in knowledge.TEXTURES)
    if matches:
        names = ", ".join(entry.name for entry in matches)
        raise UnslopperError(f"'{name}' matches several textures: {names}. Name one of: {known}.")
    raise UnslopperError(f"'{name}' is not one of the twenty-two textures: {known}.")


def reference_snippets(textures: tuple[Texture, ...]) -> list[dict[str, str]]:
    """The course's canvas code for each texture, read from textures-reference.md."""
    document = REFERENCE_PATH.read_text(encoding="utf-8")
    snippets = {
        heading.strip(): code
        for heading, code in re.findall(r"^## (.+?)\n.*?```js\n(.+?)\n```", document, flags=re.MULTILINE | re.DOTALL)
    }
    missing = [entry.name for entry in textures if entry.name not in snippets]
    if missing:
        raise UnslopperError(f"{REFERENCE_PATH} has no reference code for: {', '.join(missing)}.")
    return [{"name": entry.name, "use": entry.use, "code": snippets[entry.name]} for entry in textures]


def render_prompt(requested: Texture | None, subject: str | None, palette: Palette | None, animated: bool) -> str:
    """The prompt: the catalog, the request, the relevant reference code and the code rules."""
    snippets = reference_snippets((requested,) if requested else knowledge.TEXTURES)
    template = Environment(undefined=StrictUndefined).from_string(PROMPT_PATH.read_text(encoding="utf-8"))
    return template.render(
        textures=[entry.model_dump() for entry in knowledge.TEXTURES],
        requested=None if requested is None else requested.model_dump(),
        subject=subject,
        palette=None if palette is None else palette.model_dump(),
        animated=animated,
        snippets=snippets,
        max_bytes=MAX_BYTES,
    )


def check(answer: Answer, requested: Texture | None, palette: Palette | None, animated: bool) -> list[str]:
    """Everything wrong with the answer that the model has to fix, in its own words; empty when it is acceptable."""
    problems: list[str] = []
    size = len(answer.code.encode())
    if size >= MAX_BYTES:
        problems.append(f"the code is {size} bytes and must be under {MAX_BYTES}")
    if not animated and (motion := MOTION.search(answer.code)):
        problems.append(f"the code animates ('{motion.group()}') and animation was not asked for")
    external = any(not target.startswith(("data:", "#")) for target in URL_TARGET.findall(answer.code))
    if external or EXTERNAL_URL.search(answer.code):
        problems.append("the code references an external resource; use only gradients, data: URIs and inline script")
    if answer.kind == "css" and SCRIPT_OR_CANVAS.search(answer.code):
        problems.append("kind is css but the code contains <script> or <canvas>")
    if answer.kind == "canvas" and not SCRIPT.search(answer.code):
        problems.append("kind is canvas but the code has no <script>")
    drawn = _catalog(answer.texture, problems)
    if requested is not None and drawn is not None and drawn != requested:
        problems.append(f"the texture must be {requested.name}, not {drawn.name}")
    if not answer.recommendations:
        problems.append("recommendations is empty; give two or three from the catalog with why, the drawn one first")
    elif _catalog(answer.recommendations[0].name, problems) != drawn:
        problems.append("the first recommendation must be the texture the code draws")
    if palette is None:
        try:
            _palette(answer.ground, answer.light, answer.signal)
        except UnslopperError as error:
            problems.append(f"the inferred palette is not three hex colours: {error}")
    return problems


def _catalog(name: str, problems: list[str]) -> Texture | None:
    """The catalog texture `name` selects, or None after recording why it selects none."""
    try:
        return match_texture(name)
    except UnslopperError as error:
        problems.append(str(error))
        return None


def retry_prompt(problems: list[str]) -> str:
    """What the model is told when its answer failed the checks."""
    return "Your answer was not accepted: " + "; ".join(problems) + ". Answer again with the whole answer corrected."


def _palette(ground: str | None, light: str | None, signal: str | None) -> Palette | None:
    given = {"ground": ground or None, "light": light or None, "signal": signal or None}
    if not any(given.values()):
        return None
    missing = [role for role, value in given.items() if value is None]
    if missing:
        raise UnslopperError(
            f"A palette needs ground, light and signal together; missing {', '.join(missing)}. "
            "Pass all three, or none and let the subject propose one."
        )
    return Palette(**{role: color.normalize_hex(value) for role, value in given.items() if value is not None})


def _run(intelligence: Intelligence, request: AgentRequest) -> AgentResult:
    result = intelligence.run(request)
    if result.error:
        raise UnslopperError(
            f"The texture agent failed: {result.error} Check the agent provider's credentials and model name, "
            "or pass a different --agent-provider or --model, then try again."
        )
    return result


def _answer(result: AgentResult) -> Answer:
    if result.output is None:
        raise UnslopperError("The texture agent answered without structured output. Try again.")
    return Answer.model_validate(result.output)


def _result(answer: Answer, palette: Palette | None) -> TextureResult:
    palette = palette or _palette(answer.ground, answer.light, answer.signal)
    if palette is None:
        raise UnslopperError("The texture agent proposed no palette. Try again or pass --ground, --light and --signal.")
    note = answer.contrast.strip()
    measured = color.contrast(palette.light, palette.ground)
    if not measured.aa_body and not REMEDY_WORDS.search(note):
        remedy = (
            f"Light on ground measures {measured.ratio}:1, under WCAG AA's 4.5:1 for body text: set body text on "
            f"a scrim of {palette.ground} at 85 percent or more, or lower the texture's contrast beneath it."
        )
        note = f"{note} {remedy}".strip()
    return TextureResult(
        palette=palette,
        recommendations=answer.recommendations,
        texture=match_texture(answer.texture).name,
        kind=answer.kind,
        code=answer.code,
        size_bytes=len(answer.code.encode()),
        contrast=note,
        warning=answer.warning.strip() or None,
    )
