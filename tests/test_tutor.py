"""Drives the tutor with a fake intelligence, so no agent provider, credentials or network are needed."""

from pathlib import Path
from typing import Any

import pytest
import yaml

from unslopper import knowledge
from unslopper.capabilities.tutor.capability import (
    ALIASES,
    ORDER,
    ExplainAnswer,
    MarkAnswer,
    QuizAnswer,
    TeachAnswer,
    marks_correct,
    next_term,
    resolve_term,
    tutor,
)
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.schemas import UnslopperError

REPOSITORY = Path(__file__).parents[1]
AGENT_SKILL = REPOSITORY / "skills" / "design-terms-tutor"

TEACH_OUTPUT = {
    "explanation": "Digits share one width. Columns line up.",
    "demo_html": "<div>demo</div>",
    "why_generated_designs_miss_it": "Defaults are proportional.",
    "prompt_line": "Use tabular numbers on every price.",
}
QUIZ_OUTPUT = {
    "lead_in": "Compare the two panels.",
    "demo_html": "<div>before/after</div>",
    "question": "The right column stops wobbling: which term applies?",
}
MARK_OUTPUT = {"feedback": "That is it."}
EXPLAIN_SUMMARY = "The buttons are tiny and the prices wobble."
EXPLAIN_OUTPUT = {
    "summary": EXPLAIN_SUMMARY,
    "relevant": [{"term": "Touch target", "note": "24px icon buttons"}, {"term": "tabular nums", "note": "prices"}],
}


class FakeIntelligence:
    """Records every request and answers each with the next canned result."""

    def __init__(self, *results: AgentResult) -> None:
        self.implementation = "fake"
        self.results = list(results)
        self.requests: list[AgentRequest] = []
        self.preflights = 0

    def preflight(self) -> None:
        self.preflights += 1

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        return self.results.pop(0)


def answering(output: dict[str, Any]) -> FakeIntelligence:
    return FakeIntelligence(AgentResult(output=output, text="done"))


def test_order_is_exactly_the_twenty_knowledge_terms_with_type_first_and_motion_last() -> None:
    assert len(ORDER) == 20
    assert set(ORDER) == {term.name for term in knowledge.TERMS}
    assert set(ALIASES) == set(ORDER)
    assert ORDER[0] == "Kerning"
    assert ORDER[-1] == "Shared element transition"


def test_next_term_skips_progress_in_any_spelling_and_ends_in_none() -> None:
    assert next_term([]) == "Kerning"
    assert next_term(["kerning", "TRACKING", "line height"]) == "x-height"
    assert next_term(list(ORDER)) is None


def test_terms_resolve_by_name_or_alias_and_unknown_names_list_all_twenty() -> None:
    assert resolve_term("tabular nums").name == "Tabular numbers"
    assert resolve_term("Optical Center").name == "Optical centre"

    with pytest.raises(UnslopperError) as failure:
        resolve_term("serif")

    for name in ORDER:
        assert name in str(failure.value)


def test_teach_prompt_carries_the_terms_meaning_and_runs_as_a_plain_completion() -> None:
    fake = answering(TEACH_OUTPUT)
    term = resolve_term("Tabular numbers")

    turn = tutor("teach", term="tabular numbers", intelligence=fake, model="fake-model")

    assert fake.preflights == 1
    [request] = fake.requests
    assert request.workspace is None
    assert request.model == "fake-model"
    assert request.output_schema == TeachAnswer.model_json_schema()
    assert term.meaning in request.prompt
    assert term.ai_note in request.prompt
    assert "tabular-nums" in request.prompt
    assert turn.mode == "teach"
    assert turn.term == "Tabular numbers"
    assert turn.text.startswith(TEACH_OUTPUT["explanation"])
    assert TEACH_OUTPUT["why_generated_designs_miss_it"] in turn.text
    assert turn.demo_html == TEACH_OUTPUT["demo_html"]
    assert turn.prompt_line == TEACH_OUTPUT["prompt_line"]
    assert turn.progress == []
    assert turn.next_term == "Kerning"


def test_teach_without_a_term_takes_the_next_one_and_keeps_progress_canonical() -> None:
    fake = answering(TEACH_OUTPUT)

    turn = tutor("teach", progress=["kerning", "tracking"], intelligence=fake)

    assert turn.term == "Leading"
    assert resolve_term("Leading").meaning in fake.requests[0].prompt
    assert turn.progress == ["Kerning", "Tracking"]
    assert turn.next_term == "Leading"


def test_teach_with_every_term_done_and_none_named_fails_with_a_remedy() -> None:
    fake = answering(TEACH_OUTPUT)

    with pytest.raises(UnslopperError, match="--term"):
        tutor("teach", progress=list(ORDER), intelligence=fake)

    assert fake.requests == []


def test_quiz_without_an_answer_asks_about_the_term_without_naming_it_in_the_prompt_instructions() -> None:
    fake = answering(QUIZ_OUTPUT)

    turn = tutor("quiz", progress=["Kerning"], intelligence=fake)

    [request] = fake.requests
    assert request.workspace is None
    assert request.output_schema == QuizAnswer.model_json_schema()
    assert resolve_term("Tracking").meaning in request.prompt
    assert turn.mode == "quiz"
    assert turn.term == "Tracking"
    assert turn.text == QUIZ_OUTPUT["lead_in"]
    assert turn.question == QUIZ_OUTPUT["question"]
    assert turn.demo_html == QUIZ_OUTPUT["demo_html"]
    assert turn.answer_correct is None
    assert turn.progress == ["Kerning"]


