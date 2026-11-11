"""Coverage and source provenance survive the public scan and model-audit boundaries."""

import pytest

from unslopper import lib
from unslopper.capabilities.audit import capability
from unslopper.schemas import ScanReport
from unslopper.sources import Asset, Source, Stylesheet


def test_linked_css_is_scanned_without_rewriting_source_text() -> None:
    html = '<link rel="stylesheet" href="site.css"><h2>Heading</h2>'
    css = "h2{font-size:20px;letter-spacing:-.08em}"
    label = "https://example.test/site.css"
    source = Source(html, "https://example.test/", "html", (Stylesheet(css, label),), (Asset(label, "loaded"),))

    report = capability.scan_source(source)

    assert source.text == html
    assert report.analysis_kind == "static_candidates"
    assert report.source_kind == "html"
    assert report.assets[0].url == label
    assert report.assets[0].status == "loaded"
    hit = next(hit for hit in report.hits if hit.indicator == "Negative kerning")
    assert label in hit.evidence[0].location
    assert any("rendered layout" in warning for warning in report.warnings)
    assert ScanReport.model_validate_json(report.model_dump_json()) == report


def test_offline_links_are_reported_as_incomplete_coverage() -> None:
    report = lib.scan(source='<link rel="stylesheet" href="site.css"><h2>Heading</h2>')

    assert report.assets[0].status == "skipped"
    assert report.assets[0].reason
    assert report.warnings
    assert report.score == 0


def test_stylesheet_scan_is_explicitly_not_a_page_scan() -> None:
    report = lib.scan(source=".unused{letter-spacing:-.08em}")

    assert report.source_kind == "css"
    assert report.analysis_kind == "static_candidates"
    assert report.score == 1


def test_audit_prompt_contains_linked_css_provenance() -> None:
    css = "h2{letter-spacing:-.08em}"
    label = "https://example.test/site.css"
    source = Source("<h2>Heading</h2>", "https://example.test/", "html", (Stylesheet(css, label),))

    prompt = capability.render_prompt(source, capability.scan_source(source))

    assert css in prompt
    assert label in prompt
    assert source.text in prompt


def test_audit_source_budget_includes_linked_stylesheets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(capability, "MAX_SOURCE_CHARS", 40)
    first = "/*FIRST*/" + "a" * 100
    second = "/*SECOND*/" + "b" * 100
    source = Source(
        "<h2>Hi</h2>",
        "https://example.test/",
        "html",
        (
            Stylesheet(first, "https://example.test/first.css"),
            Stylesheet(second, "https://example.test/second.css"),
        ),
    )

    prompt = capability.render_prompt(source, None)

    assert "It is truncated" in prompt
    assert "/*FIRST*/" in prompt
    assert first not in prompt
    assert "/*SECOND*/" not in prompt


def test_legacy_scan_reports_remain_readable() -> None:
    report = ScanReport(source="inline", score=0, verdict="No defaults showing", hits=[], fixes_first=[])

    assert report.analysis_kind == "static_candidates"
    assert report.assets == []
