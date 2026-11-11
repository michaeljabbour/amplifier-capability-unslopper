"""Antislop: the whole pipeline over one file, from audit through fixes, direction, texture and polish.

Purpose: one entry point that takes an HTML or CSS file and returns an improved copy, as a diff, with a
before and after score and a three-line account of what moved.
Inputs: the path of an .html, .htm or .css file, whether to write, whether to add a texture, and the agent
provider, model, reasoning effort or injected Intelligence every model-backed capability takes.
Outputs: AntislopReport with both audits, one PipelineStep per stage, the unified diff, whether the file was
written and the summary.
Side effects: several agent runs in a temporary directory; the original is replaced only when `write` is true.
Dependencies: the sibling capabilities audit, unslop, direct and texture, the Intelligence interface,
python-liquid.
"""

from collections.abc import Callable
import difflib
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any

from liquid import Environment, StrictUndefined
from pydantic import BaseModel, Field, ValidationError

# A composing capability imports its siblings itself: lib.py imports this module, so going through lib would
# be a circular import. They are imported as modules and called at call time, so a test can swap any of them.
from unslopper.capabilities.audit import capability as audit_capability
from unslopper.capabilities.direct import capability as direct_capability
from unslopper.capabilities.texture import capability as texture_capability
from unslopper.capabilities.unslop import capability as unslop_capability
from unslopper.intelligence.interface import Intelligence, select_intelligence
from unslopper.intelligence.schemas import AgentRequest, HostWorkspace
from unslopper.schemas import (
    DEFAULT_INTELLIGENCE_MODELS,
    AgentProvider,
    AntislopReport,
    AuditReport,
    Direction,
    Palette,
    PipelineStep,
    ReasoningEffort,
    TextureResult,
    UnslopperError,
    UnslopResult,
)

TEMPLATES = Path(__file__).parent
SUFFIXES = (".html", ".htm", ".css")
UNSLOP_THRESHOLD = 3
# A read of the page is one answer; an edit pass reads, edits and re-reads a long page many times.
READ_TIMEOUT_SECONDS = 300
EDIT_TIMEOUT_SECONDS = 1800
# Enough of each to show the page's choices without pasting the stylesheet into the prompt.
MAX_DECLARATIONS = 40
MAX_HEADINGS = 12
UNTOUCHED = "The original file is untouched."

