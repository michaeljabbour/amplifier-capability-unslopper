---
name: unslopper
description: >-
  Remove AI design defaults from visual work with the unslopper smart tool: scan or audit HTML,
  CSS, a URL or a screenshot against twenty slop indicators, apply the fixes as a diff, turn a
  brief into a three-colour direction with CSS tokens, generate textured backgrounds, teach the
  twenty design terms, or run the whole pass on one file. Use when a design a model produced looks
  generic, when asked to "unslop", "de-slop" or "make this look less AI", when a page needs a
  visual direction or palette, or when someone needs design vocabulary. Drive it as `unslopper`
  from the command line or `unslopper.lib` from Python. Triggers on "unslopper", "design slop",
  "AI slop design", "unslop this page", "unslop this design".
license: MIT
metadata:
  version: "0.2.0"
  repository: https://github.com/michaeljabbour/amplifier-capability-unslopper
---

# Using unslopper

One library, eleven capabilities, from the Unslop School course. Deterministic ones (`manifest`,
`reference`, `route`, `scan`, `contrast`) need no credentials. Model-backed ones (`audit`, `unslop`,
`direct`, `tutor`, `texture`, `antislop`) run through Amplifier Agent or the Claude Agent SDK.

## Install

```bash
# as a CLI, choosing the agent provider(s) you want
uv tool install "unslopper[all | amplifier-agent | claude] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"

# as a library, from another project
uv add "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"

# once, without installing
uvx --from "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper" unslopper --help
```

Check with `unslopper manifest`, which needs no credentials.

## Use it

Run `unslopper --help`. It prints the tool's skill: when to use it, every capability, sharp
edges, and which files to read. Follow it. Then read the capability's own skill with
`unslopper <command> --help` before calling it: it carries the arguments, a worked invocation,
and the result. Never work from memory.

Pick the entry point by the job. When it is not obvious, run `unslopper route "<the job in a
sentence>"`: it names the capability, an example command and the sibling skill, deterministically.

- "Is this slop?" with evidence: `scan` first (free), then `audit` when judgment is needed.
- "Fix it": `unslop PATH`, review the diff, then `unslop PATH --write`.
- "Give it a direction": `direct "<brief>"`, then `contrast` on any pair you change.
- "The background is flat or a purple gradient": `texture` with the palette.
- "Teach me / quiz me / what is wrong here": `tutor`.
- "Just do the whole thing": `antislop PATH`, which chains the rest and takes minutes.

Every command prints one JSON document. Nothing on disk changes without `--write`. A failure
exits non-zero and names the remedy; relay it rather than working around it.

The sibling skills in this repository carry the method for doing each job by hand when the tool
is not installed: `design-slop-audit`, `unslop-pass`, `palette-director`, `design-terms-tutor`,
`texture-backgrounds` and `design-antislopper`.

## Keep it current

Compare `unslopper --version` with the version in the repository's `SMART_TOOL.md`. When the install is behind, tell the user and offer `uv tool upgrade unslopper`; run it only when they agree. Never work around restrictions or the user's preferences.
