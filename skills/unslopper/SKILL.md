---
name: unslopper
description: >-
  Remove AI design defaults from visual work with the unslopper smart tool: scan or audit HTML,
  CSS, a URL or a screenshot against twenty slop indicators, apply the fixes as a diff, turn a
  brief into a three-colour direction with CSS tokens, generate textured backgrounds, teach the
  twenty design terms, or review and edit existing writing with explicit prose mode. Use for editor or scoped
  research-partner review of supplied claims and reasoning, when a design looks generic, when asked to
  "unslop", "de-slop" or "make this look less AI", when a page needs a
  visual direction or palette, or when someone needs design vocabulary. Drive it as `unslopper`
  from the command line or `unslopper.lib` from Python. Triggers on "unslopper", "design slop",
  "AI slop design", "unslop this page", "unslop this design", "unslop this writing", "stop slop".
license: MIT
metadata:
  version: "0.2.0"
  repository: https://github.com/michaeljabbour/amplifier-capability-unslopper
---

# Using unslopper

One library, eleven capabilities: the Unslop School design methods and integrated prose review. Deterministic ones (`manifest`,
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

## Role scope

Read [the shared role contract](references/role-contract.md), also exposed by command-help resources.
Use editor, research-partner and designer roles with an explicit scope when combining them. An editor
preserves purpose, audience and voice; a research partner maps claims to supplied sources and reviews
reasoning; a designer separates code/DOM evidence, inspected visual states and task impact. Keep or query
when evidence is insufficient. Return author-facing comments to the caller; never contact an author.

## Use it

Run `unslopper --help`. It prints the tool's skill: when to use it, every capability, sharp
edges, and which files to read. Follow it. Then read the capability's own skill with
`unslopper <command> --help` before calling it: it carries the arguments, a worked invocation,
and the result. Never work from memory.

Pick the entry point by the job. When it is not obvious, run `unslopper route "<the job in a
sentence>"`: it names the capability, an example command and the sibling skill, deterministically.

- "Is this slop?" with evidence: `scan` first (free), then `audit` when judgment is needed.
- "Fix it": `unslop PATH`, review the diff, then `unslop PATH --write`.
- "Review this writing": `scan PATH --prose`, then `audit PATH --prose` for model judgment. For edits, `unslop PATH --prose` returns a diff.
- "Review its evidence or reasoning": `audit PATH --prose --context review.json`; return `author_comments` and specific source or premise questions. Context is local JSON; source locators are not fetched.
- "Give it a direction": `direct "<brief>"`, then `contrast` on any pair you change.
- "The background is flat or a purple gradient": `texture` with the palette.
- "Teach me / quiz me / what is wrong here": `tutor`.
- "Just do the whole thing": `antislop PATH`, which chains the rest and takes minutes.

Every command prints one JSON document. Nothing on disk changes without `--write`. A failure
exits non-zero and names the remedy; relay it rather than working around it.

Prose mode accepts local `.txt`, `.md` or `.markdown` files; `scan` and `audit` also accept inline
`--source`. It rejects URL and image inputs. Prose reports separate objective problems from contextual
review cues, anchor findings to the source, carry `authorship: "not_assessed"` and have no score.
Review edits for voice, dialect, facts, calibrated uncertainty, attribution, quotations, citations and
references. Grammar, punctuation and rhetorical structures are not blanket errors. Conservative checks
cannot guarantee semantic fidelity; never report an AI probability.

Prose guidance adapts Michael Jabbour's Stop-Slop behavior, derived from Hardik Pandya's Stop-Slop.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the MIT notices.

The sibling skills in this repository carry the method for doing each job by hand when the tool
is not installed: `design-slop-audit`, `unslop-pass`, `palette-director`, `design-terms-tutor`,
`texture-backgrounds` and `design-antislopper`.

## Keep it current

Compare `unslopper --version` with the version in the repository's `SMART_TOOL.md`. When the install is behind, tell the user and offer `uv tool upgrade unslopper`; run it only when they agree. Never work around restrictions or the user's preferences.
