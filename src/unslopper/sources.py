"""Loading the design a capability looks at: a file, a URL or inline text."""

from pathlib import Path
from typing import Literal, NamedTuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from unslopper.schemas import UnslopperError

Kind = Literal["html", "css", "text"]
FETCH_TIMEOUT_SECONDS = 20
USER_AGENT = "unslopper"


class Source(NamedTuple):
    """What a scan or audit reads: the text, where it came from, and what kind of text it is."""

    text: str
    label: str
    kind: Kind


def load_source(path: Path | None = None, url: str | None = None, source: str | None = None) -> Source:
    """Exactly one of `path`, `url` or `source`, loaded as text with a label naming where it came from."""
    given = [name for name, value in (("path", path), ("url", url), ("source", source)) if value is not None]
    if len(given) != 1:
        raise UnslopperError(
            "Give exactly one of a file path, a URL, or inline source text. "
            f"Got {', '.join(given) if given else 'none'}."
        )
    if path is not None:
        if not path.is_file():
            raise UnslopperError(f"{path} is not a file. Pass the HTML or CSS file to look at.")
        return Source(path.read_text(encoding="utf-8"), str(path), kind_of(path.suffix, None))
    if url is not None:
        return Source(fetch(url), url, "html")
    assert source is not None
    return Source(source, "inline", kind_of("", source))


def kind_of(suffix: str, text: str | None) -> Kind:
    """HTML, CSS or plain text, from the file suffix or, for inline text, from what it looks like."""
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
    """The body of a page over HTTP, as text."""
    if not url.startswith(("http://", "https://")):
        raise UnslopperError(f"{url} is not an http(s) URL.")
    try:
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=FETCH_TIMEOUT_SECONDS) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (URLError, TimeoutError, ValueError) as error:
        raise UnslopperError(
            f"Could not fetch {url}: {error}. Check the URL, or save the page and pass its path."
        ) from None
