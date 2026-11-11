"""Command line entry point for Unslopper."""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer

# Typer 0.27 vendors Click, so a command that overrides Click's own hooks has to speak the vendored types.
from typer._click import Context, Parameter
from typer.core import TyperCommand, TyperOption
from typer.models import CommandFunctionType

from unslopper import lib
from unslopper.core.skill import DISTRIBUTION
from unslopper.schemas import (
    DEFAULT_INTELLIGENCE_MODELS,
    AgentProvider,
    ReasoningEffort,
    Topic,
    TutorMode,
    UnslopperError,
)

MODEL_BACKED = "Model-backed: runs through Amplifier Agent or Claude, whichever --agent-provider names."
MODEL_DEFAULTS = "Defaults to " + ", ".join(
    f"{model} on {agent_provider}" for agent_provider, model in DEFAULT_INTELLIGENCE_MODELS.items()
)

AgentProviderOption = Annotated[
    AgentProvider | None,
    typer.Option("--agent-provider", help="The agent provider to run through. The first installed when omitted."),
]
ModelOption = Annotated[str | None, typer.Option("--model", help=f"The model to run on. {MODEL_DEFAULTS}.")]
EffortOption = Annotated[
    ReasoningEffort, typer.Option("--reasoning-effort", help="How hard the model thinks before it answers.")
]


class CapabilityCommand(TyperCommand):
    """Every capability answers `-h` with the generated summary and `--help` with its skill from the library."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["add_help_option"] = False
        super().__init__(*args, **kwargs)

    def get_params(self, ctx: Context) -> list[Parameter]:
        def short(ctx: Context, param: Parameter, value: bool) -> None:
            if value and not ctx.resilient_parsing:
                typer.echo(ctx.get_help())
                ctx.exit()

        def capability_skill(ctx: Context, param: Parameter, value: bool) -> None:
            if value and not ctx.resilient_parsing:
                typer.echo(lib.skill(self.name))
                ctx.exit()

        return [
            *super().get_params(ctx),
            TyperOption(
                param_decls=["-h"],
                is_flag=True,
                is_eager=True,
                expose_value=False,
                callback=short,
                help="Terse summary of this capability.",
            ),
            TyperOption(
                param_decls=["--help"],
                is_flag=True,
                is_eager=True,
                expose_value=False,
                callback=capability_skill,
                help="This capability's skill, for an agent about to call it.",
            ),
        ]


class SmartToolTyper(typer.Typer):
    """A Typer whose commands are CapabilityCommand by default, so a capability added later inherits the help split."""

    def command(
        self, *args: Any, cls: type[TyperCommand] = CapabilityCommand, **kwargs: Any
    ) -> Callable[[CommandFunctionType], CommandFunctionType]:
        return super().command(*args, cls=cls, **kwargs)


app = SmartToolTyper(
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    # `-h` is the terse summary and `--help` is the skill, at both scopes. On the root, the callback's parameter
    # claims `--help` and Click drops a help option name a parameter already took, which leaves the generated
    # summary on `-h`; on a capability, CapabilityCommand splits the two itself.
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _print_skill(value: bool) -> None:
    """Answer the root `--help` with the skill the library composes, leaving `-h` to Typer."""
    if value:
        typer.echo(lib.skill())
        raise typer.Exit()


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"{DISTRIBUTION} {lib.version()}")
        raise typer.Exit()


@app.callback()
def cli(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", is_eager=True, callback=_print_version, help="Print the version and exit."),
    ] = False,
    help: Annotated[
        bool,
        typer.Option(
            "--help", is_eager=True, callback=_print_skill, help="This tool's skill, for an agent driving it."
        ),
    ] = False,
) -> None:
    """Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model"""


@app.command()
def manifest() -> None:
    """Print the tool's manifest as JSON. Deterministic."""
    typer.echo(lib.load_manifest().model_dump_json(indent=2))


@app.command()
def reference(
    topic: Annotated[Topic, typer.Argument(help="terms, indicators, fixes, textures or palettes.")],
    name: Annotated[str | None, typer.Option("--name", help="Only the entry whose name matches.")] = None,
) -> None:
    """Print the course material for one topic as JSON. Deterministic."""
    typer.echo(lib.reference(topic, name).model_dump_json(indent=2))


@app.command()
def route(
    intent: Annotated[str, typer.Argument(help="The job, in a sentence.")],
) -> None:
    """Pick the capability and Agent Skill a job calls for. Deterministic."""
    typer.echo(lib.route(intent).model_dump_json(indent=2))


@app.command()
def scan(
    path: Annotated[Path | None, typer.Argument(help="An HTML or CSS file.")] = None,
    url: Annotated[str | None, typer.Option("--url", help="A page to fetch instead of a file.")] = None,
    source: Annotated[str | None, typer.Option("--source", help="Inline HTML or CSS instead of a file.")] = None,
) -> None:
    """Find the slop indicators static heuristics can see in HTML or CSS. Deterministic."""
    typer.echo(lib.scan(source, path, url).model_dump_json(indent=2))


