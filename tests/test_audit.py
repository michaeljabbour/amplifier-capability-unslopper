"""The model-backed audit with a fake intelligence: what the prompt carries, how the report is built, how it fails."""

from pathlib import Path
from typing import Any

import pytest

from unslopper import knowledge, lib
from unslopper.capabilities.audit import capability
from unslopper.capabilities.audit.capability import AuditAnswer
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.schemas import UnslopperError

FIXTURES = Path(__file__).parent / "fixtures"
SLOP_CARD = FIXTURES / "audit-slop-card.html"
REPOSITORY = Path(__file__).parents[1]

ANSWER: dict[str, Any] = {
    "summary": "A feature card built from every default at once.",
    "findings": [
        {
            "indicator": "Eyebrows",
            "layer": "Structure",
            "location": '<div class="eb"> (line 31)',
            "evidence": '"02 \u00b7 PLAN" above the heading',
            "deliberate": False,
            "rationale": "Repeats the heading and implies an order that does not exist.",
            "impact": "low",
        },
        {
            "indicator": "Gradient backgrounds",
            "layer": "Surface",
            "location": ".slop (line 14)",
            "evidence": "linear-gradient(135deg,#6E4CF5 0%,#3B82F6 55%,#22D3EE 100%)",
            "deliberate": False,
            "rationale": "The purple to blue diagonal with nothing from the product's world behind it.",
            "impact": "high",
        },
        {
            "indicator": "Excessive mono fonts",
            "layer": "Type",
            "location": ".slop .crumb (line 22)",
            "evidence": "JetBrains Mono on a decorative path",
            "deliberate": True,
            "rationale": "The product is a coding agent and the path is the kind of thing it prints.",
            "impact": "medium",
        },
    ],
    "score": 2,
    "fixes_first": ["Drop redundant labels", "Add an accent colour", "Mono only where needed", "Use a design system"],
}


class FakeIntelligence:
    """Records the request and answers with a canned result."""

    def __init__(self, result: AgentResult) -> None:
        self.implementation = "fake"
        self.result = result
        self.requests: list[AgentRequest] = []
        self.preflights = 0

    def preflight(self) -> None:
        self.preflights += 1

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        return self.result


def test_the_prompt_carries_the_source_the_scan_and_the_catalog() -> None:
    fake = FakeIntelligence(AgentResult(output=ANSWER))

    report = lib.audit(path=SLOP_CARD, intelligence=fake, model="some-model")

    assert fake.preflights == 1
    [request] = fake.requests
    assert request.model == "some-model"
    assert request.workspace is None
    assert request.output_schema == AuditAnswer.model_json_schema()
    assert request.reasoning_effort == "medium"
    assert request.timeout_seconds > 0
    assert SLOP_CARD.read_text(encoding="utf-8") in request.prompt
    assert report.scan is not None
    assert report.scan.model_dump_json(indent=2) in request.prompt
    for indicator in knowledge.INDICATORS:
        assert f"- {indicator.name} ({indicator.layer}): {indicator.description}" in request.prompt
    for fix in knowledge.FIXES:
        assert f"- {fix.name} ({fix.move})" in request.prompt
    assert "repeats consistently" in request.prompt
    assert "never rewrite" in request.prompt
    assert "When it is fine" in request.prompt or "when it is fine" in request.prompt


def test_the_report_is_assembled_from_the_answer() -> None:
    fake = FakeIntelligence(AgentResult(output=ANSWER))

    report = lib.audit(path=SLOP_CARD, intelligence=fake)

    assert report.source == str(SLOP_CARD)
    assert report.summary == ANSWER["summary"]
    assert report.score == 2
    assert report.verdict == knowledge.verdict(2)
    assert [finding.indicator for finding in report.findings] == [
        "Gradient backgrounds",
        "Excessive mono fonts",
        "Eyebrows",
    ]
    assert report.findings[1].deliberate
    assert report.fixes_first == ["Drop redundant labels", "Add an accent colour", "Mono only where needed"]
    assert report.scan is not None
    assert report.scan.source == str(SLOP_CARD)
    assert report.scan.score >= 10


def test_fixes_come_from_the_catalog_when_the_model_names_none() -> None:
    answer = {**ANSWER, "fixes_first": []}
    fake = FakeIntelligence(AgentResult(output=answer))

    report = lib.audit(path=SLOP_CARD, intelligence=fake)

    defaults = [finding["indicator"] for finding in ANSWER["findings"] if not finding["deliberate"]]
    assert report.fixes_first == [fix.name for fix in knowledge.fixes_for(defaults)][:3]


