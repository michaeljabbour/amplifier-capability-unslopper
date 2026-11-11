# route

The capability and Agent Skill a job calls for, from a sentence about the job. Deterministic.

```python
def route(intent: str) -> RouteResult
```

- `intent`: the job in a sentence. An empty sentence raises `UnslopperError`.

Returns `RouteResult(intent, capability, skill, command, reason, alternatives)`. `capability` is `None` when nothing in the sentence points at one; `alternatives` always carries every route so the caller can override.

```bash
unslopper route INTENT
```

Prints the result as JSON. Exit 1 for an empty intent.
