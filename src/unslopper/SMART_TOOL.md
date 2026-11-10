---
smart_tool_format: 1
name: unslopper
version: 0.1.0
description: >-
  Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model
use_cases:
  - >-
    Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model
platforms:
  - linux
  - macos
  - windows
requires:
  - name: amplifier-agent-provider-credentials
    purpose: >-
      The credentials of the model provider the amplifier-agent agent provider calls, for
      instance OPENAI_API_KEY for its default model. Without them, the model-backed
      capabilities cannot run through amplifier-agent.
    optional: true
    install: https://github.com/microsoft/amplifier-agent/blob/v0.22.0/docs/providers.md
  - name: claude-credentials
    purpose: >-
      ANTHROPIC_API_KEY, or a cloud provider's credentials, for the claude agent provider.
      Without them, the model-backed capabilities cannot run through claude.
    optional: true
    install: https://code.claude.com/docs/en/agent-sdk/quickstart

---

Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model.

**The library is the tool.** `unslopper.lib` holds every capability. The CLI is a thin
wrapper over it, so anything you can do from the shell you can also do from Python.

## When to reach for it

- Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model.

## Before writing code

Every capability has its own skill. Read `unslopper <command> --help` before calling it: it
carries the arguments, a worked invocation, and the result. Do not fill gaps from memory. The library source beside this file, `lib.py`, carries the signatures. The
repository's `docs/01-library.md` and `docs/02-cli.md` carry the rest.

## Install

```bash
# as a CLI
uv tool install "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"

# as a library, from another project
uv add "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"

# once, without installing
uvx --from "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper" unslopper --help
```

`[all]` brings every agent provider the model-backed capabilities run through. Put
`[amplifier-agent]` or `[claude]` in its place for just one, or drop it for the deterministic
capabilities only.

Verify with `unslopper manifest`, which needs no credentials. To upgrade, run
`uv tool upgrade unslopper`.

## Prerequisites

Deterministic capabilities need only `uv`. Model-backed capabilities run through an agent
provider, the first installed of `amplifier-agent` and `claude`:

- `amplifier-agent`: [Amplifier Agent](https://github.com/microsoft/amplifier-agent), calling
  the model provider named in the model `<provider>/<model>` with that provider's credentials,
  for instance `OPENAI_API_KEY` for the default `openai/...` models. See its
  [providers](https://github.com/microsoft/amplifier-agent/blob/v0.22.0/docs/providers.md).
- `claude`: the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python), with the
  user's Claude Code settings. Needs `ANTHROPIC_API_KEY`, or Amazon Bedrock, Claude Platform on AWS,
  Google Cloud's Agent Platform, or Microsoft Foundry credentials, see
  [authentication](https://code.claude.com/docs/en/agent-sdk/quickstart).

Without one, a model-backed capability fails immediately and names what to configure; it
never falls back to a deterministic answer.

Runs on Linux, macOS, and Windows.

## Straight and smart paths

Deterministic capabilities run with no provider configured. Model-backed capabilities go
through Amplifier Agent or Claude, and say so in their help text.

## Output and failure contract

Results go to stdout, diagnostics to stderr. A failure prints a message naming what went
wrong and how to fix it, and exits non-zero: 1 for a failure the tool can name, 2 for a
bad invocation. Never treat an empty result as success.

## Choosing a surface

Import the library from Python. Shell out to the CLI from anything that cannot import
Python in-process: a shell script, a CI job, or an agent that can run commands but not
load a Python object. Both reach the same capabilities.
