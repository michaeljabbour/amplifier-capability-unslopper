"""`contrast` is a thin call to the colour library, so it answers like it and fails like it."""

import pytest

from unslopper import color, lib
from unslopper.schemas import UnslopperError


def test_black_on_white_is_the_maximum_ratio_at_every_level() -> None:
    result = lib.contrast("#000000", "#FFFFFF")

    assert result.ratio == 21.0
    assert result.aa_body
    assert result.aa_large
    assert result.aaa_body


def test_the_northern_time_study_passes_aaa() -> None:
    result = lib.contrast("#E8EEF2", "#000412")

    assert result.ratio == pytest.approx(17.49, abs=0.01)
    assert result.aaa_body


@pytest.mark.parametrize(
    ("foreground", "background", "ratio", "aa_body", "aa_large", "aaa_body"),
    [
        ("#767676", "#FFFFFF", 4.54, True, True, False),  # the usual AA threshold grey
        ("#999999", "#FFFFFF", 2.85, False, False, False),
        ("#949494", "#FFFFFF", 3.03, False, True, False),  # large text only
        ("#595959", "#FFFFFF", 7.0, True, True, True),
    ],
)
def test_known_pairs_land_on_the_wcag_thresholds(
    foreground: str, background: str, ratio: float, aa_body: bool, aa_large: bool, aaa_body: bool
) -> None:
    result = lib.contrast(foreground, background)

    assert result.ratio == pytest.approx(ratio, abs=0.01)
    assert (result.aa_body, result.aa_large, result.aaa_body) == (aa_body, aa_large, aaa_body)


def test_the_order_of_the_colours_does_not_change_the_ratio() -> None:
    assert lib.contrast("#111111", "#C9EF35").ratio == lib.contrast("#C9EF35", "#111111").ratio


def test_short_hex_is_accepted_and_both_colours_are_normalized() -> None:
    result = lib.contrast("fff", "#000")

    assert result.foreground == "#FFFFFF"
    assert result.background == "#000000"
    assert result == color.contrast("#FFFFFF", "#000000")


def test_a_bad_hex_names_the_shape_wanted() -> None:
    with pytest.raises(UnslopperError, match="#RRGGBB"):
        lib.contrast("navy", "#FFFFFF")
