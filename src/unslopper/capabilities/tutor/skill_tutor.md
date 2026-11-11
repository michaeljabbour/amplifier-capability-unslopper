`tutor` teaches the twenty design terms from the course to a non-designer, one short turn at a
time, so they can ask a model for what they want by name. Three modes: `teach` explains one term
with a tiny wrong-versus-right HTML demo and a sentence to paste into a prompt; `quiz` shows a
demo and asks which term applies, then marks the answer; `explain` reads a screenshot and names
the terms relevant to what is wrong. Every turn is one model call. The tool is stateless: you
carry the learner's progress between calls with `--progress`.

## Arguments

- `MODE`: `teach`, `quiz` or `explain`. Defaults to `teach`.
- `--term TEXT`: the term to teach or quiz on, by name or a common alias (`tabular nums`,
  `line height`). Omitted, the next term in teaching order not yet in `--progress` is used.
  Required when marking an answer. Fails naming all twenty when the name is not one of them.
- `--image PATH`: in `explain` mode, the screenshot to read. Required there and must exist.
- `--answer TEXT`: in `quiz` mode, the learner's answer to mark. Marking happens in code, by
  comparing the answer to the term's name and aliases, not by the model.
- `--progress TEXT`: a term the learner has already answered correctly. Repeatable; pass every
  term from the previous turn's `progress` back in.
- `--agent-provider`, `--model`, `--reasoning-effort`: the model-backed options. `medium`
  effort is plenty; `low` is fine for `teach` and `quiz`.

The teaching order runs type first (kerning, tracking, leading, x-height, tabular numbers, line
length, widow), then layout (optical centre, touch target, safe area, affordance, combobox,
progressive disclosure, layout shift), then colour (OKLCH), then motion (optimistic update,
origin-aware animation, stagger, interruptible animation, shared element transition).

## The loop

Teach, quiz, mark, repeat. Each turn returns `progress` and `next_term`; pass `progress` back
as repeated `--progress` flags and the tool picks the next term itself. Only correct answers go
into `progress`, so a missed term comes round again on its own; to revisit it sooner, quiz it by
name with `--term`. Show the learner `text`, render or describe `demo_html`, and hand them
`prompt_line` to keep.

```bash
unslopper tutor teach --term "tabular numbers"
unslopper tutor quiz --progress Kerning --progress Tracking
unslopper tutor quiz --term Leading --answer "line height" --progress Kerning --progress Tracking
unslopper tutor explain --image ./checkout.png --agent-provider claude
```

```python
from unslopper.lib import tutor

progress: list[str] = []
question = tutor("quiz", progress=progress)
marked = tutor("quiz", term=question.term, answer="kerning", progress=progress)
progress = marked.progress
lesson = tutor("teach", term=marked.next_term)
```

## Result

`TutorTurn`: `mode`; `term`, the term the turn is about (in `quiz` without an answer, the term
to pass back with `--answer`); `text`, what the tutor says; `demo_html`, a self-contained
fragment with inline CSS only, under about 2 KB, in `teach` and `quiz`; `prompt_line` in
`teach`; `question` in `quiz`; `answer_correct` once an answer was marked; `progress`, the given
terms plus this one when correct, in canonical spelling; `next_term`, the first term in
teaching order not in `progress`, or null when all twenty are done. In `explain`, `text` is one
summary line followed by one `- Term: note` line per relevant term and `term` is null.

## Failures

Each raises `UnslopperError` (exit 1) naming the remedy: a `--term` or `--progress` entry that
is not one of the twenty terms; `quiz --answer` without `--term`; `explain` without `--image` or
with a path that does not exist; every term already in `--progress` with no `--term` given; a
missing agent provider or credentials; a model run that errored or gave no structured answer.

`explain` runs the agent read-only in the screenshot's directory and asks it to view the file,
so it works best on the `claude` agent provider, whose Read tool can see images.
