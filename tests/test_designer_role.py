"""Offline role boundaries for design evidence and intentional existing choices."""

from pathlib import Path
from typing import Any

import pytest

from unslopper.capabilities.antislop import capability as pipeline_capability
from unslopper.capabilities.audit import capability as audit_capability
from unslopper.capabilities.direct import capability as direct_capability
from unslopper.capabilities.texture import capability as texture_capability
from unslopper.capabilities.unslop import capability as unslop_capability
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.roles import role_contract_text

MONOCHROME_PAGE = """<html><title>Archive</title><style>
:root { --ground: #ffffff; --light: #111111; }
body { font-family: system-ui; background: var(--ground); color: var(--light); }
</style><h1>Archive</h1><p>Read the record.</p></html>"""


class FakeIntelligence:
    """Return controlled judgments while retaining the actual prompt and tool boundaries."""

    implementation = "fake"

    def __init__(self, *outputs: dict[str, Any]) -> None:
        self.outputs = list(outputs)
        self.requests: list[AgentRequest] = []

    def preflight(self) -> None:
        pass

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        return AgentResult(output=self.outputs.pop(0))


def empty_audit() -> dict[str, Any]:
    return {
        "summary": "Keep the existing direction; runtime states remain untested.",
        "findings": [],
        "score": 0,
        "fixes_first": [],
    }


def test_source_audit_distinguishes_code_from_uninspected_visual_and_user_states() -> None:
    fake = FakeIntelligence(empty_audit())
    report = audit_capability.audit(source=MONOCHROME_PAGE, intelligence=fake)
    request = fake.requests[0]
    assert request.workspace is None
    assert request.prompt.count(role_contract_text()) == 1
    assert "Active scope: designer review, with editor review of visible copy" in request.prompt
    assert "No screenshot, rendered viewport, interaction" in request.prompt
    assert "observed evidence from the inferred reader/task cost" in request.prompt
    assert "not a comprehensive factual review" in request.prompt
    assert report.findings == []
    assert report.scan is not None
    assert "runtime states remain untested" in report.summary


def test_image_audit_limits_claims_to_the_supplied_captured_state(tmp_path: Path) -> None:
    image = tmp_path / "captured-state.png"
    image.write_bytes(b"image input is not decoded by the fake provider")
    fake = FakeIntelligence(empty_audit())
    report = audit_capability.audit(image=image, intelligence=fake)
    request = fake.requests[0]
    assert request.workspace is not None
    assert request.workspace.path == tmp_path
    assert request.writable is False
    assert "`captured-state.png`" in request.prompt
    assert "Only describe visual evidence from this image after viewing it" in request.prompt
    assert "do not infer\nother viewports" in request.prompt
    assert "Evidence available: source text and a static scan only" not in request.prompt
    assert report.scan is None


def test_coherent_monochrome_system_font_brand_skips_pipeline_restyling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = tmp_path / "archive.html"
    page.write_text(MONOCHROME_PAGE, encoding="utf-8")
    fake = FakeIntelligence(
        {
            "has_direction": True,
            "flat_background": True,
            "inferred_brief": "An archive for reading records.",
            "ground": "#FFFFFF",
            "light": "#111111",
            "signal": None,
        }
    )

    def reject_restyle(*args: Any, **kwargs: Any) -> None:
        pytest.fail("A kept intentional direction must not invoke a new palette proposal.")

    monkeypatch.setattr(pipeline_capability.direct_capability, "direct", reject_restyle)
    pipeline = pipeline_capability.Pipeline(page, str(page), fake, "test/model", "medium")
    read = pipeline.direct()
    assert read.has_direction
    assert pipeline.direction is None
    assert pipeline.steps[-1].ran is False
    assert page.read_text(encoding="utf-8") == MONOCHROME_PAGE
    prompt = fake.requests[0].prompt
    assert "font-family: system-ui" in prompt
    assert "intentional monochrome or system typography" in prompt
    assert "not an automatic restyle requirement" in prompt
    assert prompt.count(role_contract_text()) == 1


def test_design_edit_and_polish_keep_evidence_scope_and_allow_no_change() -> None:
    scanned = audit_capability.scan(source=MONOCHROME_PAGE)
    edit_prompt = unslop_capability.render_prompt("archive.html", scanned, None)
    polish_prompt = pipeline_capability.render("polish.md.liquid", file_name="archive.html")
    for prompt in (edit_prompt, polish_prompt):
        assert prompt.count(role_contract_text()) == 1
        assert "Active scope: designer" in prompt
        assert "editor" in prompt
    assert "Source inspection is not a rendered-state or usability test" in edit_prompt
    assert "do not claim screenshots, runtime states or user tasks were tested" in polish_prompt
    assert "An empty list is a fine answer" in polish_prompt


def test_direction_and_texture_requests_and_retries_retain_designer_contract() -> None:
    direct = direct_capability._render(
        direct_capability.PROMPT_PATH,
        brief="Keep the archive's established system-ui type and monochrome identity.",
        directions=1,
        dark_and_light=False,
    )
    direct_retry = direct_capability._render(direct_capability.RETRY_PATH, problems=["The light/ground pair fails."])
    texture = texture_capability.render_prompt(
        texture_capability.match_texture("Paper texture"), "A deliberately flat monochrome archive", None, False
    )
    texture_retry = texture_capability.retry_prompt(["the code is too large"])
    for prompt in (direct, direct_retry, texture, texture_retry):
        assert prompt.count(role_contract_text()) == 1
        assert "Active scope: designer" in prompt
    assert "Keep established type named in the brief" in direct
    assert "not evidence of a rendered visual improvement or user-task result" in direct
    assert "a flat fill, system font or purposeful gradient\nis not inherently a defect" in texture
    assert "rendered contrast over the texture and interactive states are unmeasured" in texture
    assert "Flat fills read as unfinished" not in texture


@pytest.mark.parametrize(
    ("template", "variables"),
    [
        (
            "apply-direction.md.liquid",
            {
                "file_name": "archive.html",
                "scene": "Paper archive",
                "palette": [],
                "typography": {
                    "display": "system-ui",
                    "body": "system-ui",
                    "rationale": "Keep established archive type.",
                },
                "css": ":root {}",
            },
        ),
        (
            "apply-texture.md.liquid",
            {
                "file_name": "archive.html",
                "texture": "Paper texture",
                "kind": "css",
                "code": ".texture {}",
                "contrast": "Unrendered proposal.",
            },
        ),
    ],
)
def test_pipeline_application_stages_retain_role_contract(template: str, variables: dict[str, Any]) -> None:
    prompt = pipeline_capability.render(template, **variables)
    assert prompt.count(role_contract_text()) == 1
    assert "Active scope: designer, limited to the supplied source and requested stage" in prompt
