"""Tutor: teach the twenty design terms one at a time, quiz on them, or name the ones a screenshot calls for.

The CLI is stateless, so the caller carries `progress`, the terms answered correctly, from one turn into the
next; every turn reports the `next_term` so the loop can continue without the caller knowing the order.
"""

from pathlib import Path
import re

from liquid import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field

from unslopper import knowledge
from unslopper.intelligence.interface import Intelligence, select_intelligence
from unslopper.intelligence.schemas import AgentRequest, HostWorkspace
from unslopper.schemas import (
    DEFAULT_INTELLIGENCE_MODELS,
    AgentProvider,
    ReasoningEffort,
    Term,
    TutorMode,
    TutorTurn,
    UnslopperError,
)

# Type first, then layout, colour and motion: the order the brief asks a non-designer to meet the terms in.
ORDER: tuple[str, ...] = (
    "Kerning",
    "Tracking",
    "Leading",
    "x-height",
    "Tabular numbers",
    "Line length",
    "Widow",
    "Optical centre",
    "Touch target",
    "Safe area",
    "Affordance",
    "Combobox",
    "Progressive disclosure",
    "Layout shift",
    "OKLCH",
    "Optimistic update",
    "Origin-aware animation",
    "Stagger",
    "Interruptible animation",
    "Shared element transition",
)

# Other names a learner answers with that mean the same term; the term's own name always counts.
ALIASES: dict[str, tuple[str, ...]] = {
    "Kerning": ("kern", "kerning pairs"),
    "Tracking": ("letter spacing",),
    "Leading": ("line height",),
    "x-height": ("x height",),
    "Tabular numbers": ("tabular nums", "tabular figures", "tabular digits", "tabular lining figures"),
    "Line length": ("measure", "line width"),
    "Widow": ("widows", "widowed word"),
    "Optical centre": ("optical center", "optical alignment", "optical centering"),
    "Touch target": ("tap target", "hit area", "hit target", "touch area"),
    "Safe area": ("safe areas", "safe area inset"),
    "Affordance": ("affordances",),
    "Combobox": ("combo box", "autocomplete"),
    "Progressive disclosure": (),
    "Layout shift": ("cumulative layout shift", "cls", "content shift"),
    "OKLCH": ("oklch colour", "oklch color", "oklch color space"),
    "Optimistic update": ("optimistic ui", "optimistic updates"),
    "Origin-aware animation": ("origin aware", "transform origin"),
    "Stagger": ("staggered animation", "staggering"),
    "Interruptible animation": ("interruptible transitions", "interruptable animation"),
    "Shared element transition": ("view transition", "view transitions", "shared element", "hero transition"),
}

# The course's own live demos, carried into the teach prompt so the tutor echoes the lesson rather than inventing one.
COURSE_DEMOS: dict[str, str] = {
    "Kerning": (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font:700 34px/1 sans-serif">'
        '<div><div style="font-kerning:none;letter-spacing:.02em">AVATAR Type</div>'
        '<small style="display:block;font-size:12px;color:#666">No kerning</small></div>'
        '<div><div style="font-kerning:normal">AVATAR Type</div>'
        '<small style="display:block;font-size:12px;color:#666">Kerned</small></div></div>'
    ),
    "Tabular numbers": (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font:20px/1.3 sans-serif">'
        '<div style="font-variant-numeric:proportional-nums">$1,111.11<br>$8,808.00<br>$417.90'
        '<small style="display:block;font-size:12px;color:#666">Proportional</small></div>'
        '<div style="font-variant-numeric:tabular-nums">$1,111.11<br>$8,808.00<br>$417.90'
        '<small style="display:block;font-size:12px;color:#666">Tabular</small></div></div>'
    ),
    "x-height": (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;font-size:32px;line-height:1">'
        '<div><div style="font-family:Verdana,sans-serif">Hamburg</div>'
        '<small style="display:block;font-size:12px;color:#666">Tall x-height</small></div>'
        "<div><div style=\"font-family:'Times New Roman',serif\">Hamburg</div>"
        '<small style="display:block;font-size:12px;color:#666">Short x-height, same size</small></div></div>'
    ),
    "Touch target": (
        '<div style="display:flex;gap:18px;align-items:center;font:12px sans-serif;color:#666">'
        '<button type="button" style="width:24px;height:24px;padding:0;border:0;border-radius:6px;background:#2b6cb0;color:#fff">+</button>'
        "<span>24 px, hard to hit</span>"
        '<button type="button" style="width:44px;height:44px;padding:0;border:0;border-radius:6px;background:#2b6cb0;color:#fff">+</button>'
        "<span>44 px</span></div>"
    ),
}

