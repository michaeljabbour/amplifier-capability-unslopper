# route

The capability and Agent Skill a job calls for, from a sentence about the job. Deterministic.

```python
def route(intent: str) -> RouteResult
```

- `intent`: the job in a sentence. An empty sentence raises `UnslopperError`.

Returns `RouteResult(intent, capability, skill, command, reason, alternatives, roles)`. `capability` is `None` when nothing in the sentence points at one; `alternatives` always carries every route so the caller can override. `roles` suggests editor, research-partner or designer scope from the intent; confirm scope before combining them.

Research or reasoning review uses the existing prose audit with supplied context; editing and visual work
retain their existing commands. A role suggestion does not provide sources, prove a claim or establish
visual evidence. See [roles](../roles.md).

```bash
unslopper route INTENT
unslopper route "review this argument as a research partner"
```

Prints the result as JSON. Exit 1 for an empty intent.