ATTRIBUTE = re.compile(r"""\b(?:href|src|action)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE)
# A <link> href names a stylesheet or font, which the fixes may legitimately replace; it is not a link a reader follows.
LINK_TAG = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
CUSTOM_PROPERTY = re.compile(r"--[\w-]+\s*:\s*[^;}]+")
FONT_FAMILY = re.compile(r"font-family\s*:\s*[^;}]+", re.IGNORECASE)
BACKGROUND = re.compile(r"background(?:-color|-image)?\s*:\s*[^;}]+", re.IGNORECASE)
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HEADING = re.compile(r"<h[1-3][^>]*>(.*?)</h[1-3]>", re.IGNORECASE | re.DOTALL)
TAG = re.compile(r"<[^>]+>")


class DirectionRead(BaseModel):
    """What one look at the page's CSS says about its direction, and the brief its content implies."""

    has_direction: bool = Field(
        description="True only with a clear ground, light and signal colour and type that is not a default"
    )
    flat_background: bool = Field(description="True when the main background is a flat fill or a plain gradient")
    inferred_brief: str = Field(description="The product or subject in one or two sentences, from the content")
    ground: str | None = Field(default=None, description="The ground colour as #RRGGBB when the page has one")
    light: str | None = Field(default=None, description="The light colour as #RRGGBB when the page has one")
    signal: str | None = Field(default=None, description="The signal colour as #RRGGBB when the page has one")


class ChangesAnswer(BaseModel):
    """What an edit pass submits once the file is edited: one line per change made."""

    changed: list[str] = Field(description="What changed, one short line each; empty when nothing needed changing")


def antislop(
    path: Path,
    write: bool = False,
    with_texture: bool = False,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> AntislopReport:
    """Audit, unslop when the score is three or more, give direction when there is none, polish, and re-audit.

    Args:
        path: An existing .html, .htm or .css file.
        write: Replace the file with the result; otherwise nothing on disk changes and the diff is the deliverable.
        with_texture: Also draw a textured background when the page's background is flat.
        agent_provider: The agent provider to run through; the first installed when omitted.
        model: The model to run on; the agent provider's default when omitted.
        reasoning_effort: How hard the model thinks.
        intelligence: An Intelligence to run through instead of the shipped one; it drives every step.

    Returns:
        Both audits, one step record per stage, the unified diff, whether the file was written and three lines
        of summary.

    Raises:
        UnslopperError: The path is not an HTML or CSS file, a step failed (the message names it), or the
            result dropped a link target. The original is never changed on any failure.
    """
    if path.suffix.lower() not in SUFFIXES or not path.is_file():
        raise UnslopperError(
            f"{path} is not an HTML or CSS file. Pass the path of an existing .html, .htm or .css file to take "
            "through the pipeline."
        )
    intelligence, model = select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)
    intelligence.preflight()
    raw = path.read_text(encoding="utf-8", newline="")
    newline = "\r\n" if "\r\n" in raw else "\n"
    original = path.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="antislop-") as workspace:
        copy = Path(workspace) / path.name
        shutil.copyfile(path, copy)
        pipeline = Pipeline(copy, str(path), intelligence, model, reasoning_effort)
        before = pipeline.audit()
        pipeline.unslop(before)
        read = pipeline.direct()
        pipeline.texture(with_texture, read)
        pipeline.polish()
        after = pipeline.audit()
        edited = copy.read_text(encoding="utf-8")

    check_links(original, edited)
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            edited.splitlines(keepends=True),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
        )
    )
    if write:
        path.write_text(edited, encoding="utf-8", newline=newline)
    return AntislopReport(
        path=path,
        before=before,
        after=after,
        steps=pipeline.steps,
        diff=diff,
        written=write,
        summary=summarize(before, after, pipeline),
    )


