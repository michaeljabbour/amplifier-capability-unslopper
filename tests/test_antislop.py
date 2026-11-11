"""The antislop pipeline over a slop fixture, with every sibling capability and the model faked."""

from collections.abc import Callable
from pathlib import Path
import shutil
from typing import Any

import pytest

from unslopper.capabilities.antislop import capability as antislop_capability
from unslopper.capabilities.antislop.capability import antislop
from unslopper.capabilities.audit import capability as audit_capability
from unslopper.capabilities.direct import capability as direct_capability
from unslopper.capabilities.texture import capability as texture_capability
from unslopper.capabilities.unslop import capability as unslop_capability
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.schemas import (
    AuditReport,
    Color,
    ContrastResult,
    Direction,
    DirectResult,
    Palette,
    PlannedChange,
    ScanReport,
    TextureRecommendation,
    TextureResult,
    Typography,
    UnslopperError,
    UnslopResult,
)

FIXTURE = Path(__file__).with_name("fixtures") / "antislop-slop.html"
STEP_NAMES = ["audit", "unslop", "direct", "texture", "polish", "audit"]
NO_DIRECTION: dict[str, Any] = {
    "has_direction": False,
    "flat_background": True,
    "inferred_brief": "Ledgerly, a finance platform for small teams.",
    "ground": None,
    "light": None,
    "signal": None,
}
HAS_DIRECTION: dict[str, Any] = {
    **NO_DIRECTION,
    "has_direction": True,
    "ground": "#000412",
    "light": "#E8EEF2",
    "signal": "#2BF08A",
}
CHANGED: dict[str, Any] = {"changed": ["one change"]}


class FakeIntelligence:
    """Answers the pipeline's own calls in order, and edits the working copy when it may write."""

    def __init__(self, answers: list[dict[str, Any] | str], edit: Callable[[Path], None] | None = None) -> None:
        self.implementation = "fake"
        self.answers = list(answers)
        self.edit = edit
        self.requests: list[AgentRequest] = []
        self.preflights = 0

    def preflight(self) -> None:
        self.preflights += 1

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, str):
            return AgentResult(error=answer)
        if request.writable:
            assert request.workspace is not None
            (self.edit or append_marker)(request.workspace.path / FIXTURE.name)
        return AgentResult(output=answer, text="done")


def append_marker(path: Path) -> None:
    path.write_text(path.read_text(encoding="utf-8") + "<!-- polished -->\n", encoding="utf-8")


