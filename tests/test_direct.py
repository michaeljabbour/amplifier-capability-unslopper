"""Drives `direct` through a fake intelligence, so no credentials, network or model are needed."""

from typing import Any

import pytest

from unslopper import color, knowledge, lib
from unslopper.capabilities.direct import capability
from unslopper.capabilities.direct.capability import DirectAnswer, has_purple_blue_gradient
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.schemas import AGENT_PROVIDERS, DEFAULT_INTELLIGENCE_MODELS, UnslopperError

BRIEF = "a mechanical watch brand lit like the aurora"
GROUND, LIGHT, SIGNAL = "#000412", "#E8EEF2", "#2BF08A"
PURPLE_BLUE = "background: linear-gradient(135deg, #667eea, #764ba2);"


class FakeIntelligence:
    """Records every request and answers from a queue of canned results."""

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


def direction(
    ground: str = GROUND,
    light: str = LIGHT,
    signal: str = SIGNAL,
    css: str | None = None,
    scene: str = "Aurora over a dial",
) -> dict[str, Any]:
    return {
        "scene": scene,
        "colours": [
            {"role": "ground", "name": "night sky", "hex": ground},
            {"role": "light", "name": "ice white", "hex": light},
            {"role": "signal", "name": "aurora green", "hex": signal},
        ],
        "display": "Cormorant Garamond",
        "body": "Source Serif 4",
        "rationale": "Luxury watchmaking sets its own name in a high-contrast serif.",
        "hero": "The watch face lit from one side, a green trail across the crystal.",
        "css": css if css is not None else f":root {{ --ground: {ground}; --light: {light}; --signal: {signal}; }}",
    }


def answer(*directions: dict[str, Any], session_id: str = "session-1") -> AgentResult:
    return AgentResult(output={"directions": list(directions)}, text="", session_id=session_id)


def test_one_plain_structured_call_with_the_default_model() -> None:
    fake = FakeIntelligence(answer(direction()))

    result = lib.direct(BRIEF, intelligence=fake)

    assert fake.preflights == 1
    assert len(fake.requests) == 1
    request = fake.requests[0]
    assert request.workspace is None
    assert request.resume is None
    assert request.model == DEFAULT_INTELLIGENCE_MODELS[AGENT_PROVIDERS[0]]
    assert request.output_schema == DirectAnswer.model_json_schema()
    assert result.brief == BRIEF
    assert len(result.directions) == 1


def test_the_prompt_carries_the_brief_the_bans_the_default_faces_and_the_studies() -> None:
    fake = FakeIntelligence(answer(direction()))

    lib.direct(BRIEF, intelligence=fake)

    prompt = fake.requests[0].prompt
    assert BRIEF in prompt
    for word in knowledge.BANNED_ADJECTIVES:
        assert word in prompt
    for face in knowledge.DEFAULT_FACES:
        assert face in prompt
    for study in knowledge.PALETTE_STUDIES:
        assert study.name in prompt
        assert study.typography in prompt
        for swatch in study.swatches:
            assert swatch.hex in prompt
    for role in ("ground", "light", "signal"):
        assert role in prompt
    assert "10 percent" in prompt
    assert "4.5 to 1" in prompt
    assert "Google Fonts" in prompt
    assert "purple and blue" in prompt
    assert ":root" in prompt


def test_the_prompt_asks_for_three_or_one_when_directions_is_not_given() -> None:
    fake = FakeIntelligence(answer(direction()))

    lib.direct(BRIEF, intelligence=fake)

    prompt = fake.requests[0].prompt
    assert "three distinct directions" in prompt
    assert "one when it is specific" in prompt
    assert "exactly" not in prompt


@pytest.mark.parametrize("count", [1, 2, 3])
def test_a_given_number_of_directions_is_asked_for_exactly(count: int) -> None:
    fake = FakeIntelligence(answer(*[direction() for _ in range(count)]))

    result = lib.direct(BRIEF, directions=count, intelligence=fake)

    assert f"Give exactly {count} direction" in fake.requests[0].prompt
    assert "three distinct directions when the brief is open" not in fake.requests[0].prompt
    assert len(result.directions) == count


def test_dark_and_light_adds_the_variant_to_the_prompt() -> None:
    plain = FakeIntelligence(answer(direction()))
    both = FakeIntelligence(answer(direction()))

    lib.direct(BRIEF, intelligence=plain)
    lib.direct(BRIEF, dark_and_light=True, intelligence=both)

    assert "prefers-color-scheme" not in plain.requests[0].prompt
    assert "prefers-color-scheme" in both.requests[0].prompt


def test_oklch_and_contrast_are_computed_in_code_from_normalized_hex() -> None:
    fake = FakeIntelligence(answer(direction(ground="#000412", light="e8eef2", signal="#2bf08a")))

    result = lib.direct(BRIEF, intelligence=fake)

    [entry] = result.directions
    assert [swatch.role for swatch in entry.palette] == ["ground", "light", "signal"]
    assert [swatch.hex for swatch in entry.palette] == [GROUND, LIGHT, SIGNAL]
    for swatch in entry.palette:
        assert swatch.oklch == color.to_oklch(swatch.hex)
    assert entry.contrast == color.contrast(LIGHT, GROUND)
    assert entry.contrast.aa_body
    assert entry.typography.display == "Cormorant Garamond"
    assert entry.css.startswith(":root")