TURN_TIMEOUT_SECONDS = 180
EXPLAIN_TIMEOUT_SECONDS = 300

TEMPLATES = Environment(loader=FileSystemLoader(Path(__file__).parent), undefined=StrictUndefined)


class TeachAnswer(BaseModel):
    """What the model returns for a teach turn."""

    explanation: str = Field(description="Two plain sentences saying what the term means")
    demo_html: str = Field(description="A self-contained HTML fragment showing wrong and right side by side")
    why_generated_designs_miss_it: str = Field(description="One or two sentences")
    prompt_line: str = Field(description="One sentence the learner can paste into a prompt to ask for it by name")


class QuizAnswer(BaseModel):
    """What the model returns for a quiz question."""

    lead_in: str = Field(description="One sentence pointing the learner at the demo, without naming the term")
    demo_html: str = Field(description="A self-contained HTML fragment showing wrong and right side by side")
    question: str = Field(description="The question, ending in 'which term applies?' without naming the term")


class MarkAnswer(BaseModel):
    """What the model returns when an answer has been marked."""

    feedback: str = Field(
        description="Two or three sentences: why the answer is right or wrong, and what the demo showed"
    )


class RelevantTerm(BaseModel):
    """One term a screenshot calls for."""

    term: str = Field(description="One of the twenty terms, spelled exactly as given")
    note: str = Field(description="One line on what in the image calls for it")


class ExplainAnswer(BaseModel):
    """What the model returns after reading a screenshot."""

    summary: str = Field(description="One sentence on what is wrong overall")
    relevant: list[RelevantTerm]


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
) -> TutorTurn:
    """One short turn: an explanation with a live demo, a quiz question or its marking, or a screenshot read."""
    done = [resolve_term(name).name for name in progress or []]
    intelligence, model = select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)
    intelligence.preflight()
    match mode:
        case "teach":
            return _teach(_chosen(term, done, mode), done, intelligence, model, reasoning_effort)
        case "quiz":
            if answer is None:
                return _quiz(_chosen(term, done, mode), done, intelligence, model, reasoning_effort)
            if term is None:
                raise UnslopperError(
                    "Marking an answer needs the term that was quizzed. Pass --term with the `term` of the quiz turn."
                )
            return _mark(resolve_term(term), answer, done, intelligence, model, reasoning_effort)
        case "explain":
            if image is None:
                raise UnslopperError("Explain mode reads a screenshot. Pass --image with the path to it.")
            if not image.is_file():
                raise UnslopperError(f"There is no file at {image}. Pass --image with the path to a screenshot.")
            return _explain(image.resolve(), done, intelligence, model, reasoning_effort)


def next_term(progress: list[str]) -> str | None:
    """The first term in teaching order not yet answered correctly, or None once all twenty are."""
    done = {resolve_term(name).name for name in progress}
    return next((name for name in ORDER if name not in done), None)


def resolve_term(name: str) -> Term:
    """The term `name` means, by its own name or an alias, case-insensitively; fails naming all twenty."""
    wanted = normalize(name)
    for entry in knowledge.TERMS:
        if wanted == normalize(entry.name) or wanted in ALIASES[entry.name]:
            return entry
    raise UnslopperError(f"'{name}' is not one of the twenty terms. They are: {', '.join(ORDER)}.")


def marks_correct(answer: str, term: Term) -> bool:
    """Whether the learner's answer names the term, by its own name or an alias."""
    given = normalize(answer)
    return given == normalize(term.name) or given in ALIASES[term.name]


def normalize(text: str) -> str:
    """Lowercase with hyphens and runs of whitespace collapsed to single spaces and end punctuation dropped."""
    return re.sub(r"[\s_-]+", " ", text.strip().lower()).strip(" .!?")


def _chosen(term: str | None, done: list[str], mode: TutorMode) -> Term:
    if term is not None:
        return resolve_term(term)
    upcoming = next_term(done)
    if upcoming is None:
        raise UnslopperError(
            f"All twenty terms are in --progress, so there is nothing left to {mode}. "
            "Pass --term to revisit one, or drop a term from --progress."
        )
    return resolve_term(upcoming)


