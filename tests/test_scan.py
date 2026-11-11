"""The deterministic scan on the course's own before-and-after cards: the slop card scores high, the clean card near zero."""

from pathlib import Path

import pytest

from unslopper import knowledge, lib
from unslopper.capabilities.audit import scan as checks
from unslopper.capabilities.audit.document import parse_css, parse_html
from unslopper.schemas import UnslopperError

FIXTURES = Path(__file__).parent / "fixtures"
SLOP_CARD = FIXTURES / "audit-slop-card.html"
CLEAN_CARD = FIXTURES / "audit-clean-card.html"
SLOP_CSS = FIXTURES / "audit-slop.css"

# What the course's callouts name on the slop card, where static code can honestly see it.
SLOP_CARD_INDICATORS = {
    "Instrument Serif",
    "Excessive italics",
    "Excessive mono fonts",
    "ALL CAPS subtitles",
    "Periods in titles",
    "Gradient backgrounds",
    "Color shades and opacities",
    "Containers with borders",
    "Overusing dividers",
    "Tags and pills",
    "Eyebrows",
    "Section numbering",
    "Code breadcrumbs",
    "Verbose, redundant text",
}


def test_every_check_is_named_after_an_indicator_in_the_catalog() -> None:
    names = [name for name, _ in checks.CHECKS]

    assert names == [entry.name for entry in knowledge.INDICATORS]


def test_the_slop_card_reads_as_pure_default_output() -> None:
    report = lib.scan(path=SLOP_CARD)

    assert report.source == str(SLOP_CARD)
    assert {hit.indicator for hit in report.hits} >= SLOP_CARD_INDICATORS
    assert report.score == len(report.hits) >= 10
    assert report.verdict == knowledge.verdict(report.score) == "Pure default output"
    assert report.fixes_first[:3] == ["Delete filler badges", "Drop redundant labels", "Unitalicize random words"]


def test_every_hit_carries_evidence_a_person_can_check() -> None:
    report = lib.scan(path=SLOP_CARD)
    by_name = {hit.indicator: hit for hit in report.hits}

    for hit in report.hits:
        assert hit.evidence
        assert hit.layer == knowledge.indicator(hit.indicator).layer
        assert hit.fix_ids == knowledge.indicator(hit.indicator).fix_ids
        for evidence in hit.evidence:
            assert evidence.location
            assert evidence.detail
    assert by_name["Instrument Serif"].evidence[0].location == ".slop h5 (line 18)"
    assert "Instrument Serif" in by_name["Instrument Serif"].evidence[0].detail
    assert by_name["Excessive italics"].evidence[0].location == "<h5> (line 32)"
    assert by_name["Tags and pills"].evidence[0].detail == '"NEW"'
    assert by_name["Section numbering"].evidence[0].detail.startswith('"02')
    assert by_name["Code breadcrumbs"].evidence[0].detail.startswith('"src/auth/refresh.py')
    assert by_name["Gradient backgrounds"].evidence[0].detail.endswith("(purple to blue)")
    assert "8 alphas" in by_name["Color shades and opacities"].evidence[0].detail
    assert by_name["Eyebrows"].evidence[0].detail.endswith('above "Plans first. Acts second."')
    buzzwords = {evidence.detail.split(" in ")[0] for evidence in by_name["Verbose, redundant text"].evidence}
    assert buzzwords >= {'"powerful"', '"AI-driven"', '"seamlessly"', '"empowering"'}
    assert all(
        evidence.location == '<p class="copy"> (line 36)' for evidence in by_name["Verbose, redundant text"].evidence
    )


def test_the_clean_card_scores_at_most_one() -> None:
    report = lib.scan(path=CLEAN_CARD)

    assert report.score <= 1
    assert report.verdict in {"No defaults showing", "Mostly intentional. Check those were choices"}


def test_a_stylesheet_alone_runs_the_rule_based_checks() -> None:
    report = lib.scan(path=SLOP_CSS)
    names = {hit.indicator for hit in report.hits}

    assert names >= {
        "Instrument Serif",
        "Gradient backgrounds",
        "Color shades and opacities",
        "Containers with borders",
    }
    assert not names & {"Excessive italics", "Periods in titles", "Code breadcrumbs", "Verbose, redundant text"}


def test_inline_source_is_labelled_inline_and_detected_by_shape() -> None:
    html = lib.scan(source='<div class="pill">NEW</div><div class="pill">BETA</div>')
    css = lib.scan(source=".hero{background:linear-gradient(135deg,#7c3aed,#2563eb)}")

    assert html.source == css.source == "inline"
    assert [hit.indicator for hit in html.hits] == ["Tags and pills"]
    assert [hit.indicator for hit in css.hits] == ["Gradient backgrounds"]


def test_plain_text_names_what_to_pass_instead() -> None:
    with pytest.raises(UnslopperError, match="neither HTML nor CSS"):
        lib.scan(source="just some words about a design")


def test_a_missing_file_is_named() -> None:
    with pytest.raises(UnslopperError, match="is not a file"):
        lib.scan(path=FIXTURES / "nope.html")


def test_negative_tracking_on_display_headings_alone_is_not_flagged() -> None:
    document = parse_css(
        "h1{font-size:64px;letter-spacing:-.025em} h2{font-size:40px;letter-spacing:-.015em} h3{font-size:28px;letter-spacing:-.02em}"
    )

    assert checks.negative_kerning(document) == []
    assert checks.negative_kerning(parse_css("p{letter-spacing:-.02em}"))
    assert checks.negative_kerning(parse_css(".label{font-size:12px;letter-spacing:-.02em}"))
    assert checks.negative_kerning(parse_css("h1{letter-spacing:-.06em}"))


def test_monospace_inside_code_is_not_flagged() -> None:
    document = parse_html(
        "<style>code,pre{font-family:ui-monospace,monospace} .label{font:11px ui-monospace}</style><code>x</code><div class='label'>v2</div>"
    )
    names = [hit.indicator for hit in checks.scan_document(document)]

    assert "Excessive mono fonts" in names
    assert checks.excessive_mono(parse_css("pre, code{font-family:'Fira Code',monospace}")) == []


def test_a_single_terminal_block_is_output_not_a_breadcrumb() -> None:
    document = parse_html(
        "<style>.shot{font-family:ui-monospace,monospace}</style>"
        "<div class='shot'>run tests<br><span>-> patch auth/refresh.py</span><br>done, nothing else to do here at all</div>"
    )

    assert checks.code_breadcrumbs(document) == []


def test_a_warm_gradient_on_one_element_is_not_a_purple_to_blue_default() -> None:
    assert checks.gradient_backgrounds(parse_css(".sunset{background:linear-gradient(#f97316,#facc15)}")) == []
    assert checks.gradient_backgrounds(parse_css(".ai{background:linear-gradient(135deg,#6E4CF5,#3B82F6)}"))


def test_the_course_page_itself_scans_without_error() -> None:
    report = lib.scan(path=Path(__file__).parents[1] / "docs" / "unslop-school.html")

    # The course embeds the slop card and deliberately wrong demos, so it is expected to score.
    assert report.score >= 10
    assert all(hit.evidence for hit in report.hits)