class Pipeline:
    """The stages over one working copy; each records a PipelineStep and leaves the copy for the next."""

    def __init__(
        self, copy: Path, label: str, intelligence: Intelligence, model: str, reasoning_effort: ReasoningEffort
    ) -> None:
        self.copy = copy
        # The caller's own path. Every report names it, never the scratch copy the stages edit.
        self.label = label
        self.intelligence = intelligence
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.steps: list[PipelineStep] = []
        self.unslopped: UnslopResult | None = None
        self.direction: Direction | None = None
        self.textured: TextureResult | None = None
        self.polished: list[str] = []

    def audit(self) -> AuditReport:
        report = self._guard("audit", lambda: audit_capability.audit(path=self.copy, **self._model_arguments()))
        report.source = self.label
        if report.scan is not None:
            report.scan.source = self.label
        self._record("audit", True, f"{report.score}/20, {report.verdict}. {report.summary}")
        return report

    def unslop(self, before: AuditReport) -> None:
        if before.score < UNSLOP_THRESHOLD:
            self._record("unslop", False, f"Skipped: the score is {before.score}, below {UNSLOP_THRESHOLD}.")
            return
        result = self._guard(
            "unslop",
            lambda: unslop_capability.unslop(self.copy, write=True, audit_report=before, **self._model_arguments()),
        )
        result.path = Path(self.label)
        result.before.source = self.label
        result.after.source = self.label
        self.unslopped = result
        self._record(
            "unslop",
            True,
            f"{len(result.plan)} planned changes; scan score {result.before.score} before, {result.after.score} after.",
        )

    def direct(self) -> DirectionRead:
        read = DirectionRead.model_validate(
            self._run(
                "direct",
                render("direction.md.liquid", **page_facts(self.copy)),
                DirectionRead,
                writable=False,
                timeout_seconds=READ_TIMEOUT_SECONDS,
            )
        )
        if read.has_direction:
            self._record(
                "direct",
                False,
                f"Skipped: the page already commits to ground {read.ground}, light {read.light}, signal {read.signal}.",
            )
            return read
        result = self._guard(
            "direct", lambda: direct_capability.direct(read.inferred_brief, directions=1, **self._model_arguments())
        )
        if not result.directions:
            raise UnslopperError(f"The direct step failed: no direction came back for the brief. {UNTOUCHED}")
        direction = result.directions[0]
        changed = self._edit(
            "direct",
            render(
                "apply-direction.md.liquid",
                file_name=self.copy.name,
                scene=direction.scene,
                palette=[color.model_dump() for color in direction.palette],
                typography=direction.typography.model_dump(),
                css=direction.css,
            ),
        )
        self.direction = direction
        swatches = ", ".join(f"{color.role} {color.hex}" for color in direction.palette)
        self._record(
            "direct",
            True,
            f"Brief: {read.inferred_brief} Applied {swatches}; {direction.typography.display} with "
            f"{direction.typography.body}. {len(changed)} edits.",
        )
        return read

    def texture(self, with_texture: bool, read: DirectionRead) -> None:
        if not with_texture:
            self._record("texture", False, "Skipped: --with-texture was not asked for.")
            return
        if not read.flat_background:
            self._record("texture", False, "Skipped: the background already has texture or imagery.")
            return
        palette = self._palette(read)
        if palette is None:
            self._record("texture", False, "Skipped: no ground, light and signal colours as hex to draw in.")
            return
        result = self._guard(
            "texture",
            lambda: texture_capability.texture(
                subject=read.inferred_brief,
                ground=palette.ground,
                light=palette.light,
                signal=palette.signal,
                **self._model_arguments(),
            ),
        )
        changed = self._edit(
            "texture",
            render(
                "apply-texture.md.liquid",
                file_name=self.copy.name,
                texture=result.texture,
                kind=result.kind,
                code=result.code,
                contrast=result.contrast,
            ),
        )
        self.textured = result
        self._record(
            "texture", True, f"{result.texture} as {result.kind}, {result.size_bytes} bytes. {len(changed)} edits."
        )

    def polish(self) -> None:
        self.polished = self._edit("polish", render("polish.md.liquid", file_name=self.copy.name))
        note = (
            f"{len(self.polished)} edits: " + "; ".join(self.polished) if self.polished else "Nothing needed changing."
        )
        self._record("polish", True, note)

    def _palette(self, read: DirectionRead) -> Palette | None:
        """The applied direction's three colours, else the page's own; None when a role is unfilled."""
        if self.direction is not None:
            colors = {color.role: color.hex for color in self.direction.palette}
        else:
            colors = {"ground": read.ground, "light": read.light, "signal": read.signal}
        ground, light, signal = colors.get("ground"), colors.get("light"), colors.get("signal")
        if ground is None or light is None or signal is None:
            return None
        try:
            return Palette(ground=ground, light=light, signal=signal)
        except ValidationError:
            return None

    def _model_arguments(self) -> dict[str, Any]:
        return {"model": self.model, "reasoning_effort": self.reasoning_effort, "intelligence": self.intelligence}

    def _edit(self, step: str, prompt: str) -> list[str]:
        output = self._run(step, prompt, ChangesAnswer, writable=True, timeout_seconds=EDIT_TIMEOUT_SECONDS)
        return ChangesAnswer.model_validate(output).changed

    def _run(
        self, step: str, prompt: str, answer: type[BaseModel], writable: bool, timeout_seconds: int
    ) -> dict[str, Any]:
        result = self.intelligence.run(
            AgentRequest(
                prompt=prompt,
                model=self.model,
                workspace=HostWorkspace(path=self.copy.parent) if writable else None,
                writable=writable,
                output_schema=answer.model_json_schema(),
                reasoning_effort=self.reasoning_effort,
                timeout_seconds=timeout_seconds,
            )
        )
        if result.error:
            raise UnslopperError(
                f"The {step} step failed: {result.error} Check the agent provider's credentials and model, or retry "
                f"with --reasoning-effort high. {UNTOUCHED}"
            )
        if result.output is None:
            raise UnslopperError(
                f"The {step} step failed: the agent gave no structured answer. Retry the run. {UNTOUCHED}"
            )
        return result.output

    def _guard[T](self, step: str, call: Callable[[], T]) -> T:
        try:
            return call()
        except UnslopperError as error:
            raise UnslopperError(f"The {step} step failed: {error} {UNTOUCHED}") from None

    def _record(self, name: str, ran: bool, note: str) -> None:
        self.steps.append(PipelineStep(name=name, ran=ran, note=one_line(note)))


