import pytest

from unslopper.capabilities.route.capability import ROUTES
from unslopper.core.skill import CAPABILITIES
from unslopper.lib import route
from unslopper.schemas import UnslopperError


@pytest.mark.parametrize(
    ("intent", "capability", "skill"),
    [
        ("this landing page looks AI generated, what is wrong with it", "audit", "design-slop-audit"),
        ("here is a screenshot, is it slop", "audit", "design-slop-audit"),
        ("quick static check of this css", "scan", "design-slop-audit"),
        ("fix this page so it looks less generic", "unslop", "unslop-pass"),
        ("give the coffee roaster site a palette and fonts", "direct", "palette-director"),
        ("is #777 on white readable, what is the contrast ratio", "contrast", "palette-director"),
        ("the background is a flat purple gradient", "texture", "texture-backgrounds"),
        ("teach me what leading means", "tutor", "design-terms-tutor"),
        ("list the twenty indicators", "reference", "unslopper"),
        ("just do the whole thing end to end on index.html", "antislop", "design-antislopper"),
    ],
)
def test_the_words_of_a_job_pick_its_capability(intent: str, capability: str, skill: str) -> None:
    choice = route(intent)

    assert choice.capability == capability
    assert choice.skill == skill
    assert choice.command.startswith(f"unslopper {capability}")
    assert choice.alternatives


def test_an_intent_that_points_nowhere_returns_the_table_and_no_choice() -> None:
    choice = route("hello there")

    assert choice.capability is None
    assert choice.skill == "unslopper"
    assert len(choice.alternatives) == len(ROUTES)


def test_an_empty_intent_asks_for_a_sentence() -> None:
    with pytest.raises(UnslopperError, match="sentence"):
        route("   ")


def test_every_route_names_a_real_capability() -> None:
    names = {capability.name for capability in CAPABILITIES}

    for option, command, _ in ROUTES:
        assert option.capability in names
        assert command.startswith(f"unslopper {option.capability}")
