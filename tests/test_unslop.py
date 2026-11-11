"""Drives `unslop` with a fake intelligence that edits the workspace copy and a fake scan, so no model is needed."""

from collections.abc import Callable
import json
from pathlib import Path
import shutil
from typing import Any

import pytest

from unslopper.capabilities.audit import capability as audit_capability
from unslopper.capabilities.unslop import capability as unslop_capability
from unslopper.capabilities.unslop.capability import MOVE_ORDER, TIMEOUT_SECONDS, UnslopAnswer, unslop
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.knowledge import FIXES
from unslopper.schemas import AuditReport, PlannedChange, ScanReport, UnslopperError

FIXTURES = Path(__file__).parent / "fixtures"
PILL = '<span class="pill">NEW</span>'
VERBOSE = (
    "Our powerful AI-driven planning engine lets you seamlessly see the plan before any changes are made, "
    "empowering you to edit, reorder, or reject it with confidence."
)
PLAIN = "The agent lists every step and the files it will change. Edit, reorder or reject it and nothing runs."
ANSWER = UnslopAnswer(
    plan=[
        PlannedChange(move="Subtract", fix_id=1, fix="Delete filler badges", change="Removed the NEW pill."),
        PlannedChange(move="Focus", fix_id=9, fix="Make headlines specific", change="Shortened the copy."),
    ],
    notes=["Check the shortened copy still says what you mean."],
)

Edit = Callable[[str], str]


def remove_pill_and_shorten(text: str) -> str:
    return text.replace(PILL, "").replace(VERBOSE, PLAIN)


class FakeIntelligence:
    """Edits the file in the request's workspace the way an agent would, then answers with the canned plan."""

    def __init__(self, edit: Edit = remove_pill_and_shorten, error: str | None = None) -> None:
        self.implementation = "fake"
        self.edit = edit
        self.error = error
        self.preflighted = False
        self.requests: list[AgentRequest] = []

    def preflight(self) -> None:
        self.preflighted = True

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        assert request.workspace is not None
        target = request.workspace.path / "unslop-card.html"
        if not target.exists():
            target = request.workspace.path / "unslop-card.css"
        target.write_text(self.edit(target.read_text(encoding="utf-8")), encoding="utf-8")
        if self.error is not None:
            return AgentResult(error=self.error)
        return AgentResult(output=ANSWER.model_dump(mode="json"), text="done")


def fake_scan(source: str | None = None, path: Path | None = None, url: str | None = None) -> ScanReport:
    text = path.read_text(encoding="utf-8") if path is not None else (source or "")
    score = 3 if PILL in text else 1
    return ScanReport(
        source=str(path) if path is not None else "inline",
        score=score,
        verdict="Some defaults showing",
        hits=[],
        fixes_first=["Delete filler badges"],
    )