def test_a_failing_contrast_is_sent_back_once_in_the_same_session_and_the_fix_is_accepted() -> None:
    fake = FakeIntelligence(
        answer(direction(ground="#666666", light="#777777", scene="Fog on the bay"), session_id="first"),
        answer(direction(), session_id="second"),
    )

    result = lib.direct(BRIEF, intelligence=fake)

    assert len(fake.requests) == 2
    retry = fake.requests[1]
    assert retry.resume == "first"
    assert retry.output_schema == DirectAnswer.model_json_schema()
    assert "Direction 1 (Fog on the bay)" in retry.prompt
    assert "light #777777 on ground #666666" in retry.prompt
    assert f"{color.contrast_ratio('#777777', '#666666')} to 1" in retry.prompt
    assert "4.5 to 1" in retry.prompt
    assert result.directions[0].contrast.aa_body


def test_a_second_failing_contrast_raises_naming_the_ratio_and_the_remedy() -> None:
    fake = FakeIntelligence(
        answer(direction(ground="#666666", light="#777777")),
        answer(direction(ground="#666666", light="#777777")),
    )

    with pytest.raises(UnslopperError) as failure:
        lib.direct(BRIEF, intelligence=fake)

    message = str(failure.value)
    assert len(fake.requests) == 2
    assert f"{color.contrast_ratio('#777777', '#666666')} to 1" in message
    assert "4.5 to 1" in message
    assert "--reasoning-effort" in message


def test_a_purple_to_blue_gradient_is_rejected_and_named() -> None:
    css = f":root {{ --ground: {GROUND}; --light: {LIGHT}; --signal: {SIGNAL}; }} .hero {{ {PURPLE_BLUE} }}"
    fake = FakeIntelligence(answer(direction(css=css)), answer(direction(css=css)))

    with pytest.raises(UnslopperError, match="gradient between purple and blue"):
        lib.direct(BRIEF, intelligence=fake)

    assert "gradient between purple and blue" in fake.requests[1].prompt


def test_only_the_failing_direction_is_named_in_the_retry() -> None:
    fake = FakeIntelligence(
        answer(direction(scene="Good one"), direction(ground="#666666", light="#777777", scene="Bad one")),
        answer(direction(scene="Good one"), direction(scene="Fixed one")),
    )

    result = lib.direct(BRIEF, directions=2, intelligence=fake)

    assert "Direction 2 (Bad one)" in fake.requests[1].prompt
    assert "Good one" not in fake.requests[1].prompt
    assert [entry.scene for entry in result.directions] == ["Good one", "Fixed one"]


def test_the_wrong_number_of_directions_is_sent_back() -> None:
    fake = FakeIntelligence(answer(direction()), answer(direction(), direction()))

    result = lib.direct(BRIEF, directions=2, intelligence=fake)

    assert "2 directions were asked for and 1 came back" in fake.requests[1].prompt
    assert len(result.directions) == 2


def test_missing_roles_are_sent_back() -> None:
    incomplete = direction()
    incomplete["colours"] = incomplete["colours"][:2]
    fake = FakeIntelligence(answer(incomplete), answer(direction()))

    lib.direct(BRIEF, intelligence=fake)

    assert "one each for ground, light and signal" in fake.requests[1].prompt


def test_an_agent_error_raises_with_a_remedy() -> None:
    fake = FakeIntelligence(AgentResult(error="The agent did not finish within 600 seconds."))

    with pytest.raises(UnslopperError) as failure:
        lib.direct(BRIEF, intelligence=fake)

    message = str(failure.value)
    assert "did not finish within 600 seconds" in message
    assert "--model" in message


def test_an_empty_brief_and_a_bad_count_fail_before_any_call() -> None:
    fake = FakeIntelligence()

    with pytest.raises(UnslopperError, match="brief is empty"):
        lib.direct("  ", intelligence=fake)
    with pytest.raises(UnslopperError, match="1 or more"):
        lib.direct(BRIEF, directions=0, intelligence=fake)

    assert fake.requests == []


@pytest.mark.parametrize(
    ("css", "banned"),
    [
        (PURPLE_BLUE, True),
        ("background: linear-gradient(to right, purple, blue);", True),
        (":root { --a: #6366F1; --b: #A855F7; } .x { background: radial-gradient(circle, var(--a), var(--b)); }", True),
        ("background: conic-gradient(from 90deg, #7C3AED, #3B82F6 50%, #7C3AED);", True),
        (f"background: linear-gradient({GROUND}, {SIGNAL});", False),
        ("background: linear-gradient(#1E3A8A, #3B82F6);", False),  # one hue, blue to blue
        ("background: linear-gradient(#000412, #E8EEF2);", False),  # greys carry no hue
        ("color: #764ba2; background: #667eea;", False),  # the hues without a gradient
    ],
)
def test_the_gradient_detector_reads_hex_names_and_tokens(css: str, banned: bool) -> None:
    assert has_purple_blue_gradient(css) is banned


def test_the_prompt_templates_sit_beside_the_code() -> None:
    assert capability.PROMPT_PATH.is_file()
    assert capability.RETRY_PATH.is_file()
