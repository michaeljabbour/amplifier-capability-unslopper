"""Load source text and a bounded, explicit inventory of linked stylesheets."""

from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Any, Literal, NamedTuple
from urllib.error import URLError
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from unslopper.schemas import UnslopperError

Kind = Literal["html", "css", "text"]
FETCH_TIMEOUT_SECONDS = 20
MAX_PAGE_BYTES = 4 * 1024 * 1024
MAX_STYLESHEET_BYTES = 1024 * 1024
MAX_STYLESHEETS = 16
USER_AGENT = "unslopper"


class Stylesheet(NamedTuple):
    """A separately loaded stylesheet, preserving its provenance."""

    text: str
    label: str
    line: int = 1
    column: int = 0


class Asset(NamedTuple):
    """Coverage of one stylesheet reference."""

    url: str
    status: Literal["loaded", "skipped", "failed"]
    reason: str = ""
    bytes_read: int = 0


class Source(NamedTuple):
    """Original source text and separately loaded CSS; three-argument construction remains valid."""

    text: str
    label: str
    kind: Kind
    stylesheets: tuple[Stylesheet, ...] = ()
    assets: tuple[Asset, ...] = ()
    warnings: tuple[str, ...] = ()


class _Response(NamedTuple):
    text: str
    url: str
    content_type: str
    bytes_read: int


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.base: str | None = None
        self.links: list[tuple[str, str, int, int]] = []
        self.inline_css: list[str] = []
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "base" and self.base is None and attributes.get("href") is not None:
            self.base = attributes["href"]
        if tag == "style":
            self.in_style = True
        if tag != "link":
            return
        rel = (attributes.get("rel") or "").lower().split()
        if "stylesheet" in rel:
            reason = (
                "Alternate or disabled stylesheet is not inspected."
                if "alternate" in rel or "disabled" in attributes
                else ""
            )
            media = (attributes.get("media") or "").strip().lower()
            if media not in {"", "all", "screen"}:
                reason = f"Conditional stylesheet media={media!r} is not evaluated or inspected."
            self.links.append((attributes.get("href") or "", reason, *self.getpos()))

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.inline_css.append(data)


def _origin(url: str) -> tuple[str, str, int]:
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("Only HTTP(S) URLs without embedded credentials are supported")
    return parts.scheme.lower(), parts.hostname.lower(), parts.port or (443 if parts.scheme.lower() == "https" else 80)


class _SafeRedirects(HTTPRedirectHandler):
    def __init__(self, origin: tuple[str, str, int] | None) -> None:
        self.origin = origin

    def redirect_request(self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Request | None:
        destination = _origin(newurl)
        if self.origin is not None and destination != self.origin:
            raise ValueError("Cross-origin stylesheet redirect is not inspected")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url: str, limit: int, origin: tuple[str, str, int] | None = None) -> _Response:
    try:
        actual_origin = _origin(url)
        if origin is not None and actual_origin != origin:
            raise ValueError("Cross-origin stylesheet is not inspected")
        opener = build_opener(_SafeRedirects(origin))
        with opener.open(Request(url, headers={"User-Agent": USER_AGENT}), timeout=FETCH_TIMEOUT_SECONDS) as response:
            final_url = response.geturl()
            if origin is not None and _origin(final_url) != origin:
                raise ValueError("Cross-origin stylesheet redirect is not inspected")
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise ValueError(f"Response exceeds the {limit}-byte limit")
            charset = response.headers.get_content_charset() or "utf-8"
            return _Response(
                raw.decode(charset, errors="replace"), final_url, response.headers.get_content_type(), len(raw)
            )
    except (URLError, OSError, ValueError, LookupError) as error:
        raise UnslopperError(
            f"Could not fetch {url}: {error}. Check the URL, or save the page and pass its path."
        ) from None


def _imports(css: str, label: str) -> list[Asset]:
    cleaned = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    return [
        Asset(f"{label}#import-{index}", "skipped", "CSS @import is not fetched; imported rules are not inspected.")
        for index, _ in enumerate(re.finditer(r"@import\b", cleaned, re.IGNORECASE), 1)
    ]