@pytest.fixture
def scans(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    def record(source: str | None = None, path: Path | None = None, url: str | None = None) -> ScanReport:
        calls.append({"source": source, "path": path, "url": url})
        return fake_scan(source, path, url)

    monkeypatch.setattr(audit_capability, "scan", record)
    return calls


@pytest.fixture
def page(tmp_path: Path) -> Path:
    return Path(shutil.copy(FIXTURES / "unslop-card.html", tmp_path))


@pytest.fixture
def sheet(tmp_path: Path) -> Path:
    return Path(shutil.copy(FIXTURES / "unslop-card.css", tmp_path))


def test_proposes_a_diff_without_touching_the_file(page: Path, scans: list[dict[str, Any]]) -> None:
    original = page.read_text(encoding="utf-8")
    fake = FakeIntelligence()

    result = unslop(page, intelligence=fake)

    assert fake.preflighted
    assert result.path == page
    assert result.written is False
    assert page.read_text(encoding="utf-8") == original
    assert result.diff.startswith("--- a/unslop-card.html\n+++ b/unslop-card.html\n")
    assert f'-    <div class="eb">02 - PLAN {PILL}</div>' in result.diff
    assert PLAIN in result.diff
    assert result.plan == ANSWER.plan
    assert result.notes == ANSWER.notes


def test_scans_the_file_before_and_the_edited_text_after(page: Path, scans: list[dict[str, Any]]) -> None:
    result = unslop(page, intelligence=FakeIntelligence())

    assert [call["path"] for call in scans] == [page, None]
    assert scans[1]["source"] is not None
    assert PILL not in scans[1]["source"]
    assert result.before.score == 3
    assert result.after.score == 1


def test_write_replaces_the_file_and_keeps_its_newline_style(page: Path, scans: list[dict[str, Any]]) -> None:
    page.write_bytes(page.read_bytes().replace(b"\n", b"\r\n"))

    result = unslop(page, write=True, intelligence=FakeIntelligence())

    written = page.read_bytes()
    assert result.written is True
    assert PILL.encode() not in written
    assert PLAIN.encode() in written
    assert b"\r\n" in written
    assert b"\n" not in written.replace(b"\r\n", b"")


def test_the_agent_works_on_a_copy_in_a_fresh_writable_workspace(page: Path, scans: list[dict[str, Any]]) -> None:
    fake = FakeIntelligence()

    unslop(page, intelligence=fake, reasoning_effort="high")

    (request,) = fake.requests
    assert request.workspace is not None
    assert request.workspace.path != page.parent
    assert request.writable is True
    assert request.output_schema == UnslopAnswer.model_json_schema()
    assert request.reasoning_effort == "high"
    assert request.timeout_seconds == TIMEOUT_SECONDS
    assert not request.workspace.path.exists()


def test_the_prompt_carries_the_file_the_moves_in_order_the_fixes_and_the_scan(
    page: Path, scans: list[dict[str, Any]]
) -> None:
    fake = FakeIntelligence()

    unslop(page, intelligence=fake)

    prompt = fake.requests[0].prompt
    assert "`unslop-card.html`" in prompt
    positions = [prompt.index(f"## {move}") for move in MOVE_ORDER]
    assert positions == sorted(positions)
    for fix in FIXES:
        assert fix.how in prompt
    assert json.dumps(str(page))[1:-1] in prompt
    assert "What the audit judged" not in prompt
    assert "prefers-reduced-motion" in prompt


def test_an_audit_report_is_passed_to_the_agent(page: Path, scans: list[dict[str, Any]]) -> None:
    fake = FakeIntelligence()
    audit = AuditReport(
        source=str(page),
        score=4,
        verdict="Some defaults showing",
        summary="A gradient card with a filler pill.",
        findings=[],
        fixes_first=["Delete filler badges", "Make headlines specific"],
    )

    unslop(page, audit_report=audit, intelligence=fake)

    prompt = fake.requests[0].prompt
    assert "What the audit judged" in prompt
    assert "A gradient card with a filler pill." in prompt


def test_a_dropped_link_is_refused_and_the_file_left_alone(page: Path, scans: list[dict[str, Any]]) -> None:
    original = page.read_text(encoding="utf-8")

    def drop_docs_link(text: str) -> str:
        return text.replace('<a href="/docs">Learn more -></a> ', "")

    with pytest.raises(UnslopperError) as failure:
        unslop(page, write=True, intelligence=FakeIntelligence(edit=drop_docs_link))

    assert "/docs" in str(failure.value)
    assert "untouched" in str(failure.value)
    assert page.read_text(encoding="utf-8") == original


def test_a_replaced_stylesheet_link_is_not_a_dropped_link(page: Path, scans: list[dict[str, Any]]) -> None:
    fonts = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Instrument+Serif">'
    page.write_text(page.read_text(encoding="utf-8").replace("<head>", "<head>" + fonts, 1), encoding="utf-8")

    def swap_font(text: str) -> str:
        return remove_pill_and_shorten(text.replace(fonts, ""))

    result = unslop(page, intelligence=FakeIntelligence(edit=swap_font))

    assert "-" + fonts in result.diff.replace("<head>", "<head>\n-", 1) or fonts in result.diff
    assert result.written is False
    assert result.plan == ANSWER.plan


def test_a_dropped_form_is_refused_even_when_its_action_survives(page: Path, scans: list[dict[str, Any]]) -> None:
    def unwrap_form(text: str) -> str:
        return text.replace('<form action="/subscribe" method="post">', "<div data-was=/subscribe>").replace(
            "</form>", "</div>"
        )

    with pytest.raises(UnslopperError, match="<form>"):
        unslop(page, intelligence=FakeIntelligence(edit=unwrap_form))


def test_an_emptied_file_is_refused(page: Path, scans: list[dict[str, Any]]) -> None:
    with pytest.raises(UnslopperError, match="empty"):
        unslop(page, intelligence=FakeIntelligence(edit=lambda text: "  \n"))


def test_an_agent_error_is_raised_with_the_original_untouched(page: Path, scans: list[dict[str, Any]]) -> None:
    original = page.read_text(encoding="utf-8")

    with pytest.raises(UnslopperError) as failure:
        unslop(page, write=True, intelligence=FakeIntelligence(error="The agent did not finish within 1800 seconds."))

    message = str(failure.value)
    assert "did not finish" in message
    assert "untouched" in message
    assert page.read_text(encoding="utf-8") == original
    assert len(scans) == 1


def test_a_css_file_is_edited_without_link_checks(sheet: Path, scans: list[dict[str, Any]]) -> None:
    def drop_the_pill_rule(text: str) -> str:
        return "\n".join(line for line in text.splitlines() if ".pill" not in line) + "\n"

    result = unslop(sheet, intelligence=FakeIntelligence(edit=drop_the_pill_rule))

    assert result.diff.startswith("--- a/unslop-card.css\n+++ b/unslop-card.css\n")
    assert "-.card .pill" in result.diff


@pytest.mark.parametrize("name", ["notes.txt", "missing.html"])
def test_anything_but_an_existing_html_or_css_file_is_refused(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    if path.suffix == ".txt":
        path.write_text("hello", encoding="utf-8")
    fake = FakeIntelligence()

    with pytest.raises(UnslopperError, match=r"\.html, \.htm or \.css"):
        unslop(path, intelligence=fake)

    assert not fake.preflighted


def test_the_template_renders_every_fix_from_knowledge_once() -> None:
    prompt = unslop_capability.render_prompt("page.html", fake_scan(source="<p>x</p>"), None)

    for fix in FIXES:
        assert prompt.count(f"Fix {fix.id}, {fix.name}:") == 1