def _teach(
    term: Term, done: list[str], intelligence: Intelligence, model: str, reasoning_effort: ReasoningEffort
) -> TutorTurn:
    prompt = _render("teach.md.liquid", term=term.model_dump(), course_demo=COURSE_DEMOS.get(term.name, ""))
    answer = TeachAnswer.model_validate(_complete(prompt, TeachAnswer, intelligence, model, reasoning_effort))
    return TutorTurn(
        mode="teach",
        term=term.name,
        text=f"{answer.explanation}\n\n{answer.why_generated_designs_miss_it}",
        demo_html=answer.demo_html,
        prompt_line=answer.prompt_line,
        progress=done,
        next_term=next_term(done),
    )


def _quiz(
    term: Term, done: list[str], intelligence: Intelligence, model: str, reasoning_effort: ReasoningEffort
) -> TutorTurn:
    prompt = _render("quiz.md.liquid", term=term.model_dump())
    answer = QuizAnswer.model_validate(_complete(prompt, QuizAnswer, intelligence, model, reasoning_effort))
    return TutorTurn(
        mode="quiz",
        term=term.name,
        text=answer.lead_in,
        demo_html=answer.demo_html,
        question=answer.question,
        progress=done,
        next_term=next_term(done),
    )


def _mark(
    term: Term,
    answer: str,
    done: list[str],
    intelligence: Intelligence,
    model: str,
    reasoning_effort: ReasoningEffort,
) -> TutorTurn:
    correct = marks_correct(answer, term)
    prompt = _render("mark.md.liquid", term=term.model_dump(), answer=answer, correct=correct)
    marked = MarkAnswer.model_validate(_complete(prompt, MarkAnswer, intelligence, model, reasoning_effort))
    progress = [*done, term.name] if correct and term.name not in done else done
    return TutorTurn(
        mode="quiz",
        term=term.name,
        text=marked.feedback,
        answer_correct=correct,
        progress=progress,
        next_term=next_term(progress),
    )


def _explain(
    image: Path, done: list[str], intelligence: Intelligence, model: str, reasoning_effort: ReasoningEffort
) -> TutorTurn:
    prompt = _render("explain.md.liquid", file=image.name, terms=[term.model_dump() for term in knowledge.TERMS])
    request = AgentRequest(
        prompt=prompt,
        model=model,
        workspace=HostWorkspace(path=image.parent),
        output_schema=ExplainAnswer.model_json_schema(),
        reasoning_effort=reasoning_effort,
        timeout_seconds=EXPLAIN_TIMEOUT_SECONDS,
    )
    read = ExplainAnswer.model_validate(_run(request, intelligence, "explain"))
    lines = [read.summary, ""] + [f"- {_known(entry.term)}: {entry.note}" for entry in read.relevant]
    return TutorTurn(mode="explain", text="\n".join(lines).strip(), progress=done, next_term=next_term(done))


def _known(name: str) -> str:
    """The canonical spelling of a term the model named, or the model's own words when it strayed from the list."""
    try:
        return resolve_term(name).name
    except UnslopperError:
        return name


def _render(template: str, **context: object) -> str:
    return TEMPLATES.get_template(template).render(**context)


def _complete(
    prompt: str,
    answer_model: type[BaseModel],
    intelligence: Intelligence,
    model: str,
    reasoning_effort: ReasoningEffort,
) -> dict[str, object]:
    """A plain completion, no tools, answered in `answer_model`'s shape."""
    request = AgentRequest(
        prompt=prompt,
        model=model,
        output_schema=answer_model.model_json_schema(),
        reasoning_effort=reasoning_effort,
        timeout_seconds=TURN_TIMEOUT_SECONDS,
    )
    return _run(request, intelligence, "turn")


def _run(request: AgentRequest, intelligence: Intelligence, what: str) -> dict[str, object]:
    result = intelligence.run(request)
    if result.error is not None or result.output is None:
        problem = result.error or "the model gave no structured answer"
        raise UnslopperError(
            f"The tutor's {what} did not finish: {problem}. Check the agent provider's credentials and the model "
            f"name ({request.model}), then run the same command again; a lower --reasoning-effort is enough for this."
        )
    return result.output
