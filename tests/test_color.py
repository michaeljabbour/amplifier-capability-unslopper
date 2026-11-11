import pytest

from unslopper import color
from unslopper.schemas import UnslopperError


def test_hex_parses_short_and_long_forms_and_normalizes() -> None:
    assert color.parse_hex("#2BF08A") == (43, 240, 138)
    assert color.parse_hex("fff") == (255, 255, 255)
    assert color.normalize_hex("#abc") == "#AABBCC"


def test_a_bad_hex_names_the_shape_wanted() -> None:
    with pytest.raises(UnslopperError, match="#RRGGBB"):
        color.parse_hex("purple")


def test_black_on_white_is_the_maximum_ratio() -> None:
    assert color.contrast_ratio("#000000", "#FFFFFF") == 21.0
    assert color.contrast_ratio("#FFFFFF", "#000000") == 21.0


def test_contrast_reports_the_wcag_levels() -> None:
    result = color.contrast("#E8EEF2", "#000412")

    assert result.ratio > 17
    assert result.aa_body
    assert result.aa_large
    assert result.aaa_body

    weak = color.contrast("#999999", "#FFFFFF")
    assert weak.ratio == pytest.approx(2.85, abs=0.01)
    assert not weak.aa_body
    assert not weak.aa_large


def test_oklch_matches_known_values() -> None:
    assert color.to_oklch("#FFFFFF") == "oklch(100.0% 0.000 0.0)"
    assert color.to_oklch("#000000") == "oklch(0.0% 0.000 0.0)"
    assert color.to_oklch("#FF0000") == "oklch(62.8% 0.258 29.2)"
