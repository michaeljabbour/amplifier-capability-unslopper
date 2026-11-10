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

## Interface

```bash
# Print the tool's manifest as JSON
unslopper manifest
```

See the [CLI reference](docs/02-cli.md) for every flag and the [library reference](docs/01-library.md) for the Python surface.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to set up your development environment.
