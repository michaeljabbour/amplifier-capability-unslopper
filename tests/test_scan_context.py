"""Static candidates need visible DOM context, not merely a matching-looking stylesheet."""

import pytest

from unslopper.capabilities.audit.document import parse_css, parse_html
from unslopper.capabilities.audit.scan import scan_document
from unslopper.sources import Stylesheet


def indicators(html: str) -> set[str]:
    return {hit.indicator for hit in scan_document(parse_html(html))}


def test_unused_css_is_not_html_evidence() -> None:
    css = (
        '.unused { font-family: "Instrument Serif"; letter-spacing: -2px; background: linear-gradient(purple, blue); }'
    )
    assert not indicators(f"<style>{css}</style><p>Ordinary text</p>")
    assert {hit.indicator for hit in scan_document(parse_css(css))} >= {
        "Instrument Serif",
        "Negative kerning",
        "Gradient backgrounds",
    }


@pytest.mark.parametrize("selector", [".missing .present", ".missing > .present", "article.present", "#absent"])
def test_nonmatching_supported_selectors_are_skipped(selector: str) -> None:
    assert not indicators(f'<style>{selector} {{ letter-spacing: -2px; }}</style><p class="present">Text</p>')


@pytest.mark.parametrize(
    "selector", [".present:hover", ".present:not(.other)", "[data-x]", ".missing + .present", ".present::before"]
)
def test_unsupported_selectors_are_not_guessed(selector: str) -> None:
    doc = parse_html(
        f'<style>{selector} {{ letter-spacing: -2px; display:none; }}</style><p class="present" data-x>Text</p>'
    )
    assert not scan_document(doc)
    assert any("Unsupported CSS selectors" in warning for warning in doc.warnings)
    assert any(element.tag == "p" for element in doc.elements())


@pytest.mark.parametrize(
    "wrapper",
    [
        "<div hidden>{}</div>",
        '<div style="display:none">{}</div>',
        '<div class="hidden">{}</div>',
        "<template>{}</template>",
    ],
)
def test_hidden_subtree_does_not_score(wrapper: str) -> None:
    content = '<h2>Move fast. Go further.</h2><span class="pill">NEW</span><p>Powerful seamless tools</p>'
    assert not indicators("<style>.hidden { display:none }</style>" + wrapper.format(content))


def test_hidden_descendant_text_does_not_leak_into_visible_heading() -> None:
    assert not indicators("<h2>Reports<span hidden>Move fast. Go further.</span></h2>")


@pytest.mark.parametrize(
    "markup",
    [
        '<a href="?filter=new" class="pill"><span class="pill">NEW</span></a>',
        '<button><span class="pill">NEW</span></button>',
        '<div role="button"><span class="pill">NEW</span></div>',
        '<nav><span class="pill">NEW</span></nav>',
        '<label><span class="pill">NEW</span><input type="checkbox"></label>',
        '<span role="tab" class="pill">NEW</span>',
    ],
)
def test_functional_controls_are_not_filler_badges(markup: str) -> None:
    assert "Tags and pills" not in indicators(markup)


def test_decorative_badge_still_scores() -> None:
    assert "Tags and pills" in indicators('<span class="pill">NEW</span>')


@pytest.mark.parametrize(
    ("css", "inline", "expected"),
    [
        ("#target {letter-spacing:0} p {letter-spacing:-2px}", "", "0"),
        ("p {letter-spacing:-2px} p {letter-spacing:0}", "", "0"),
        ("p {letter-spacing:0 !important} #target {letter-spacing:-2px}", "", "0"),
        ("p {letter-spacing:0 !important}", "letter-spacing:-2px", "0"),
        ("#target {letter-spacing:-2px !important}", "letter-spacing:0 !important", "0"),
        ("p {letter-spacing:0 !important;letter-spacing:-2px}", "", "0"),
        ("p {letter-spacing:-2px}", "letter-spacing:0", "0"),
    ],
)
def test_specificity_order_and_importance(css: str, inline: str, expected: str) -> None:
    doc = parse_html(f'<style>{css}</style><p id="target" style="{inline}">Text</p>')
    element = next(element for element in doc.elements() if element.id == "target")
    assert doc.style(element)["letter-spacing"] == expected
    assert not scan_document(doc)


