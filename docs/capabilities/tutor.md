# tutor

Teaches the twenty design terms from the course one short turn at a time, quizzes on them, or names the terms a screenshot calls for. Model-backed. The library is stateless: the caller carries `progress`, the terms answered correctly, from one turn into the next, and every turn reports the `next_term` so a loop needs no knowledge of the order.

Prompts are Liquid templates beside the code in `capabilities/tutor/`, rendered with the term's `meaning` and `ai_note` from `knowledge.TERMS`. The teaching order and the answer aliases are in `capability.py` as `ORDER` and `ALIASES`; marking is done in code, never by the model.

## Library

```python
def tutor(
    mode: TutorMode = "teach",
    term: str | None = None,
    image: Path | None = None,
    answer: str | None = None,
    progress: list[str] | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> TutorTurn
```

- `mode`: `teach`, `quiz` or `explain`.
- `term`: the term, by name or alias, matched case-insensitively. In `teach` and `quiz` it defaults to the first term in `ORDER` not in `progress`. Required when `answer` is given.
- `image`: in `explain`, the screenshot. Must exist. The agent runs read-only in its parent directory and is told to view the file by name.
- `answer`: in `quiz`, the learner's answer. Compared in code to the term's name and `ALIASES` after lowercasing and collapsing hyphens, whitespace and end punctuation.
- `progress`: terms already answered correctly, in any spelling the tool accepts; returned in canonical spelling.
- `agent_provider`, `model`, `reasoning_effort`, `intelligence`: as every model-backed capability; `model` defaults to the agent provider's entry in `DEFAULT_INTELLIGENCE_MODELS`.

Returns `TutorTurn`:

- `teach`: `term`, `text` (two sentences, a blank line, why generated designs miss it), `demo_html`, `prompt_line`.
- `quiz` without `answer`: `term` (pass it back with the answer), `text`, `demo_html`, `question`.
- `quiz` with `answer`: `term`, `text` (the feedback), `answer_correct`, and `progress` extended with the term when correct.
- `explain`: `text` only: a summary line then one `- Term: note` line per relevant term; `term` is None.
- Always: `progress` and `next_term`, the first term in `ORDER` not in `progress`, None once all twenty are.

Raises `UnslopperError` for a `term` or `progress` entry that is not one of the twenty (naming them), `quiz` with `answer` but no `term`, `explain` without `image` or with a path that is not a file, every term done with no `term` given, a missing agent provider or credentials, and a run that errored or returned no structured output.

```python
from unslopper.lib import tutor

progress: list[str] = []
asked = tutor("quiz", progress=progress)
marked = tutor("quiz", term=asked.term, answer="kerning", progress=progress)
progress = marked.progress
```

## CLI

```bash
unslopper tutor [MODE] [--term TEXT] [--image PATH] [--answer TEXT] [--progress TEXT ...] [model options]
```

`MODE` defaults to `teach`. `--progress` is repeatable, one term per flag. Calls `lib.tutor` and prints the `TutorTurn` as JSON. Exits 1 with the message on stderr for any `UnslopperError` above, 2 for a bad invocation.

```bash
unslopper tutor teach --term "tabular numbers"
unslopper tutor quiz --progress Kerning --progress Tracking
unslopper tutor quiz --term Leading --answer "line height" --progress Kerning --progress Tracking
unslopper tutor explain --image ./checkout.png --agent-provider claude
```

`explain` works best on the `claude` agent provider, whose Read tool can view image files.
