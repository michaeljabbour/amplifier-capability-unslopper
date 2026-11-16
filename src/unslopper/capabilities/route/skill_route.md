`route` picks the capability a job calls for, and the Agent Skill that teaches the same method
by hand, from a plain sentence about the job. Deterministic and free: it matches the words of
the job against each capability's vocabulary, so it is the first thing to run when it is not
obvious whether to scan, audit, unslop, direct, texture, tutor or run the whole pipeline. The
result always carries every route, so a caller can override the choice.

## Arguments

- `INTENT`: the job, in a sentence. Required. For instance "this landing page a model wrote
  looks generic, make it look designed" or "what font pairing and colours for a kayak rental".

```bash
unslopper route "this landing page looks AI generated, what is wrong with it"
unslopper route "give the coffee roaster site a palette"
unslopper route "review this argument as a research partner"
```

```python
from unslopper.lib import route

choice = route("make this page look less AI")
choice.capability, choice.skill, choice.command
```

## Result

`RouteResult`: `intent`; `capability` (the best match, or null when the sentence points nowhere,
in which case start with `scan`); `skill` (the Agent Skill directory under `skills/` that carries
the method); `command` (an example invocation to adapt); `reason` (the words that decided it and
when that capability is right); `alternatives` (every route: capability, skill, when); `roles` (suggested
editor, research-partner or designer roles, whose scope still needs to be established).

Read `role-contract.md` before combining roles. Research/source/logic work routes to the existing prose
audit with explicit context and supplied evidence; it returns comments rather than contacting an author.
A role suggestion does not establish factual support or visual evidence. Keep separate artifact scopes
for prose and designer work; no new role-specific command is needed.

Rules of thumb the table encodes: a screenshot means `audit`, not `scan`; "everything" or "the
whole thing" means `antislop`; "fix" or "remove" means `unslop`; colours, fonts or a brief mean
`direct`; one colour pair means `contrast`; a background means `texture`; a question about a word
means `tutor`; a list of the material means `reference`.

## Failures

An empty intent raises, asking for a sentence. Nothing else can fail: this capability never calls
a model.