def _with_stylesheets(source: Source, network: bool) -> Source:
    assets: list[Asset] = []
    stylesheets: list[Stylesheet] = []
    if source.kind == "css":
        assets.extend(_imports(source.text, source.label))
    elif source.kind == "html":
        parser = _Links()
        parser.feed(source.text)
        assets.extend(_imports("\n".join(parser.inline_css), source.label))
        base_error = ""
        try:
            base = urljoin(source.label, parser.base or "") if network else source.label
        except ValueError as error:
            base = source.label
            base_error = f"Malformed document base URL: {error}. Linked stylesheets are not inspected."
        cached: dict[str, _Response] = {}
        attempted = 0
        for href, reason, line, column in parser.links:
            if network and base_error:
                assets.append(Asset(href, "skipped", base_error))
                continue
            try:
                target = urldefrag(urljoin(base, href))[0] if network else href
            except ValueError as error:
                assets.append(Asset(href, "skipped", f"Malformed stylesheet URL: {error}."))
                continue
            if not href:
                assets.append(Asset(target, "skipped", "Stylesheet link has no href."))
                continue
            if not network:
                reason = "Linked stylesheets are not loaded for local or inline HTML; supply a URL to inspect same-origin CSS."
            if reason:
                assets.append(Asset(target, "skipped", reason))
                continue
            try:
                if _origin(target) != _origin(source.label):
                    assets.append(Asset(target, "skipped", "Cross-origin stylesheet is not inspected."))
                    continue
            except ValueError as error:
                assets.append(Asset(target, "skipped", str(error)))
                continue
            if len(stylesheets) >= MAX_STYLESHEETS:
                assets.append(
                    Asset(
                        target,
                        "skipped",
                        f"Stylesheet occurrence limit ({MAX_STYLESHEETS}) reached; duplicate links count toward this limit.",
                    )
                )
                continue
            if target in cached:
                response = cached[target]
                stylesheets.append(Stylesheet(response.text, response.url, line, column))
                continue
            if attempted >= MAX_STYLESHEETS:
                assets.append(Asset(target, "skipped", f"Stylesheet limit ({MAX_STYLESHEETS}) reached."))
                continue
            attempted += 1
            try:
                response = _fetch(target, MAX_STYLESHEET_BYTES, _origin(source.label))
                if response.content_type not in {"text/css", "text/plain", "application/octet-stream"}:
                    assets.append(Asset(target, "failed", f"Expected CSS, received {response.content_type}."))
                    continue
                cached[target] = response
                stylesheets.append(Stylesheet(response.text, response.url, line, column))
                assets.append(Asset(target, "loaded", bytes_read=response.bytes_read))
                assets.extend(_imports(response.text, response.url))
            except UnslopperError as error:
                assets.append(Asset(target, "failed", str(error)))
    warnings = tuple(dict.fromkeys(asset.reason for asset in assets if asset.status != "loaded"))
    return source._replace(stylesheets=tuple(stylesheets), assets=tuple(assets), warnings=warnings)


def load_source(path: Path | None = None, url: str | None = None, source: str | None = None) -> Source:
    """Load exactly one input; URL HTML retains at most 16 same-origin stylesheet occurrences."""
    given = [name for name, value in (("path", path), ("url", url), ("source", source)) if value is not None]
    if len(given) != 1:
        raise UnslopperError(
            "Give exactly one of a file path, a URL, or inline source text. "
            f"Got {', '.join(given) if given else 'none'}."
        )
    if path is not None:
        if not path.is_file():
            raise UnslopperError(f"{path} is not a file. Pass the HTML or CSS file to look at.")
        return _with_stylesheets(Source(path.read_text(encoding="utf-8"), str(path), kind_of(path.suffix, None)), False)
    if url is not None:
        response = _fetch(url, MAX_PAGE_BYTES)
        suffix = Path(urlsplit(response.url).path).suffix
        kind = "css" if response.content_type == "text/css" else kind_of(suffix, response.text)
        return _with_stylesheets(Source(response.text, response.url, kind), True)
    assert source is not None
    return _with_stylesheets(Source(source, "inline", kind_of("", source)), False)


def kind_of(suffix: str, text: str | None) -> Kind:
    """Infer HTML, CSS or plain text from a suffix or inline text."""
    if suffix.lower() in {".html", ".htm"}:
        return "html"
    if suffix.lower() == ".css":
        return "css"
    if text is not None:
        head = text.lstrip()[:200].lower()
        if head.startswith("<") or "<html" in head or "<div" in head or "<body" in head:
            return "html"
        if "{" in text and ":" in text and "<" not in text:
            return "css"
    return "text"


def fetch(url: str) -> str:
    """Fetch a bounded HTTP(S) body as text."""
    return _fetch(url, MAX_PAGE_BYTES).text