@app.command()
def audit(
    path: Annotated[Path | None, typer.Argument(help="An HTML or CSS file.")] = None,
    url: Annotated[str | None, typer.Option("--url", help="A page to fetch instead of a file.")] = None,
    image: Annotated[Path | None, typer.Option("--image", help="A screenshot instead of a file.")] = None,
    source: Annotated[str | None, typer.Option("--source", help="Inline HTML or CSS instead of a file.")] = None,
    agent_provider: AgentProviderOption = None,
    model: ModelOption = None,
    reasoning_effort: EffortOption = "medium",
) -> None:
    """Review a design against the twenty slop indicators and report what shows, with evidence. Model-backed."""
    report = lib.audit(path, url, image, source, agent_provider, model, reasoning_effort)
    typer.echo(report.model_dump_json(indent=2))


@app.command()
def unslop(
    path: Annotated[Path, typer.Argument(help="The HTML or CSS file to fix.")],
    write: Annotated[
        bool, typer.Option("--write", help="Replace the file; otherwise only the diff is returned.")
    ] = False,
    agent_provider: AgentProviderOption = None,
    model: ModelOption = None,
    reasoning_effort: EffortOption = "medium",
) -> None:
    """Apply the fixes to a file as a diff, and write it with --write. Model-backed."""
    result = lib.unslop(path, write, None, agent_provider, model, reasoning_effort)
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def contrast(
    foreground: Annotated[str, typer.Argument(help="Text colour as hex, like #E8EEF2.")],
    background: Annotated[str, typer.Argument(help="Ground colour as hex, like #000412.")],
) -> None:
    """WCAG contrast ratio between two colours and the levels it passes. Deterministic."""
    typer.echo(lib.contrast(foreground, background).model_dump_json(indent=2))


@app.command()
def direct(
    brief: Annotated[str, typer.Argument(help="The product or brand, in a sentence or two.")],
    directions: Annotated[
        int | None,
        typer.Option("--directions", help="How many to offer. Three for an open brief, one for a specific one."),
    ] = None,
    dark_and_light: Annotated[
        bool, typer.Option("--dark-and-light", help="Emit both a dark and a light variant.")
    ] = False,
    agent_provider: AgentProviderOption = None,
    model: ModelOption = None,
    reasoning_effort: EffortOption = "medium",
) -> None:
    """Turn a brief into a committed direction: scene, palette, type, hero and CSS tokens. Model-backed."""
    result = lib.direct(brief, directions, dark_and_light, agent_provider, model, reasoning_effort)
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def tutor(
    mode: Annotated[TutorMode, typer.Argument(help="teach, quiz or explain.")] = "teach",
    term: Annotated[
        str | None, typer.Option("--term", help="The term to teach or quiz on. The next one when omitted.")
    ] = None,
    image: Annotated[Path | None, typer.Option("--image", help="In explain mode, the screenshot to read.")] = None,
    answer: Annotated[str | None, typer.Option("--answer", help="In quiz mode, the learner's answer to mark.")] = None,
    progress: Annotated[
        list[str] | None, typer.Option("--progress", help="A term already answered correctly. Repeatable.")
    ] = None,
    agent_provider: AgentProviderOption = None,
    model: ModelOption = None,
    reasoning_effort: EffortOption = "medium",
) -> None:
    """Teach, quiz or explain the twenty design terms, one short turn at a time. Model-backed."""
    turn = lib.tutor(mode, term, image, answer, progress, agent_provider, model, reasoning_effort)
    typer.echo(turn.model_dump_json(indent=2))


@app.command()
def texture(
    name: Annotated[
        str | None, typer.Option("--name", help="The texture to draw. Recommended from the subject when omitted.")
    ] = None,
    subject: Annotated[
        str | None, typer.Option("--subject", help="What the design is for, so the texture comes from its world.")
    ] = None,
    ground: Annotated[str | None, typer.Option("--ground", help="Ground colour as hex.")] = None,
    light: Annotated[str | None, typer.Option("--light", help="Light colour as hex.")] = None,
    signal: Annotated[str | None, typer.Option("--signal", help="Signal colour as hex.")] = None,
    animated: Annotated[
        bool, typer.Option("--animated", help="Allow motion, honouring prefers-reduced-motion.")
    ] = False,
    agent_provider: AgentProviderOption = None,
    model: ModelOption = None,
    reasoning_effort: EffortOption = "medium",
) -> None:
    """Recommend and generate a textured background as CSS or canvas code in a palette. Model-backed."""
    result = lib.texture(name, subject, ground, light, signal, animated, agent_provider, model, reasoning_effort)
    typer.echo(result.model_dump_json(indent=2))


@app.command()
def antislop(
    path: Annotated[Path, typer.Argument(help="The HTML or CSS file to take through the whole pipeline.")],
    write: Annotated[
        bool, typer.Option("--write", help="Replace the file; otherwise only the diff is returned.")
    ] = False,
    with_texture: Annotated[
        bool, typer.Option("--with-texture", help="Also add a textured background when the page is flat.")
    ] = False,
    agent_provider: AgentProviderOption = None,
    model: ModelOption = None,
    reasoning_effort: EffortOption = "medium",
) -> None:
    """Audit, fix, direct, texture, polish and re-audit one file. Model-backed."""
    report = lib.antislop(path, write, with_texture, agent_provider, model, reasoning_effort)
    typer.echo(report.model_dump_json(indent=2))


def main() -> int:
    try:
        app()
    except UnslopperError as error:
        typer.echo(error, err=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