@pytest.mark.parametrize("answer", ["Tabular numbers", "tabular nums", " Tabular-Figures. "])
def test_a_correct_answer_is_marked_in_code_and_added_to_progress(answer: str) -> None:
    fake = answering(MARK_OUTPUT)

    turn = tutor("quiz", term="Tabular numbers", answer=answer, progress=["Kerning"], intelligence=fake)

    [request] = fake.requests
    assert request.output_schema == MarkAnswer.model_json_schema()
    assert "marked correct" in request.prompt
    assert answer in request.prompt
    assert turn.answer_correct is True
    assert turn.text == MARK_OUTPUT["feedback"]
    assert turn.progress == ["Kerning", "Tabular numbers"]
    assert turn.next_term == "Tracking"


def test_a_wrong_answer_is_marked_in_code_and_leaves_progress_alone() -> None:
    fake = answering(MARK_OUTPUT)

    turn = tutor("quiz", term="Tabular numbers", answer="leading", progress=["Kerning"], intelligence=fake)

    assert "marked wrong" in fake.requests[0].prompt
    assert turn.answer_correct is False
    assert turn.term == "Tabular numbers"
    assert turn.progress == ["Kerning"]


def test_a_term_already_in_progress_is_not_added_twice() -> None:
    fake = answering(MARK_OUTPUT)

    turn = tutor("quiz", term="Kerning", answer="kerning", progress=["Kerning"], intelligence=fake)

    assert turn.progress == ["Kerning"]


def test_marking_without_the_term_fails_naming_the_flag() -> None:
    fake = answering(MARK_OUTPUT)

    with pytest.raises(UnslopperError, match="--term"):
        tutor("quiz", answer="kerning", intelligence=fake)

    assert fake.requests == []


def test_marks_correct_ignores_case_hyphens_and_end_punctuation_only() -> None:
    term = resolve_term("x-height")

    assert marks_correct("X Height", term)
    assert marks_correct("x-height!", term)
    assert not marks_correct("the x-height", term)
    assert not marks_correct("leading", term)


def test_explain_without_an_image_or_with_a_missing_one_fails_naming_the_flag(tmp_path: Path) -> None:
    fake = answering(EXPLAIN_OUTPUT)

    with pytest.raises(UnslopperError, match="--image"):
        tutor("explain", intelligence=fake)
    with pytest.raises(UnslopperError, match="--image"):
        tutor("explain", image=tmp_path / "missing.png", intelligence=fake)

    assert fake.requests == []


def test_explain_reads_the_image_from_a_read_only_workspace_at_its_parent(tmp_path: Path) -> None:
    image = tmp_path / "shot.png"
    image.write_bytes(b"not really a png")
    fake = answering(EXPLAIN_OUTPUT)

    turn = tutor("explain", image=image, progress=["Kerning"], intelligence=fake)

    [request] = fake.requests
    assert request.workspace is not None
    assert request.workspace.path == tmp_path.resolve()
    assert request.writable is False
    assert request.output_schema == ExplainAnswer.model_json_schema()
    assert "`shot.png`" in request.prompt
    for term in knowledge.TERMS:
        assert term.name in request.prompt
    assert turn.mode == "explain"
    assert turn.term is None
    assert turn.text.startswith(EXPLAIN_SUMMARY)
    assert "- Touch target: 24px icon buttons" in turn.text
    assert "- Tabular numbers: prices" in turn.text
    assert turn.progress == ["Kerning"]
    assert turn.next_term == "Tracking"


def test_an_agent_error_raises_with_a_remedy() -> None:
    fake = FakeIntelligence(AgentResult(error="rate limited"))

    with pytest.raises(UnslopperError) as failure:
        tutor("teach", term="Kerning", intelligence=fake, model="fake-model")

    message = str(failure.value)
    assert "rate limited" in message
    assert "fake-model" in message
    assert "run the same command again" in message


def test_a_run_without_structured_output_raises_rather_than_returning_an_empty_turn() -> None:
    fake = FakeIntelligence(AgentResult(text="prose only"))

    with pytest.raises(UnslopperError, match="no structured answer"):
        tutor("quiz", term="Kerning", intelligence=fake)


def test_unknown_progress_entries_fail_before_any_model_call() -> None:
    fake = answering(TEACH_OUTPUT)

    with pytest.raises(UnslopperError, match="twenty terms"):
        tutor("teach", progress=["serifs"], intelligence=fake)

    assert fake.requests == []


# region: The design-terms-tutor Agent Skill


def terms_reference() -> str:
    """The terms reference the Agent Skill carries, rendered from knowledge in teaching order."""
    lines = [
        "# The twenty design terms",
        "",
        "Generated from `unslopper.knowledge.TERMS` in teaching order; `tests/test_tutor.py` checks it stays in sync.",
        "Each entry is the course's meaning, then why generated designs tend to miss it.",
    ]
    for name in ORDER:
        term = resolve_term(name)
        lines += ["", f"## {term.name}", "", term.meaning, "", f"Why generated designs miss it: {term.ai_note}"]
    return "\n".join(lines) + "\n"


def test_the_agent_skills_terms_reference_matches_knowledge() -> None:
    path = AGENT_SKILL / "references" / "terms.md"

    assert path.read_text(encoding="utf-8") == terms_reference(), (
        f"{path} has drifted from knowledge.TERMS; regenerate it with terms_reference() in this module."
    )


def test_the_agent_skill_has_spec_frontmatter_and_routes_to_the_tool() -> None:
    text = (AGENT_SKILL / "SKILL.md").read_text(encoding="utf-8")
    _, frontmatter, body = text.split("---\n", 2)
    fields = yaml.safe_load(frontmatter)

    assert fields["name"] == AGENT_SKILL.name
    assert 0 < len(fields["description"]) <= 1024
    assert "unslopper tutor" in body
    assert "references/terms.md" in body
    for name in ORDER:
        assert name in body


# endregion
