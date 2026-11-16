"""Paired editorial fixtures, scope confounds, and model-path fidelity without live model calls."""

from collections import Counter
from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

import pytest

from unslopper.capabilities.prose.capability import (
    FIDELITY_WARNING,
    ProseAuditAnswer,
    ProseEditAnswer,
    audit_prose,
    scan_prose,
    unslop_prose,
)
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.prose import MAX_PROSE_CHARS, check_fidelity, protected_spans, scoped_text
from unslopper.schemas import ProseFinding, UnslopperError

FIXTURES = Path(__file__).parents[0] / "fixtures"
PAIRS: list[dict[str, Any]] = json.loads((FIXTURES / "prose-pairs.json").read_text(encoding="utf-8"))
CALIBRATED = "Most samples may remain stable for about 7 days (Lee et al., 2025) [1].\n"
ORIGINAL = "It is important to note that " + CALIBRATED[0].lower() + CALIBRATED[1:]


class FakeIntelligence:
    """Returns inspectable local structured outputs; no model SDK or network is involved."""

    implementation = "fake"

    def __init__(self, output: dict[str, Any] | None = None, error: str | None = None) -> None:
        self.output = output
        self.error = error
        self.requests: list[AgentRequest] = []
        self.preflighted = False

    def preflight(self) -> None:
        self.preflighted = True

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        return AgentResult(output=self.output, error=self.error)


@pytest.mark.parametrize("pair", PAIRS, ids=[pair["name"] for pair in PAIRS])
def test_paired_candidates_and_legitimate_twins(pair: dict[str, Any]) -> None:
    for key, expected in (("problem", "expected_rules"), ("legitimate", "legitimate_rules")):
        text = pair[key]
        report = scan_prose(source=text)
        assert Counter(found.rule_id for found in report.findings) == Counter(pair[expected])
        assert report.authorship == "not_assessed"
        assert "score" not in report.model_dump()
        for found in report.findings:
            assert text[found.start : found.end] == found.evidence
            assert found.line == text.count("\n", 0, found.start) + 1
            assert found.disposition == "review"
            assert found.category == ("objective" if found.rule_id == "duplicate-word" else "review")


def test_scan_needs_no_intelligence_or_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    from unslopper.capabilities.prose import capability

    def fail(*args: Any, **kwargs: Any) -> None:
        pytest.fail("A deterministic prose scan must not select a model.")

    monkeypatch.setattr(capability, "select_intelligence", fail)
    assert scan_prose(source=ORIGINAL).findings


@pytest.mark.parametrize("text", ["the `payload` the", 'the "quoted" the', "the [1] the"])
def test_masked_spans_do_not_bridge_into_accidental_duplicates(text: str) -> None:
    assert scan_prose(source=text).findings == []


def test_scope_keeps_offsets_and_protects_unclosed_fences_and_curly_quotes() -> None:
    text = "A note.\n\u201cMake no mistake, keep this.\u201d\n```text\nIt is important to note that the the payload is literal."
    scoped, spans = scoped_text(text)
    assert len(scoped) == len(text)
    assert scoped.count("\n") == text.count("\n")
    assert {span.kind for span in spans} == {"quotation", "code"}
    assert scan_prose(source=text).findings == []


@pytest.mark.parametrize(
    "text",
    [
        "> Quoted introduction\nIt is important to note that most teams may need review.\n",
        'The witness said, "A first line.\nIt is important to note that most teams may need review."\n',
        "The witness said, \u201cA first line.\nIt is important to note that most teams may need review.\u201d\n",
    ],
)
def test_lazy_markdown_blockquotes_and_multiline_quotations_are_protected(text: str) -> None:
    assert scan_prose(source=text).findings == []
    with pytest.raises(UnslopperError, match="protected"):
        check_fidelity(text, text.replace("It is important to note that ", ""))


@pytest.mark.parametrize(
    "text",
    [
        "'I don't consent.'",
        "\u2018I don\u2019t consent.\u2019",
        "'I don't consent.\nIt is important to note that I don't.'",
    ],
)
def test_quoted_speech_with_contractions_is_protected(text: str) -> None:
    assert scan_prose(source=text).findings == []
    with pytest.raises(UnslopperError, match="protected"):
        check_fidelity(text, text.replace("consent", "agree"))


