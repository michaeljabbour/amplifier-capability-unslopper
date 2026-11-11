"""Drives the texture capability with a fake intelligence, so neither credentials nor a model are needed."""

from typing import Any

import pytest

from unslopper import knowledge
from unslopper.capabilities.texture import capability
from unslopper.capabilities.texture.capability import MAX_BYTES, Answer, texture
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.schemas import TextureResult, UnslopperError

PALETTE = {"ground": "#1C4E8A", "light": "#F5F7FA", "signal": "#FFB020"}
CSS = ".texture{background-color:#1C4E8A;background-image:linear-gradient(rgba(255,255,255,.12) 1px,transparent 1px)}"
CANVAS = '<canvas class="texture" width="640" height="400"></canvas><script>const c=document.querySelector(".texture").getContext("2d");c.fillStyle="#1C4E8A";c.fillRect(0,0,640,400)</script>'


def answer(**overrides: Any) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "recommendations": [
            {"name": "Blueprint grids", "why": "Engineering drawings are the world of developer tools."},
            {"name": "Square-dot grids", "why": "A quieter technical ground."},
        ],
        "texture": "Blueprint grids",
        "kind": "css",
        "code": CSS,
        "contrast": "The grid lines stay at 12 percent white on the ground, so #F5F7FA text reads at AA.",
        "warning": "",
        "ground": "",
        "light": "",
        "signal": "",
    }
    fields.update(overrides)
    return fields


class FakeIntelligence:
    """Records every request and answers from a queue of canned outputs."""

    def __init__(self, *outputs: dict[str, Any] | None, error: str | None = None) -> None:
        self.implementation = "fake"
        self.outputs = list(outputs)
        self.error = error
        self.requests: list[AgentRequest] = []

    def preflight(self) -> None:
        pass

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        if self.error:
            return AgentResult(error=self.error)
        return AgentResult(output=self.outputs.pop(0), session_id=f"session-{len(self.requests)}")


def run(
    fake: FakeIntelligence,
    name: str | None = None,
    animated: bool = False,
    ground: str = PALETTE["ground"],
    light: str = PALETTE["light"],
    signal: str = PALETTE["signal"],
) -> TextureResult:
    return texture(
        name=name,
        subject="a developer tools landing page",
        ground=ground,
        light=light,
        signal=signal,
        animated=animated,
        intelligence=fake,
    )


def test_a_partial_palette_raises_naming_the_missing_roles() -> None:
    with pytest.raises(UnslopperError, match="missing light, signal"):
        texture(subject="a zine", ground="#111111", intelligence=FakeIntelligence())


def test_no_palette_and_no_subject_raises_saying_what_to_pass() -> None:
    with pytest.raises(UnslopperError, match=r"subject.*--ground, --light and --signal"):
        texture(intelligence=FakeIntelligence())


def test_an_unknown_name_raises_listing_the_textures() -> None:
    with pytest.raises(UnslopperError) as failure:
        run(FakeIntelligence(), name="chrome")

    for entry in knowledge.TEXTURES:
        assert entry.name in str(failure.value)


def test_a_name_matches_by_substring_and_case() -> None:
    assert capability.match_texture("BLUEPRINT").name == "Blueprint grids"
    assert capability.match_texture("Paper texture").name == "Paper texture"


def test_an_ambiguous_name_names_its_matches() -> None:
    with pytest.raises(UnslopperError, match="Blueprint grids, Square-dot grids"):
        capability.match_texture("grid")


def test_the_prompt_carries_the_catalog_the_palette_and_the_reference_snippet() -> None:
    fake = FakeIntelligence(answer())

    result = run(fake, name="blueprint")

    (request,) = fake.requests
    assert request.workspace is None
    assert request.output_schema == Answer.model_json_schema()
    for entry in knowledge.TEXTURES:
        assert f"- {entry.name}: {entry.use}" in request.prompt
    for value in PALETTE.values():
        assert value in request.prompt
    assert "### Blueprint grids" in request.prompt
    assert 'c.fillStyle="#1C4E8A"' in request.prompt
    assert "### Felt texture" not in request.prompt
    assert "no @keyframes" in request.prompt
    assert result.texture == "Blueprint grids"
    assert result.kind == "css"
    assert result.size_bytes == len(CSS.encode())
    assert result.palette.model_dump() == PALETTE
    assert result.warning is None


def test_without_a_name_every_reference_snippet_is_in_the_prompt() -> None:
    fake = FakeIntelligence(answer())

    run(fake)

    for entry in knowledge.TEXTURES:
        assert f"### {entry.name}" in fake.requests[0].prompt