def render(template: str, **variables: Any) -> str:
    """One prompt from the template beside this module; a variable the template names but is not given fails."""
    source = (TEMPLATES / template).read_text(encoding="utf-8")
    return Environment(undefined=StrictUndefined).from_string(source).render(**variables)


def page_facts(copy: Path) -> dict[str, Any]:
    """What the direction read is shown: the page's own tokens, fonts, backgrounds, title and headings."""
    text = copy.read_text(encoding="utf-8")
    title = TITLE.search(text)
    return {
        "file_name": copy.name,
        "title": one_line(TAG.sub("", title.group(1))) if title else "",
        "headings": _unique([one_line(TAG.sub("", match)) for match in HEADING.findall(text)])[:MAX_HEADINGS],
        "custom_properties": _unique([one_line(match) for match in CUSTOM_PROPERTY.findall(text)])[:MAX_DECLARATIONS],
        "font_families": _unique([one_line(match) for match in FONT_FAMILY.findall(text)])[:MAX_DECLARATIONS],
        "backgrounds": _unique([one_line(match) for match in BACKGROUND.findall(text)])[:MAX_DECLARATIONS],
    }


def check_links(original: str, edited: str) -> None:
    """Raise when the result emptied the file or dropped an href, src or action value the original had."""
    if not edited.strip():
        raise UnslopperError(f"The pipeline left the file empty. Retry the run. {UNTOUCHED}")
    targets = {
        next(group for group in match.groups() if group is not None)
        for match in ATTRIBUTE.finditer(LINK_TAG.sub("", original))
    }
    missing = sorted(target for target in targets if target and target not in edited)
    if missing:
        raise UnslopperError(
            f"The result dropped these link targets: {', '.join(missing)}. Every href, src and action must survive "
            f"the pipeline. Retry the run. {UNTOUCHED}"
        )


def summarize(before: AuditReport, after: AuditReport, pipeline: Pipeline) -> str:
    """Exactly three lines: the scores, the biggest moves, and what to check by hand."""
    moves: list[str] = []
    if pipeline.unslopped is not None:
        fixes = _unique([change.fix for change in pipeline.unslopped.plan])[:3]
        moves.append(f"{len(pipeline.unslopped.plan)} fixes ({', '.join(fixes)})")
    if pipeline.direction is not None:
        swatches = "/".join(color.hex for color in pipeline.direction.palette)
        moves.append(f"a committed direction ({swatches}, {pipeline.direction.typography.display})")
    if pipeline.textured is not None:
        moves.append(f"a {pipeline.textured.texture.lower()} background")
    if pipeline.polished:
        moves.append(f"{len(pipeline.polished)} polish edits")
    checks = list(pipeline.unslopped.notes[:2]) if pipeline.unslopped is not None else []
    checks.append(
        "open the result in a browser, confirm the signal colour sits on one element, and read the copy aloud"
    )
    lines = [
        f"Score {before.score}/20 before, {after.score}/20 after.",
        "Biggest moves: " + ("; ".join(moves) if moves else "none, the page needed no changes") + ".",
        "Check by hand: " + "; ".join(one_line(check).rstrip(".") for check in checks) + ".",
    ]
    return "\n".join(lines)


def one_line(text: str) -> str:
    """The text with every run of whitespace, newlines included, as one space."""
    return " ".join(text.split())


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))