def test_markdown_file_reports_its_scope(tmp_path: Path) -> None:
    path = tmp_path / "draft.md"
    path.write_text("# Draft\n" + ORIGINAL, encoding="utf-8")
    report = scan_prose(path=path)
    assert report.source == str(path)
    assert report.source_kind == "markdown"
    assert report.findings[0].line == 2
    assert report.warnings
    assert "partial" in report.warnings[0]


@pytest.mark.parametrize(
    ("source", "path"), [(None, None), ("text", Path("draft.txt")), ("", None), ("x" * (MAX_PROSE_CHARS + 1), None)]
)
def test_bad_sources_fail_before_selecting_a_model(source: str | None, path: Path | None) -> None:
    with pytest.raises(UnslopperError):
        scan_prose(source=source, path=path)


def test_non_text_or_missing_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "draft.html"
    path.write_text("<p>words</p>", encoding="utf-8")
    with pytest.raises(UnslopperError, match="prose file"):
        scan_prose(path=path)
    with pytest.raises(UnslopperError, match="prose file"):
        scan_prose(path=tmp_path / "missing.txt")


def audit_output(text: str, disposition: str = "keep") -> dict[str, Any]:
    finding = scan_prose(source=text).findings[0].model_dump()
    finding.update(disposition=disposition, rationale="The speaker intentionally emphasizes this sentence.")
    return {"summary": "Keep the deliberate voice.", "findings": [finding], "warnings": []}


def test_contextual_audit_can_keep_intentional_rhetoric_and_forward_model_options() -> None:
    text = "Make no mistake, we wait, we watch, we listen."
    fake = FakeIntelligence(audit_output(text))
    report = audit_prose(source=text, intelligence=fake, model="test/model", reasoning_effort="high")
    assert report.findings[0].disposition == "keep"
    assert report.authorship == "not_assessed"
    assert fake.preflighted
    (request,) = fake.requests
    assert request.model == "test/model"
    assert request.reasoning_effort == "high"
    assert request.workspace is None
    assert request.writable is False
    assert request.output_schema == ProseAuditAnswer.model_json_schema()
    assert "untrusted data" in request.prompt
    assert text in request.prompt


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("start", 4),
        ("evidence", "fabricated"),
        ("line", 2),
        ("rule_id", "passive-voice"),
        ("category", "objective"),
        ("end", 9000),
    ],
)
def test_audit_rejects_ungrounded_evidence_and_invented_objective_rules(field: str, value: str | int) -> None:
    output = audit_output(ORIGINAL)
    output["findings"][0][field] = value
    with pytest.raises(UnslopperError, match="ungrounded"):
        audit_prose(source=ORIGINAL, intelligence=FakeIntelligence(output))


def test_audit_rejects_findings_inside_quotations() -> None:
    text = 'She said, "Make no mistake, the gate is shut."'
    start = text.index("Make no mistake")
    found = ProseFinding(
        rule_id="performative-emphasis",
        category="review",
        start=start,
        end=start + 15,
        line=1,
        evidence=text[start : start + 15],
        rationale="Candidate",
    )
    output = {"summary": "Review", "findings": [found.model_dump()], "warnings": []}
    with pytest.raises(UnslopperError, match="protected-span"):
        audit_prose(source=text, intelligence=FakeIntelligence(output))


def test_audit_rejects_fabricated_duplicate_word_objective() -> None:
    text = "Most teams may need review."
    found = ProseFinding(
        rule_id="duplicate-word", category="objective", start=0, end=4, line=1, evidence="Most", rationale="Fabricated"
    )
    with pytest.raises(UnslopperError, match="ungrounded"):
        audit_prose(source=text, intelligence=FakeIntelligence({"summary": "Review", "findings": [found.model_dump()]}))


def test_uncertain_judgment_survives_the_audit() -> None:
    report = audit_prose(source=ORIGINAL, intelligence=FakeIntelligence(audit_output(ORIGINAL, "uncertain")))
    assert report.findings[0].disposition == "uncertain"


def test_edit_returns_diff_proposed_text_and_scans_without_writing(tmp_path: Path) -> None:
    path = tmp_path / "draft.md"
    path.write_text(ORIGINAL, encoding="utf-8")
    fake = FakeIntelligence({"proposed_text": CALIBRATED, "notes": ["Removed an empty announcement."]})
    report = unslop_prose(path, intelligence=fake)
    assert path.read_text(encoding="utf-8") == ORIGINAL
    assert report.proposed_text == CALIBRATED
    assert report.diff.startswith("--- a/draft.md\n+++ b/draft.md\n")
    assert report.before.findings
    assert report.after.findings == []
    assert report.written is False
    assert FIDELITY_WARNING in report.notes
    assert fake.requests[0].output_schema == ProseEditAnswer.model_json_schema()
    assert fake.requests[0].workspace is None