def test_an_oversize_first_answer_triggers_one_resume_naming_the_size() -> None:
    oversize = ".texture{" + "a" * MAX_BYTES + "}"
    fake = FakeIntelligence(answer(code=oversize), answer())

    result = run(fake)

    first, second = fake.requests
    assert first.resume is None
    assert second.resume == "session-1"
    assert f"{len(oversize.encode())} bytes" in second.prompt
    assert result.code == CSS


def test_animation_when_not_allowed_triggers_one_resume_naming_it() -> None:
    fake = FakeIntelligence(answer(code=CSS + "@keyframes drift{to{background-position:40px 0}}"), answer())

    run(fake)

    assert "@keyframes" in fake.requests[1].prompt
    assert "animation was not asked for" in fake.requests[1].prompt


def test_animation_is_accepted_when_asked_for() -> None:
    animated = CSS + "@media (prefers-reduced-motion:no-preference){.texture{animation:drift 20s linear infinite}}"
    fake = FakeIntelligence(answer(code=animated))

    result = run(fake, animated=True)

    assert len(fake.requests) == 1
    assert "allowed" in fake.requests[0].prompt
    assert result.code == animated


def test_a_second_failing_answer_raises_naming_the_failure() -> None:
    fake = FakeIntelligence(answer(code="x" * MAX_BYTES), answer(code="y" * MAX_BYTES))

    with pytest.raises(UnslopperError, match=r"failed its checks twice.*bytes"):
        run(fake)

    assert len(fake.requests) == 2


def test_kind_and_code_mismatch_is_caught_both_ways() -> None:
    fake = FakeIntelligence(answer(code=CANVAS), answer(kind="canvas", code=CSS), answer(kind="canvas", code=CANVAS))

    with pytest.raises(UnslopperError, match="kind is canvas but the code has no <script>"):
        run(fake)
    result = run(fake)

    assert "kind is css but the code contains <script> or <canvas>" in fake.requests[1].prompt
    assert len(fake.requests) == 3
    assert result.kind == "canvas"


def test_an_external_image_is_caught() -> None:
    fake = FakeIntelligence(answer(code='.texture{background:url("https://example.com/paper.png")}'), answer())

    run(fake)

    assert "external resource" in fake.requests[1].prompt


def test_the_svg_namespace_in_a_data_uri_is_not_external() -> None:
    noise = (
        ".texture{background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3C/svg%3E\")}"
    )
    fake = FakeIntelligence(answer(code=noise))

    assert run(fake).code == noise


def test_the_drawn_texture_must_be_the_one_named() -> None:
    fake = FakeIntelligence(answer(texture="Paper texture"), answer())

    run(fake, name="blueprint")

    assert "must be Blueprint grids, not Paper texture" in fake.requests[1].prompt


def test_without_a_palette_the_model_proposes_one_and_it_is_normalized() -> None:
    fake = FakeIntelligence(answer(ground="#efe8d9", light="#2b2118", signal="#c0392b"))

    result = texture(subject="a small press publishing poetry", intelligence=fake)

    assert "No palette was given" in fake.requests[0].prompt
    assert result.palette.model_dump() == {"ground": "#EFE8D9", "light": "#2B2118", "signal": "#C0392B"}


def test_a_bad_inferred_palette_triggers_a_resume() -> None:
    fake = FakeIntelligence(answer(ground="beige"), answer(ground="#EFE8D9", light="#2B2118", signal="#C0392B"))

    texture(subject="a small press", intelligence=fake)

    assert "inferred palette" in fake.requests[1].prompt


def test_a_failing_contrast_gets_a_scrim_added_to_the_note() -> None:
    fake = FakeIntelligence(answer(contrast="The lines are faint."))

    result = run(fake, ground="#1C4E8A", light="#4A7AB8", signal="#FFB020")

    assert result.contrast.startswith("The lines are faint. Light on ground measures")
    assert "scrim of #1C4E8A" in result.contrast


def test_a_failing_contrast_keeps_a_note_that_already_names_a_scrim() -> None:
    fake = FakeIntelligence(answer(contrast="Body text sits on a scrim of the ground at 90 percent."))

    result = run(fake, ground="#1C4E8A", light="#4A7AB8", signal="#FFB020")

    assert result.contrast == "Body text sits on a scrim of the ground at 90 percent."


def test_a_warning_is_passed_through() -> None:
    fake = FakeIntelligence(answer(warning="Dithering reads as an AI default here; use Blueprint grids."))

    assert run(fake).warning == "Dithering reads as an AI default here; use Blueprint grids."


def test_an_agent_error_raises_with_a_remedy() -> None:
    with pytest.raises(UnslopperError, match=r"rate limited.*credentials"):
        run(FakeIntelligence(error="rate limited."))
