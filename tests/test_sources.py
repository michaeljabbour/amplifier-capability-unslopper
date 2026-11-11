"""Offline coverage of source loading, bounded fetching and stylesheet provenance."""

from email.message import Message
from pathlib import Path
from typing import Self
from urllib.request import Request

import pytest

from unslopper import sources
from unslopper.schemas import UnslopperError


class Response:
    def __init__(self, text: str, url: str, content_type: str = "text/html") -> None:
        self.body = text.encode()
        self.url = url
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.read_sizes: list[int] = []

    def geturl(self) -> str:
        return self.url

    def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        return self.body[:size]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        pass


class Network:
    def __init__(self, monkeypatch: pytest.MonkeyPatch, responses: dict[str, Response | Exception]) -> None:
        self.responses = responses
        self.requests: list[str] = []
        monkeypatch.setattr(sources, "build_opener", lambda handler: self)

    def open(self, request: Request, timeout: int) -> Response:
        assert timeout == sources.FETCH_TIMEOUT_SECONDS
        self.requests.append(request.full_url)
        response = self.responses[request.full_url]
        if isinstance(response, Exception):
            raise response
        return response


def test_source_preserves_three_argument_construction() -> None:
    source = sources.Source("x", "inline", "text")
    assert source.stylesheets == source.assets == source.warnings == ()


def test_url_loads_stylesheets_with_final_url_base_and_link_order(monkeypatch: pytest.MonkeyPatch) -> None:
    html = '<base href="/assets/">\n<link rel="stylesheet" href="main.css">\n<style>p{color:red}</style>\n<link rel="stylesheet" href="main.css">'
    network = Network(
        monkeypatch,
        {
            "https://example.com/start": Response(html, "https://example.com/dir/page"),
            "https://example.com/assets/main.css": Response(
                "p{color:blue}", "https://example.com/assets/main.css", "text/css"
            ),
        },
    )
    source = sources.load_source(url="https://example.com/start")
    assert source.text == html
    assert source.label == "https://example.com/dir/page"
    assert [sheet.line for sheet in source.stylesheets] == [2, 4]
    assert len(source.assets) == 1
    assert source.assets[0].status == "loaded"
    assert network.requests == ["https://example.com/start", "https://example.com/assets/main.css"]


def test_cross_origin_unsafe_and_conditional_links_are_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    html = "".join(
        f'<link rel="stylesheet" href="{href}" {extra}>'
        for href, extra in [
            ("https://other.example/style.css", ""),
            ("file:///tmp/a.css", ""),
            ("javascript:alert(1)", ""),
            ("/print.css", 'media="print"'),
            ("/mobile.css", 'media="screen and (max-width: 600px)"'),
            ("/disabled.css", "disabled"),
            ("https://user:password@example.com/a.css", ""),
        ]
    )
    html += '<link rel="alternate stylesheet" href="/alternate.css">'
    network = Network(monkeypatch, {"https://example.com/": Response(html, "https://example.com/")})
    source = sources.load_source(url="https://example.com/")
    assert len(source.assets) == 8
    assert all(asset.status == "skipped" for asset in source.assets)
    assert len(network.requests) == 1


def test_stylesheet_failures_degrade_main_document(monkeypatch: pytest.MonkeyPatch) -> None:
    html = '<link rel="stylesheet" href="/bad.css"><link rel="stylesheet" href="/good.css">'
    Network(
        monkeypatch,
        {
            "https://example.com/": Response(html, "https://example.com/"),
            "https://example.com/bad.css": TimeoutError("timed out"),
            "https://example.com/good.css": Response("p{color:red}", "https://example.com/good.css", "text/css"),
        },
    )
    source = sources.load_source(url="https://example.com/")
    assert [asset.status for asset in source.assets] == ["failed", "loaded"]
    assert "timed out" in source.warnings[0]
    assert source.text == html


def test_stylesheet_count_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "MAX_STYLESHEETS", 1)
    html = '<link rel="stylesheet" href="/a.css"><link rel="stylesheet" href="/b.css">'
    network = Network(
        monkeypatch,
        {
            "https://example.com/": Response(html, "https://example.com/"),
            "https://example.com/a.css": Response("p{color:red}", "https://example.com/a.css", "text/css"),
        },
    )
    source = sources.load_source(url="https://example.com/")
    assert [asset.status for asset in source.assets] == ["loaded", "skipped"]
    assert "limit" in source.assets[1].reason
    assert len(network.requests) == 2


def test_response_size_limit_and_main_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "MAX_PAGE_BYTES", 4)
    response = Response("too long", "https://example.com/")
    Network(monkeypatch, {"https://example.com/": response})
    with pytest.raises(UnslopperError, match="4-byte limit"):
        sources.load_source(url="https://example.com/")
    assert response.read_sizes == [5]


def test_asset_size_limit_and_wrong_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sources, "MAX_STYLESHEET_BYTES", 4)
    html = '<link rel="stylesheet" href="/large.css"><link rel="stylesheet" href="/login.css">'
    Network(
        monkeypatch,
        {
            "https://example.com/": Response(html, "https://example.com/"),
            "https://example.com/large.css": Response("too long", "https://example.com/large.css", "text/css"),
            "https://example.com/login.css": Response("oops", "https://example.com/login.css", "text/html"),
        },
    )
    source = sources.load_source(url="https://example.com/")
    assert [asset.status for asset in source.assets] == ["failed", "failed"]
    assert "4-byte limit" in source.assets[0].reason
    assert "text/html" in source.assets[1].reason