def test_a_stylesheet_or_inline_source_is_audited_the_same_way() -> None:
    fake = FakeIntelligence(AgentResult(output=ANSWER))

    report = lib.audit(source=".hero{background:linear-gradient(135deg,#7c3aed,#2563eb)}", intelligence=fake)

    assert report.source == "inline"
    assert report.scan is not None
    assert [hit.indicator for hit in report.scan.hits] == ["Gradient backgrounds"]
    assert "```css" in fake.requests[0].prompt


def test_a_very_long_source_is_truncated_and_the_prompt_says_so() -> None:
    fake = FakeIntelligence(AgentResult(output=ANSWER))
    source = "<div>" + "x" * (capability.MAX_SOURCE_CHARS + 500) + "</div>"

    lib.audit(source=source, intelligence=fake)

    prompt = fake.requests[0].prompt
    assert "It is truncated" in prompt
    assert source not in prompt
    assert source[: capability.MAX_SOURCE_CHARS] in prompt


def test_an_image_runs_read_only_in_its_own_directory(tmp_path: Path) -> None:
    image = tmp_path / "hero.png"
    image.write_bytes(b"\x89PNG\r\n\x1a\n")
    fake = FakeIntelligence(AgentResult(output=ANSWER))

    report = lib.audit(image=image, intelligence=fake)

    [request] = fake.requests
    assert request.workspace is not None
    assert request.workspace.path == tmp_path.resolve()
    assert not request.writable
    assert "`hero.png`" in request.prompt
    assert "Read tool" in request.prompt
    assert "Do not modify" in request.prompt
    assert "What static heuristics found" not in request.prompt
    assert report.scan is None
    assert report.source == str(image.resolve())


def test_a_non_image_path_given_as_image_is_refused(tmp_path: Path) -> None:
    fake = FakeIntelligence(AgentResult(output=ANSWER))

    with pytest.raises(UnslopperError, match="is not an image file"):
        lib.audit(image=tmp_path / "page.html", intelligence=fake)


@pytest.mark.parametrize(
    "inputs",
    [{}, {"path": SLOP_CARD, "url": "https://example.invalid"}, {"image": SLOP_CARD, "source": "<p>x</p>"}],
    ids=["none", "path and url", "image and source"],
)
def test_exactly_one_input_is_required(inputs: dict[str, Any]) -> None:
    fake = FakeIntelligence(AgentResult(output=ANSWER))

    with pytest.raises(UnslopperError, match="exactly one"):
        lib.audit(intelligence=fake, **inputs)
    assert fake.requests == []


def test_plain_text_is_refused_before_any_model_call() -> None:
    fake = FakeIntelligence(AgentResult(output=ANSWER))

    with pytest.raises(UnslopperError, match="neither HTML nor CSS"):
        lib.audit(source="some words", intelligence=fake)
    assert fake.requests == []


def test_a_run_error_becomes_an_error_with_a_remedy() -> None:
    fake = FakeIntelligence(AgentResult(error="The agent did not finish within 600 seconds."))

    with pytest.raises(UnslopperError) as failure:
        lib.audit(path=SLOP_CARD, intelligence=fake)

    message = str(failure.value)
    assert "did not finish within 600 seconds" in message
    assert "fake" in message
    assert "run the audit again" in message


def test_a_malformed_answer_becomes_an_error_with_a_remedy() -> None:
    fake = FakeIntelligence(AgentResult(output={"summary": "x", "findings": [{"indicator": "Nope"}], "score": 50}))

    with pytest.raises(UnslopperError) as failure:
        lib.audit(path=SLOP_CARD, intelligence=fake)

    message = str(failure.value)
    assert "did not match the audit's shape" in message
    assert "--model" in message


def test_an_indicator_outside_the_catalog_is_named() -> None:
    answer = {**ANSWER, "findings": [{**ANSWER["findings"][0], "indicator": "Comic Sans"}]}
    fake = FakeIntelligence(AgentResult(output=answer))

    with pytest.raises(UnslopperError, match="Comic Sans"):
        lib.audit(path=SLOP_CARD, intelligence=fake)


def test_the_answer_schema_only_admits_catalog_indicator_names() -> None:
    schema = AuditAnswer.model_json_schema()

    assert schema["$defs"]["AnswerFinding"]["properties"]["indicator"]["enum"] == [
        indicator.name for indicator in knowledge.INDICATORS
    ]


def test_the_indicator_notes_cover_the_catalog_and_ship_identically_in_the_agent_skill() -> None:
    notes = capability.INDICATORS_FILE.read_text(encoding="utf-8")
    skill_copy = (REPOSITORY / "skills" / "design-slop-audit" / "references" / "indicators.md").read_text(
        encoding="utf-8"
    )

    assert notes == skill_copy
    for indicator in knowledge.INDICATORS:
        assert f"### {indicator.name}\n" in notes
