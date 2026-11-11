# Unslopper Smart Tool

Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model.

This is a [Smart Tool](https://github.com/microsoft/amplifier-smart-tools) which is a library with a thin CLI over it and model-backed capabilities sit behind an interface so many providers can be used.
We support [Amplifier Agent](https://github.com/microsoft/amplifier-agent) and the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python).

## Installation

Prerequisites:
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- For the model-backed capabilities, one of:
  - `amplifier-agent` agent provider: the model provider's credentials, for instance `OPENAI_API_KEY` for the default `openai/...` models. See [providers](https://github.com/microsoft/amplifier-agent/blob/v0.22.0/docs/providers.md).
  - `claude` agent provider: `ANTHROPIC_API_KEY`, or any of its other supported modes of [authentication](https://code.claude.com/docs/en/agent-sdk/quickstart).
- (Optional) Install the Smart Tools skill so your agent knows about Smart Tools: `npx skills add microsoft/amplifier-smart-tools`

To get started:

```bash
# Install the Agent Skill so your agent knows about it.
npx skills add michaeljabbour/amplifier-capability-unslopper
# Install the tool, choosing the provider(s) you want
uv tool install "unslopper[all | amplifier-agent | claude] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"
# Check the install; needs no credentials
unslopper manifest
```

To use it as a library:

```bash
uv add "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"
```

To update:

```bash
npx skills update unslopper   # add -g for global installs
uv tool upgrade unslopper
```

To uninstall:

```bash
npx skills remove unslopper   # add -g for global installs
uv tool uninstall unslopper
```

## What it does

The [Unslop School](docs/unslop-school.html) course ends with six prompts for building design skills. This tool is those six skills, built once as capabilities of one library, plus the deterministic pieces they rest on. Open the course in a browser for the material itself: the twenty terms, the twenty slop indicators, the twenty fixes, the palette method and the textures.

## Interface

```bash
# Print the tool's manifest as JSON. Deterministic.
unslopper manifest

# The course material as data: terms, indicators, fixes, textures or palettes. Deterministic.
unslopper reference indicators
unslopper reference terms --name "tabular"

# Which slop indicators static heuristics can see in a file, URL or inline source, with evidence. Deterministic.
unslopper scan page.html

# Review a file, URL or screenshot against the twenty indicators, judging deliberate from default. Model-backed.
unslopper audit page.html
unslopper audit --image screenshot.png --agent-provider claude

# Apply the fixes as a diff, then write them. Model-backed.
unslopper unslop page.html
unslopper unslop page.html --write

# WCAG contrast between two colours. Deterministic.
unslopper contrast "#E8EEF2" "#000412"

# Turn a brief into a committed direction with CSS tokens. Model-backed.
unslopper direct "a silent retreat in Kyoto, golden hour on water"

# Teach, quiz or explain the twenty design terms. Model-backed.
unslopper tutor teach --term "leading"
unslopper tutor quiz
unslopper tutor explain --image screenshot.png

# A textured background as CSS or canvas code, in a palette. Model-backed.
unslopper texture --subject "a children's puzzle game" --ground "#7B2D3B" --light "#FFF3E6" --signal "#FFD43B"

# The whole pass on one file, with a before and after score. Model-backed.
unslopper antislop page.html --write
```

Agent Skills for each capability live under [skills/](skills/): `unslopper` (the router), `design-slop-audit`, `unslop-pass`, `palette-director`, `design-terms-tutor`, `texture-backgrounds` and `design-antislopper`. Install one with `npx skills add michaeljabbour/amplifier-capability-unslopper --skill <name>`.

See the [CLI reference](docs/02-cli.md) for every flag and the [library reference](docs/01-library.md) for the Python surface.

## Website

[michaeljabbour.github.io/amplifier-capability-unslopper](https://michaeljabbour.github.io/amplifier-capability-unslopper/) presents the tool with the unedited outputs of one recorded run of every capability, and serves the course as `course.html`, generated from [docs/unslop-school.html](docs/unslop-school.html). The source is `site/`; the standard library alone builds it into `_site/`:

```bash
make build      # python3 scripts/build.py
make check      # python3 scripts/check.py and node --check site/site.js
make preview    # serve _site on 127.0.0.1:8000
```

The check fails on broken links, missing alt text, anything loaded from outside, drift from the sources it renders, and a scan score above 2 on the page itself. The build also regenerates [docs/RECORDED-OUTPUTS.md](docs/RECORDED-OUTPUTS.md), the manifest of recorded runs with their key figures, and the check fails when it is stale. Publishing is a manual dispatch of the Pages workflow. See [site/README.md](site/README.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to set up your development environment.
