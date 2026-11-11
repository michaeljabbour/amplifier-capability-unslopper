---
smart_tool_format: 1
name: unslopper
version: 0.1.0
description: >-
  Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model
use_cases:
  - Tell whether a page a model generated reads as default output, with evidence and a score out of twenty
  - Remove the tells from an HTML or CSS file without changing what it says or how it is laid out
  - Give a product one committed visual direction instead of a purple gradient and Inter
  - Replace a flat or gradient background with a texture from the subject's world, as code
  - Teach a non-designer the twenty terms they need to direct design work by name
  - Take one file through the whole pass, from audit to polish, and report before and after
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

Removes AI design defaults from visual work. It knows twenty slop indicators, the twenty fixes
that remove them, twenty design terms, twenty-two textures and the three-colour method for giving a
design a direction, and it applies them to HTML, CSS, screenshots and briefs. The material comes
from the Unslop School course shipped in the repository's `docs/`.

**The library is the tool.** `unslopper.lib` holds every capability. The CLI is a thin
wrapper over it, so anything you can do from the shell you can also do from Python.

## When to reach for it

Not sure which capability? `unslopper route "<the job in a sentence>"` names it, with the Agent
Skill that teaches the same method by hand, and costs nothing.

- A page, component or screenshot a model produced looks generic and you need to say why, with
  evidence: `scan` (free, static) or `audit` (model-backed, judges deliberate from default).
- You have the HTML or CSS and want the fixes applied as a reviewable diff: `unslop`.
- A brief needs a direction before layout starts: `direct`, with `contrast` to check any pair.
- A background is flat or a purple gradient: `texture`.
- Someone needs the vocabulary to ask for what they want: `tutor`, or `reference terms`.
- You want the whole pass on one file with a before and after score: `antislop`.

Not for rendering or pixel measurement, not a design system, and not a judge of taste: a choice
that repeats and belongs to the subject's world is reported as deliberate and left alone.

## Before writing code

Every capability has its own skill. Read `unslopper <command> --help` before calling it: it
carries the arguments, a worked invocation, and the result. Do not fill gaps from memory. The
library source beside this file, `lib.py`, carries the signatures, and `knowledge.py` the course
material every capability reasons from. The repository's `docs/01-library.md` and `docs/02-cli.md`
carry the rest.

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

Deterministic capabilities (`manifest`, `reference`, `route`, `scan`, `contrast`) need only `uv`.
Model-backed capabilities run through an agent provider, the first installed of
`amplifier-agent` and `claude`:

- `amplifier-agent`: [Amplifier Agent](https://github.com/microsoft/amplifier-agent), calling
  the model provider named in the model `<provider>/<model>` with that provider's credentials,
  for instance `OPENAI_API_KEY` for the default `openai/...` models. See its
  [providers](https://github.com/microsoft/amplifier-agent/blob/v0.22.0/docs/providers.md).
- `claude`: the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python), with the
  user's Claude Code settings. Needs `ANTHROPIC_API_KEY`, or Amazon Bedrock, Claude Platform on AWS,
  Google Cloud's Agent Platform, or Microsoft Foundry credentials, see
  [authentication](https://code.claude.com/docs/en/agent-sdk/quickstart).

Without one, a model-backed capability fails immediately and names what to configure; it
never falls back to a deterministic answer. Reading screenshots (`audit --image`,
`tutor explain --image`) works on the `claude` provider, whose file reader handles images.

Runs on Linux, macOS, and Windows.

## Worked invocations

```bash
unslopper route "make this page look less AI"   # which capability and skill fit the job
unslopper scan page.html                      # static, free: indicators with evidence, score, fixes first
unslopper audit page.html                     # the same with a model's judgment of deliberate versus default
unslopper unslop page.html                    # a diff; add --write to apply it
unslopper direct "a mechanical watch brand lit like the aurora"
unslopper texture --name blueprint --subject "developer tools" --ground "#1C4E8A" --light "#F5F7FA" --signal "#FFB020"
unslopper tutor teach --term "tabular numbers"
unslopper antislop page.html --write          # the whole pass; several model calls, takes minutes
```

## Output and failure contract

Results go to stdout as one JSON document, diagnostics to stderr. A failure prints a message
naming what went wrong and how to fix it, and exits non-zero: 1 for a failure the tool can name,
2 for a bad invocation. Nothing on disk changes unless a command is given `--write`; without it the
diff in the result is the deliverable. Never treat an empty result as success.

## Choosing a surface

Import the library from Python to chain capabilities, for instance an `audit` fed into `unslop`.
Shell out to the CLI from anything that cannot import Python in-process: a shell script, a CI
job, or an agent that can run commands but not load a Python object. Both reach the same
capabilities.