def test_requested_write_preserves_crlf_and_unchanged_edit_is_valid(tmp_path: Path) -> None:
    path = tmp_path / "draft.txt"
    path.write_bytes(ORIGINAL.replace("\n", "\r\n").encode())
    report = unslop_prose(path, write=True, intelligence=FakeIntelligence({"proposed_text": CALIBRATED, "notes": []}))
    assert report.written is True
    assert path.read_bytes() == CALIBRATED.replace("\n", "\r\n").encode()
    kept = unslop_prose(path, intelligence=FakeIntelligence({"proposed_text": CALIBRATED, "notes": []}))
    assert kept.diff == ""


def test_matching_audit_is_forwarded_and_mismatched_source_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "draft.md"
    path.write_text(ORIGINAL, encoding="utf-8")
    audit = audit_prose(path=path, intelligence=FakeIntelligence(audit_output(ORIGINAL)))
    fake = FakeIntelligence({"proposed_text": ORIGINAL, "notes": []})
    unslop_prose(path, audit_report=audit, intelligence=fake)
    assert "Prior contextual review" in fake.requests[0].prompt
    assert '"disposition": "keep"' in fake.requests[0].prompt
    audit.source = "other.md"
    with pytest.raises(UnslopperError, match="different source"):
        unslop_prose(path, audit_report=audit, intelligence=fake)


@pytest.mark.parametrize("disposition", ["keep", "uncertain"])
def test_edit_preserves_keep_or_uncertain_audit_evidence(tmp_path: Path, disposition: str) -> None:
    text = "It is important to note that the gate closed."
    path = tmp_path / "draft.md"
    path.write_text(text, encoding="utf-8")
    audit = audit_prose(path=path, intelligence=FakeIntelligence(audit_output(text, disposition)))
    with pytest.raises(UnslopperError, match="keep or uncertain"):
        unslop_prose(
            path, write=True, audit_report=audit, intelligence=FakeIntelligence({"proposed_text": "The gate closed."})
        )
    assert path.read_text(encoding="utf-8") == text


@pytest.mark.parametrize(
    "edit",
    [
        lambda text: text.replace("7", "8"),
        lambda text: text.replace("most ", ""),
        lambda text: text.replace("may ", ""),
        lambda text: text.replace("[1]", "[2]"),
        lambda text: "",
    ],
)
def test_fidelity_failure_leaves_requested_write_untouched(tmp_path: Path, edit: Callable[[str], str]) -> None:
    path = tmp_path / "draft.txt"
    path.write_text(ORIGINAL, encoding="utf-8")
    fake = FakeIntelligence({"proposed_text": edit(ORIGINAL), "notes": []})
    with pytest.raises(UnslopperError, match="untouched"):
        unslop_prose(path, write=True, intelligence=fake)
    assert path.read_text(encoding="utf-8") == ORIGINAL


@pytest.mark.parametrize(
    "protected",
    [
        '"The result is not certain."',
        "`retry(7)`",
        "[guide](https://example.test/7)",
        "[1]",
        "[@lee2025]",
        "(Lee et al., 2025)",
        "(Liang, 2023)",
        "Liang (2023)",
        "> Most samples may fail.\n",
        "## References\nLee. Notes. 2025.\n",
    ],
)
def test_fidelity_preserves_quotes_code_citations_references_and_urls(protected: str) -> None:
    text = "Read this.\n" + protected
    assert protected_spans(text)
    with pytest.raises(UnslopperError, match="protected"):
        check_fidelity(text, "Read this.\nChanged source.")
    check_fidelity(text, "Read this carefully.\n" + protected)


@pytest.mark.parametrize(
    ("output", "error"), [(None, None), ({"summary": "wrong schema"}, None), (None, "network unavailable")]
)
def test_model_failures_name_the_problem_without_writing(
    tmp_path: Path, output: dict[str, Any] | None, error: str | None
) -> None:
    path = tmp_path / "draft.txt"
    path.write_text(ORIGINAL, encoding="utf-8")
    with pytest.raises(UnslopperError, match="untouched"):
        unslop_prose(path, write=True, intelligence=FakeIntelligence(output, error))
    assert path.read_text(encoding="utf-8") == ORIGINAL