def test_imports_are_explicitly_not_inspected(monkeypatch: pytest.MonkeyPatch) -> None:
    css = '/* @import "ignored.css"; */ @import "nested.css"; p{color:red}'
    network = Network(
        monkeypatch, {"https://example.com/main.css": Response(css, "https://example.com/main.css", "text/css")}
    )
    source = sources.load_source(url="https://example.com/main.css")
    assert source.kind == "css"
    assert len(source.assets) == 1
    assert source.assets[0].status == "skipped"
    assert "@import" in source.warnings[0]
    assert len(network.requests) == 1


@pytest.mark.parametrize("content_type", ["text/plain", "text/css"])
def test_css_url_is_classified_by_suffix_or_mime(monkeypatch: pytest.MonkeyPatch, content_type: str) -> None:
    Network(
        monkeypatch,
        {"https://example.com/main.css?q=1": Response("/* css */", "https://example.com/main.css?q=1", content_type)},
    )
    assert sources.load_source(url="https://example.com/main.css?q=1").kind == "css"


def test_local_and_inline_html_never_fetch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    network = Network(monkeypatch, {})
    html = '<link rel="stylesheet" href="https://example.com/a.css"><style>@import "other.css";</style>'
    path = tmp_path / "index.html"
    path.write_text(html)
    for source in (sources.load_source(source=html), sources.load_source(path=path)):
        assert len(source.assets) == 2
        assert all(asset.status == "skipped" for asset in source.assets)
        assert not source.stylesheets
    assert not network.requests


def test_redirect_guard_rejects_cross_origin_before_request() -> None:
    handler = sources._SafeRedirects(sources._origin("https://example.com/"))
    with pytest.raises(ValueError, match="Cross-origin"):
        handler.redirect_request(
            Request("https://example.com/a.css"), None, 302, "Found", {}, "https://other.example/a.css"
        )
    with pytest.raises(ValueError, match="HTTP"):
        handler.redirect_request(Request("https://example.com/a.css"), None, 302, "Found", {}, "file:///tmp/a.css")


def test_redirect_final_response_is_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    Network(
        monkeypatch, {"https://example.com/a.css": Response("p{color:red}", "https://other.example/a.css", "text/css")}
    )
    with pytest.raises(UnslopperError, match="Cross-origin"):
        sources._fetch("https://example.com/a.css", 1024, sources._origin("https://example.com/"))


@pytest.mark.parametrize("url", ["file:///tmp/a", "https://name:secret@example.com/", "https://example.com:bad/"])
def test_invalid_main_url_fails_before_network(monkeypatch: pytest.MonkeyPatch, url: str) -> None:
    network = Network(monkeypatch, {})
    with pytest.raises(UnslopperError):
        sources.load_source(url=url)
    assert not network.requests


def test_minified_link_positions_and_nested_import_coverage(monkeypatch: pytest.MonkeyPatch) -> None:
    html = '<style>p{color:red}</style><link rel="stylesheet" href="/a.css"><style>p{color:blue}</style><link rel="stylesheet" href="/a.css">'
    css = '@import "nested.css"; p{color:green}'
    Network(
        monkeypatch,
        {
            "https://example.com/": Response(html, "https://example.com/"),
            "https://example.com/a.css": Response(css, "https://example.com/a.css", "text/css"),
        },
    )
    source = sources.load_source(url="https://example.com/")
    assert [sheet.line for sheet in source.stylesheets] == [1, 1]
    assert [sheet.column for sheet in source.stylesheets] == [html.index("<link"), html.rindex("<link")]
    assert [asset.status for asset in source.assets] == ["loaded", "skipped"]
    assert "@import" in source.warnings[0]


def test_cross_origin_base_does_not_expand_fetch_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    html = '<base href="https://cdn.example.com/"><link rel="stylesheet" href="style.css">'
    network = Network(monkeypatch, {"https://example.com/": Response(html, "https://example.com/")})
    source = sources.load_source(url="https://example.com/")
    assert source.assets[0].url == "https://cdn.example.com/style.css"
    assert source.assets[0].status == "skipped"
    assert len(network.requests) == 1


def test_fetch_retains_text_api_and_invalid_charset_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Response("hello", "https://example.com/", "text/plain")
    Network(monkeypatch, {"https://example.com/": response})
    assert sources.fetch("https://example.com/") == "hello"
    response.headers.replace_header("Content-Type", "text/plain; charset=unknown-character-set")
    with pytest.raises(UnslopperError, match="Could not fetch"):
        sources.fetch("https://example.com/")


@pytest.mark.parametrize(
    "html",
    [
        '<base href="https://[bad/"><link rel="stylesheet" href="/a.css">',
        '<link rel="stylesheet" href="https://[bad/">',
    ],
)
def test_malformed_asset_urls_degrade_without_losing_document(monkeypatch: pytest.MonkeyPatch, html: str) -> None:
    network = Network(monkeypatch, {"https://example.com/": Response(html, "https://example.com/")})
    source = sources.load_source(url="https://example.com/")
    assert source.text == html
    assert source.assets[0].status == "skipped"
    assert "Malformed" in source.assets[0].reason
    assert len(network.requests) == 1


def test_cached_duplicate_stylesheets_count_toward_occurrence_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    link = '<link rel="stylesheet" href="/a.css">'
    html = link * 1000
    network = Network(
        monkeypatch,
        {
            "https://example.com/": Response(html, "https://example.com/"),
            "https://example.com/a.css": Response("p{color:red}", "https://example.com/a.css", "text/css"),
        },
    )
    source = sources.load_source(url="https://example.com/")
    assert len(source.stylesheets) == sources.MAX_STYLESHEETS
    assert [sheet.column for sheet in source.stylesheets] == [len(link) * i for i in range(sources.MAX_STYLESHEETS)]
    skipped = [asset for asset in source.assets if asset.status == "skipped"]
    assert len(skipped) == 1000 - sources.MAX_STYLESHEETS
    assert "occurrence limit" in source.warnings[0]
    assert len(network.requests) == 2
