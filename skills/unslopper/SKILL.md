---
name: unslopper
description: >-
  Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model. Drive it from the command line as `unslopper`, or from Python through
  `unslopper.lib`. Triggers on "unslopper".
license: MIT
metadata:
  repository: https://github.com/michaeljabbour/amplifier-capability-unslopper
---

# Using unslopper

Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model.

## Install

```bash
# as a CLI, choosing the agent provider(s) you want
uv tool install "unslopper[all | amplifier-agent | claude] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"

# as a library, from another project
uv add "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper"

# once, without installing
uvx --from "unslopper[all] @ git+https://github.com/michaeljabbour/amplifier-capability-unslopper" unslopper --help
```
## Use it

Run `unslopper --help`. It prints the tool's skill: when to use it, every capability, sharp
edges, and which files to read. Follow it. Then read the capability's own skill with
`unslopper <command> --help` before calling it: it carries the arguments, a worked
invocation, and the result. Never work from memory.

## Keep it current

Keep the tool up to date for the user by default if the permission mode allows it using `uv tool upgrade unslopper`.
Keep the skill up to date for the user with `npx skills update unslopper`, adding `-g` for global installs.
Do not try to get around restrictions or operate against the user's preferences to update tools (or skills).