class Siblings:
    """Fakes for the four sibling capabilities, recording every call's keyword arguments."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, scores: tuple[int, int] = (7, 1)) -> None:
        self.calls: dict[str, list[dict[str, Any]]] = {"audit": [], "unslop": [], "direct": [], "texture": []}
        self.scores = list(scores)
        monkeypatch.setattr(audit_capability, "audit", self.audit)
        monkeypatch.setattr(unslop_capability, "unslop", self.unslop)
        monkeypatch.setattr(direct_capability, "direct", self.direct)
        monkeypatch.setattr(texture_capability, "texture", self.texture)

    def audit(self, **arguments: Any) -> AuditReport:
        self.calls["audit"].append(arguments)
        return audit_report(self.scores.pop(0))

    def unslop(self, path: Path, **arguments: Any) -> UnslopResult:
        self.calls["unslop"].append({"path": path, **arguments})
        text = path.read_text(encoding="utf-8")
        if arguments["write"]:
            path.write_text(text.replace('<span class="pill">New</span> ', ""), encoding="utf-8")
        return UnslopResult(
            path=path,
            plan=[PlannedChange(move="Subtract", fix_id=1, fix="Delete filler badges", change="Dropped the New pill.")],
            diff="--- a\n+++ b\n",
            before=scan_report(6),
            after=scan_report(2),
            written=arguments["write"],
            notes=["Check the hero image still loads."],
        )

    def direct(self, brief: str, **arguments: Any) -> DirectResult:
        self.calls["direct"].append({"brief": brief, **arguments})
        return DirectResult(brief=brief, directions=[direction()])

    def texture(self, **arguments: Any) -> TextureResult:
        self.calls["texture"].append(arguments)
        return TextureResult(
            palette=Palette(ground="#000412", light="#E8EEF2", signal="#2BF08A"),
            recommendations=[TextureRecommendation(name="Speckled graphite", why="Dark, mineral, finance.")],
            texture="Speckled graphite",
            kind="css",
            code="body { background: #000412; }",
            size_bytes=31,
            contrast="Light on ground is 17.8 to 1.",
        )


def audit_report(score: int) -> AuditReport:
    return AuditReport(
        source="copy",
        score=score,
        verdict="slop" if score >= 3 else "clean",
        summary="Gradient, pills and eyebrows." if score >= 3 else "Little left to remove.",
        findings=[],
        fixes_first=["Delete filler badges"],
    )


def scan_report(score: int) -> ScanReport:
    return ScanReport(source="copy", score=score, verdict="slop", hits=[], fixes_first=[])


def direction() -> Direction:
    return Direction(
        scene="A ledger open on a banker's desk under a green lamp.",
        palette=[
            Color(role="ground", name="ink", hex="#000412", oklch="oklch(8% 0.02 265)"),
            Color(role="light", name="paper", hex="#E8EEF2", oklch="oklch(94% 0.01 220)"),
            Color(role="signal", name="lamp green", hex="#2BF08A", oklch="oklch(85% 0.2 155)"),
        ],
        contrast=ContrastResult(
            foreground="#E8EEF2", background="#000412", ratio=17.8, aa_body=True, aa_large=True, aaa_body=True
        ),
        typography=Typography(display="Fraunces", body="Source Sans 3", rationale="A ledger's type."),
        hero="The balance, very large, in tabular figures.",
        css=":root { --ground: #000412; --light: #E8EEF2; --signal: #2BF08A; }",
    )


@pytest.fixture
def page(tmp_path: Path) -> Path:
    return Path(shutil.copyfile(FIXTURE, tmp_path / FIXTURE.name))


def test_a_sloppy_flat_page_runs_every_step(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    Siblings(monkeypatch)
    fake = FakeIntelligence([NO_DIRECTION, CHANGED, CHANGED, {"changed": ["tabular nums", "44px targets"]}])
    original = page.read_text(encoding="utf-8")

    report = antislop(page, with_texture=True, intelligence=fake)

    assert [step.name for step in report.steps] == STEP_NAMES
    assert all(step.ran for step in report.steps)
    assert report.before.score == 7
    assert report.after.score == 1
    assert report.path == page
    assert not report.written
    assert page.read_text(encoding="utf-8") == original
    assert report.diff.startswith(f"--- a/{page.name}\n+++ b/{page.name}\n")
    assert '-    <span class="pill">New</span>' in report.diff
    assert "+<!-- polished -->" in report.diff
    assert fake.preflights == 1
    assert not fake.answers


def test_every_sibling_and_every_own_call_runs_through_the_injected_intelligence(
    monkeypatch: pytest.MonkeyPatch, page: Path
) -> None:
    siblings = Siblings(monkeypatch)
    fake = FakeIntelligence([NO_DIRECTION, CHANGED, CHANGED, CHANGED])

    antislop(page, with_texture=True, model="some-model", reasoning_effort="high", intelligence=fake)

    for name, calls in siblings.calls.items():
        assert calls, name
        for call in calls:
            assert call["intelligence"] is fake
            assert call["model"] == "some-model"
            assert call["reasoning_effort"] == "high"
    assert [call["path"].name for call in siblings.calls["audit"]] == [page.name, page.name]
    assert siblings.calls["unslop"][0]["write"] is True
    assert siblings.calls["unslop"][0]["audit_report"].score == 7
    assert siblings.calls["direct"][0] | {"brief": None} == {
        "brief": None,
        "directions": 1,
        "model": "some-model",
        "reasoning_effort": "high",
        "intelligence": fake,
    }
    assert siblings.calls["direct"][0]["brief"] == NO_DIRECTION["inferred_brief"]
    assert siblings.calls["texture"][0] | {"intelligence": None} == {
        "subject": NO_DIRECTION["inferred_brief"],
        "ground": "#000412",
        "light": "#E8EEF2",
        "signal": "#2BF08A",
        "model": "some-model",
        "reasoning_effort": "high",
        "intelligence": None,
    }
    # The direction read is a plain completion; the three edit passes write in the working directory.
    assert [request.writable for request in fake.requests] == [False, True, True, True]
    assert fake.requests[0].workspace is None
    assert all(request.workspace is not None and request.model == "some-model" for request in fake.requests[1:])


def test_the_direction_read_carries_the_pages_tokens_fonts_backgrounds_and_headings(
    monkeypatch: pytest.MonkeyPatch, page: Path
) -> None:
    Siblings(monkeypatch)
    fake = FakeIntelligence([HAS_DIRECTION, CHANGED])

    antislop(page, intelligence=fake)

    prompt = fake.requests[0].prompt
    assert "Ledgerly. The Next-Generation Finance Platform." in prompt
    assert "Seamlessly Unlock the Power of Effortless Finance." in prompt
    assert 'font-family: "Instrument Serif", serif' in prompt
    assert "background: linear-gradient(135deg, #7c3aed 0%, #2563eb 100%)" in prompt


def test_a_score_below_three_skips_unslop(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    siblings = Siblings(monkeypatch, scores=(2, 1))
    fake = FakeIntelligence([NO_DIRECTION, CHANGED, CHANGED])

    report = antislop(page, intelligence=fake)

    unslop_step = report.steps[1]
    assert unslop_step.name == "unslop"
    assert not unslop_step.ran
    assert "2" in unslop_step.note
    assert not siblings.calls["unslop"]


def test_a_page_with_a_direction_skips_direct(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    siblings = Siblings(monkeypatch)
    fake = FakeIntelligence([HAS_DIRECTION, CHANGED])

    report = antislop(page, intelligence=fake)

    direct_step = report.steps[2]
    assert direct_step.name == "direct"
    assert not direct_step.ran
    assert "#2BF08A" in direct_step.note
    assert not siblings.calls["direct"]
    assert len(fake.requests) == 2


def test_without_with_texture_the_texture_step_is_skipped(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    siblings = Siblings(monkeypatch)
    fake = FakeIntelligence([NO_DIRECTION, CHANGED, CHANGED])

    report = antislop(page, intelligence=fake)

    texture_step = report.steps[3]
    assert texture_step.name == "texture"
    assert not texture_step.ran
    assert "--with-texture" in texture_step.note
    assert not siblings.calls["texture"]


def test_a_textured_background_skips_the_texture_step_even_when_asked(
    monkeypatch: pytest.MonkeyPatch, page: Path
) -> None:
    siblings = Siblings(monkeypatch)
    fake = FakeIntelligence([{**HAS_DIRECTION, "flat_background": False}, CHANGED])

    report = antislop(page, with_texture=True, intelligence=fake)

    assert not report.steps[3].ran
    assert not siblings.calls["texture"]


def test_the_texture_draws_in_the_pages_own_palette_when_the_direction_was_kept(
    monkeypatch: pytest.MonkeyPatch, page: Path
) -> None:
    siblings = Siblings(monkeypatch)
    fake = FakeIntelligence([HAS_DIRECTION, CHANGED, CHANGED])

    report = antislop(page, with_texture=True, intelligence=fake)

    assert report.steps[3].ran
    call = siblings.calls["texture"][0]
    assert (call["ground"], call["light"], call["signal"]) == ("#000412", "#E8EEF2", "#2BF08A")


def test_a_palette_that_is_not_hex_skips_the_texture_step(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    siblings = Siblings(monkeypatch)
    fake = FakeIntelligence([{**HAS_DIRECTION, "ground": "navy"}, CHANGED])

    report = antislop(page, with_texture=True, intelligence=fake)

    assert not report.steps[3].ran
    assert "hex" in report.steps[3].note
    assert not siblings.calls["texture"]


def test_write_replaces_the_original(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    Siblings(monkeypatch)
    fake = FakeIntelligence([HAS_DIRECTION, CHANGED])

    report = antislop(page, write=True, intelligence=fake)

    assert report.written
    text = page.read_text(encoding="utf-8")
    assert text.endswith("<!-- polished -->\n")
    assert '<span class="pill">New</span>' not in text


def test_the_summary_is_three_lines(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    Siblings(monkeypatch)
    fake = FakeIntelligence([NO_DIRECTION, CHANGED, CHANGED, {"changed": ["tabular nums"]}])

    report = antislop(page, with_texture=True, intelligence=fake)

    lines = report.summary.splitlines()
    assert len(lines) == 3
    assert lines[0] == "Score 7/20 before, 1/20 after."
    assert lines[1].startswith("Biggest moves: ")
    assert "Delete filler badges" in lines[1]
    assert "Fraunces" in lines[1]
    assert "speckled graphite" in lines[1]
    assert "1 polish edits" in lines[1]
    assert lines[2].startswith("Check by hand: Check the hero image still loads")


def test_a_dropped_link_target_fails_and_leaves_the_original(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    Siblings(monkeypatch)

    def drop_pricing(path: Path) -> None:
        path.write_text(
            path.read_text(encoding="utf-8").replace('<a href="/pricing">Pricing</a>', ""), encoding="utf-8"
        )

    fake = FakeIntelligence([HAS_DIRECTION, CHANGED], edit=drop_pricing)
    original = page.read_text(encoding="utf-8")

    with pytest.raises(UnslopperError) as failure:
        antislop(page, write=True, intelligence=fake)

    assert "/pricing" in str(failure.value)
    assert "untouched" in str(failure.value)
    assert page.read_text(encoding="utf-8") == original


def test_a_failing_sibling_names_its_step(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    Siblings(monkeypatch)

    def broken(path: Path, **arguments: Any) -> UnslopResult:
        raise UnslopperError("The unslop agent failed: out of tokens.")

    monkeypatch.setattr(unslop_capability, "unslop", broken)
    original = page.read_text(encoding="utf-8")

    with pytest.raises(UnslopperError) as failure:
        antislop(page, write=True, intelligence=FakeIntelligence([]))

    assert str(failure.value).startswith("The unslop step failed: The unslop agent failed: out of tokens.")
    assert "untouched" in str(failure.value)
    assert page.read_text(encoding="utf-8") == original


def test_an_agent_error_in_an_own_call_names_its_step(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    Siblings(monkeypatch)

    with pytest.raises(UnslopperError) as failure:
        antislop(page, intelligence=FakeIntelligence(["The agent did not finish within 300 seconds."]))

    assert str(failure.value).startswith("The direct step failed: The agent did not finish")


def test_a_non_html_path_is_refused_before_any_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    siblings = Siblings(monkeypatch)
    fake = FakeIntelligence([])
    notes = tmp_path / "notes.txt"
    notes.write_text("hello", encoding="utf-8")

    for path in (notes, tmp_path / "missing.html"):
        with pytest.raises(UnslopperError) as failure:
            antislop(path, intelligence=fake)
        assert "not an HTML or CSS file" in str(failure.value)

    assert fake.preflights == 0
    assert not siblings.calls["audit"]


def test_every_template_renders_with_only_what_the_pipeline_passes() -> None:
    assert (
        "finance"
        in antislop_capability.render("direction.md.liquid", **antislop_capability.page_facts(FIXTURE)).lower()
    )
    assert "Fraunces" in antislop_capability.render(
        "apply-direction.md.liquid",
        file_name="x.html",
        scene="s",
        palette=[color.model_dump() for color in direction().palette],
        typography=direction().typography.model_dump(),
        css=":root {}",
    )
    for kind in ("css", "canvas"):
        rendered = antislop_capability.render(
            "apply-texture.md.liquid", file_name="x.html", texture="Halftone", kind=kind, code="x", contrast="c"
        )
        assert ("<canvas>" in rendered) == (kind == "canvas")
    assert "45 to 75" in antislop_capability.render("polish.md.liquid", file_name="x.html")


def test_reports_name_the_callers_file_not_the_scratch_copy(monkeypatch: pytest.MonkeyPatch, page: Path) -> None:
    Siblings(monkeypatch, scores=(2, 1))

    report = antislop(page, intelligence=FakeIntelligence([NO_DIRECTION, CHANGED, CHANGED]))

    assert report.before.source == str(page)
    assert report.after.source == str(page)
