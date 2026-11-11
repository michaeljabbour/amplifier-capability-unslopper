# Library Reference

Every capability of Unslopper is reachable from `unslopper.lib`.
All other surfaces, including the CLI, are thin wrappers over the library and add no capability of their own.

## Intelligence

Model-backed capabilities run through the `Intelligence` protocol in `unslopper.intelligence.interface`:

```python
class Intelligence(Protocol):
    implementation: str

    def preflight(self) -> None: ...
    def run(self, request: AgentRequest) -> AgentResult: ...
```

`preflight` raises `UnslopperError` naming what to configure when the implementation cannot run.
`run` executes one agent: `AgentRequest` holds the prompt, model, optional workspace, and optional output schema; `AgentResult` holds the text, structured output, or error.
Setting `AgentRequest.resume` to an earlier `AgentResult.session_id` continues that session instead of starting a fresh one, so the agent keeps what it learned.

`resolve_intelligence(agent_provider)` returns a shipped implementation, one per agent provider, each installed through the extra of the same name:

- `amplifier-agent`: `AmplifierAgentIntelligence`, built on [Amplifier Agent](https://github.com/microsoft/amplifier-agent). The model is `<provider>/<model>`. Sessions live under the platform's per-user state directory, in `unslopper/amplifier-agent`.
- `claude`: `ClaudeIntelligence`, built on the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python) and run with the user's Claude Code settings and the credentials Claude Code resolves: `ANTHROPIC_API_KEY`, or a cloud provider's, as [its docs](https://code.claude.com/docs/en/agent-sdk/quickstart) describe. Sessions are kept where Claude Code keeps them; a plain completion runs in the platform's per-user state directory, in `unslopper/claude`.

Without an agent provider named, the first installed in that order is used; one that is not installed raises `UnslopperError` with the command that installs it.
`select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)` is what a capability calls: an injected `intelligence` wins, and `model` falls back to the agent provider's entry in `DEFAULT_INTELLIGENCE_MODELS`.
Another implementation is a module satisfying the protocol and a branch in that factory.

## Manifest

The tool's `SMART_TOOL.md` as structured data: the frontmatter as fields, the Markdown below it as `Manifest.body`.

```python
def load_manifest() -> Manifest
```

## Skill

What an agent reads once it has decided to drive the tool: the manifest body and the capability list, wrapped so the reader knows where the tool's files are.
Naming a capability returns that capability's own skill instead: the same wrapper, a heading carrying the capability's name, whether it is deterministic or model-backed, and the Markdown beside its code, which covers its arguments, a worked invocation, and its result.
The CLI's `--help` prints exactly this, the tool's at the root and the capability's on a command.
Raises `UnslopperError` when the name is not a capability, naming the ones that are.

```python
def skill(capability: str | None = None) -> str
```

The capabilities the skill lists, one entry each, driven by the same table the CLI is built from:

```python
class Capability(NamedTuple):
    name: str
    summary: str
    model_backed: bool
    skill: str
    resources: tuple[str, ...] = ()
```

- `name` and `summary`: the command's name and its line in the tool's capability list.
- `model_backed`: whether it runs through the `Intelligence` interface, which decides the kind shown in both skills.
- `skill`: the capability's skill body, a Markdown file relative to the installed package root, written without frontmatter, title, or kind line because the renderer supplies them.
- `resources`: the files that body refers to, relative to the installed package root, listed under `<skill_resources>` in the capability's skill. The block is omitted when there are none.

## Version

The installed package's version, from its metadata. The CLI's `--version` prints it.

```python
def version() -> str
```

## Capabilities

Each capability has its own page under [capabilities/](capabilities/) with its arguments, what it returns or raises, and a worked invocation. The signatures `lib.py` exposes:

```python
def reference(topic: Topic, name: str | None = None) -> ReferenceResult                 # deterministic
def route(intent: str) -> RouteResult                                                   # deterministic
def scan(source: str | None = None, path: Path | None = None, url: str | None = None) -> ScanReport   # deterministic
def contrast(foreground: str, background: str) -> ContrastResult                        # deterministic
def audit(path=None, url=None, image=None, source=None, agent_provider=None, model=None, reasoning_effort="medium", intelligence=None) -> AuditReport
def unslop(path, write=False, audit_report=None, agent_provider=None, model=None, reasoning_effort="medium", intelligence=None) -> UnslopResult
def direct(brief, directions=None, dark_and_light=False, agent_provider=None, model=None, reasoning_effort="medium", intelligence=None) -> DirectResult
def tutor(mode="teach", term=None, image=None, answer=None, progress=None, agent_provider=None, model=None, reasoning_effort="medium", intelligence=None) -> TutorTurn
def texture(name=None, subject=None, ground=None, light=None, signal=None, animated=False, agent_provider=None, model=None, reasoning_effort="medium", intelligence=None) -> TextureResult
def antislop(path, write=False, with_texture=False, agent_provider=None, model=None, reasoning_effort="medium", intelligence=None) -> AntislopReport
```

- [reference](capabilities/reference.md): the course material as data.
- [route](capabilities/route.md): which capability and Agent Skill a job calls for.
- [scan](capabilities/scan.md) and [audit](capabilities/audit.md): which indicators show, statically and with judgment.
- [unslop](capabilities/unslop.md): the fixes as a diff, written on request.
- [contrast](capabilities/contrast.md) and [direct](capabilities/direct.md): WCAG contrast, and a brief turned into a direction.
- [tutor](capabilities/tutor.md): the twenty terms, taught one turn at a time.
- [texture](capabilities/texture.md): a background from the subject's world, as code.
- [antislop](capabilities/antislop.md): the pipeline over one file.

Every result is a pydantic model in `unslopper.schemas`, so `model_dump_json()` is what the CLI prints. Every failure is an `UnslopperError` naming what went wrong and what to do.

## Shared modules

- `unslopper.knowledge`: the terms, indicators, fixes, textures and palette studies, with `fixes_for`, `verdict`, `fix` and `indicator` lookups. The one source of truth; prompts, scans and `reference` all read it.
- `unslopper.sources`: `load_source(path, url, source)` loads exactly one of a file, a URL or inline text and says whether it is HTML, CSS or neither.
- `unslopper.color`: `parse_hex`, `normalize_hex`, `relative_luminance`, `contrast_ratio`, `contrast` and `to_oklch`, pure functions with no model involved.

## Adding a capability

A capability's code goes in `unslopper/capabilities/<name>/`, with its prompts, templates, and its own `skill_<capability>.md` beside it, named on its row in `core/skill.py` `CAPABILITIES`, and `lib.py` gets a facade function that imports it and is the only caller of it.
Each capability of the library gets a section here: what it does and when to reach for it, the signature `lib.py` exposes, what each argument means, and what it returns or raises.
Model-backed capabilities say so, and take `agent_provider`, `model`, `reasoning_effort`, and `intelligence`. `model` defaults to the agent provider's entry in `DEFAULT_INTELLIGENCE_MODELS` and `reasoning_effort` to `medium`, both from `unslopper.schemas`.