def test_selector_list_uses_specificity_of_matching_arm_only() -> None:
    doc = parse_html('<style>#missing, p {display:none} .visible {display:block}</style><p class="visible">Text</p>')
    assert any(element.tag == "p" for element in doc.elements())


def test_conditional_styles_do_not_hide_base_content() -> None:
    doc = parse_html(
        '<style>@media print { .pill {display:none; letter-spacing:-2px} }</style><span class="pill">NEW</span>'
    )
    assert {hit.indicator for hit in scan_document(doc)} == {"Tags and pills"}
    assert any("Conditional" in warning for warning in doc.warnings)
    assert "Negative kerning" in {
        hit.indicator for hit in scan_document(parse_css("@media print { .pill {letter-spacing:-2px} }"))
    }


def test_conditional_style_element_is_not_unconditionally_applied() -> None:
    doc = parse_html('<style media="print">p {display:none; letter-spacing:-2px}</style><p>Text</p>')
    assert any(element.tag == "p" for element in doc.elements())
    assert not scan_document(doc)
    assert doc.warnings


def test_display_override_keeps_visible_element() -> None:
    assert "Tags and pills" in indicators(
        '<style>.pill {display:none} #shown {display:inline}</style><span class="pill" id="shown">NEW</span>'
    )


def test_inline_important_font_shorthand_controls_size() -> None:
    doc = parse_html('<p style="font:12px monospace !important;font-size:24px">Text</p>')
    element = next(element for element in doc.elements() if element.tag == "p")
    assert doc.font_size(element) == 12


def test_dithering_unused_rule_is_not_evidence() -> None:
    assert not indicators("<style>.dither {color:red}</style><p>Plain</p>")


def test_linked_css_preserves_source_order_on_one_line() -> None:
    before = "<style>p {letter-spacing:-2px}</style>"
    link = '<link rel="stylesheet" href="app.css">'
    html = before + link + "<style>p {letter-spacing:0}</style><p>Text</p>"
    sheet = Stylesheet("p {letter-spacing:-3px}", "https://example.test/app.css", 1, len(before))
    assert not scan_document(parse_html(html, (sheet,)))
    html = before + link + "<p>Text</p>"
    hits = scan_document(parse_html(html, (sheet,)))
    assert hits[0].evidence[0].location == "https://example.test/app.css: p (line 1)"
    assert hits[0].evidence[0].detail == "letter-spacing: -3px"


def test_failed_link_does_not_steal_later_same_line_stylesheet() -> None:
    missing = '<link rel="stylesheet" href="missing.css">'
    override = "<style>p {letter-spacing:-2px}</style>"
    loaded = '<link rel="stylesheet" href="loaded.css"/>'
    sheet = Stylesheet("p {letter-spacing:0}", "https://example.test/loaded.css", 1, len(missing + override))
    assert not scan_document(parse_html(missing + override + loaded + "<p>Text</p>", (sheet,)))


def test_basic_screen_style_remains_supported() -> None:
    assert "Negative kerning" in indicators('<style media="screen">p {letter-spacing:-2px}</style><p>Text</p>')


def test_pill_wrapper_containing_only_functional_links_is_not_a_badge() -> None:
    assert "Tags and pills" not in indicators(
        '<ul class="flow-tags"><li><a href="?x">NEW</a></li><li><a href="?y">Tools</a></li></ul>'
    )


def test_functional_link_does_not_suppress_decorative_sibling_badge() -> None:
    assert "Tags and pills" in indicators('<div><a href="?x">Tools</a><span class="pill">NEW</span></div>')


@pytest.mark.parametrize(
    "css",
    [
        "@media print { :root { --spacing:-2px; --display:none; } }",
        "@supports (display:grid) { :root { --spacing:-2px; --display:none; } }",
    ],
)
def test_conditional_custom_properties_do_not_leak(css: str) -> None:
    doc = parse_html(
        "<style>" + css + "p {letter-spacing:var(--spacing, 0); display:var(--display, block)}</style><p>Text</p>"
    )
    assert not scan_document(doc)
    assert any(element.tag == "p" for element in doc.elements())


def test_conditional_style_custom_properties_do_not_leak_into_inline_styles() -> None:
    doc = parse_html(
        '<style media="print">:root {--display:none}</style><p style="display:var(--display, block)">Text</p>'
    )
    assert any(element.tag == "p" for element in doc.elements())
