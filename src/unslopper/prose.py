"""Shared prose scope, editorial policy, and conservative mechanical fidelity checks."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re

from unslopper.schemas import UnslopperError

MAX_PROSE_CHARS = 80_000
POLICY_PATH = Path(__file__).with_name("prose-quality.md")
FENCE = re.compile(r"(?m)^[ \t]{0,3}(`{3,}|~{3,})[^\n]*(?:\n|$)")
INLINE_CODE = re.compile(r"(`+)([^`\n]|`(?!`))*?\1")
PROTECTED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("frontmatter", re.compile(r"\A---[^\S\n]*\n.*?\n(?:---|\.\.\.)[^\S\n]*(?:\n|$)", re.DOTALL)),
    ("blockquote", re.compile(r"(?m)^[ \t]{0,3}>[^\n]*(?:\n(?![ \t]*(?:\n|$))[^\n]*)*(?:\n|$)")),
    ("reference", re.compile(r"(?m)^[ \t]{0,3}\[[^\]\n]+\]:[^\n]*(?:\n|$)")),
    ("bibliography", re.compile(r"(?im)^#{1,6}[ \t]+(?:references|bibliography|works cited)[ \t#]*\n[\s\S]*")),
    ("link-target", re.compile(r"(?<=\])\((?:[^()\n]|\([^()\n]*\))*\)")),
    ("citation", re.compile(r"\[(?:@[^\]\n]+|\d[\d,; \-]*|\^[^\]\n]+)\]")),
    ("citation", re.compile(r"\([^()\n]*\bet al\.,?\s*\d{4}[a-z]?[^()\n]*\)")),
    ("citation", re.compile(r"\([^()\n]*[A-Za-z][^()\n]*,?\s+\d{4}[a-z]?[^()\n]*\)")),
    ("citation", re.compile(r"\b[A-Z][A-Za-z'-]+(?:\s+et\s+al\.)?\s*\(\d{4}[a-z]?\)")),
    ("url", re.compile(r"https?://[^\s<>\"')\]]+")),
    ("quotation", re.compile(r'"[^"]+"|\u201c[^\u201d]+\u201d')),
    (
        "quotation",
        re.compile(
            r"(?<!\w)'(?:[^']|(?<=\w)'(?=\w))+'(?!\w)|(?<!\w)\u2018(?:[^\u2019]|(?<=\w)\u2019(?=\w))+\u2019(?!\w)"
        ),
    ),
    (
        "markup",
        re.compile(
            r"<!--.*?-->|<(?:code|pre|script|style)\b[^>]*>.*?</(?:code|pre|script|style)\s*>", re.I | re.DOTALL
        ),
    ),
    ("markup", re.compile(r"</?[A-Za-z][^>\n]*>")),
)
NUMBER = re.compile(r"(?<![\w])[-+]?\d+(?:[.,:/-]\d+)*(?:\s?%|[A-Za-z]+)?(?![\w])")
QUALIFIER = re.compile(
    r"\b(?:most|may|might|could|some|many|likely|possibly|probably|approximately|about|at least|at most|up to|not|never|no)\b",
    re.I,
)


@dataclass(frozen=True)
class ProtectedSpan:
    """A syntactic region excluded from linting and retained verbatim by an edit."""

    start: int
    end: int
    kind: str


def policy_text() -> str:
    """Read the one editorial policy used by prose and design-copy model paths."""
    return POLICY_PATH.read_text(encoding="utf-8").strip()


def protected_spans(text: str) -> list[ProtectedSpan]:
    """Find conservative Markdown and quotation exclusions, preserving original character offsets."""
    spans: list[ProtectedSpan] = []
    position = 0
    while opening := FENCE.search(text, position):
        marker = opening.group(1)
        closing = re.search(
            rf"(?m)^[ \t]{{0,3}}{re.escape(marker[0])}{{{len(marker)},}}[ \t]*(?:\n|$)", text[opening.end() :]
        )
        end = opening.end() + closing.end() if closing else len(text)
        spans.append(ProtectedSpan(opening.start(), end, "code"))
        position = end
    for kind, pattern in (("code", INLINE_CODE), *PROTECTED_PATTERNS):
        for match in pattern.finditer(text):
            if any(span.start <= match.start() and match.end() <= span.end for span in spans):
                continue
            spans.append(ProtectedSpan(match.start(), match.end(), kind))
    return sorted(spans, key=lambda span: (span.start, span.end))


def scoped_text(text: str) -> tuple[str, list[ProtectedSpan]]:
    """Mask excluded syntax without changing line numbers or character offsets."""
    spans = protected_spans(text)
    chars = list(text)
    for span in spans:
        chars[span.start : span.end] = ["\n" if char == "\n" else " " for char in text[span.start : span.end]]
    return "".join(chars), spans


def check_fidelity(original: str, edited: str) -> None:
    """Reject lost protected text, changed numbers, or changed calibration/negation tokens.

    These are mechanical guards, not proof of semantic equivalence or factual correctness.
    """
    if not edited.strip():
        raise UnslopperError("The prose edit is empty. Retry the edit; the original file is untouched.")
    preserved = Counter(original[span.start : span.end] for span in protected_spans(original))
    missing = [value for value, count in preserved.items() if edited.count(value) < count]
    if missing:
        raise UnslopperError(
            "The prose edit changed protected code, quotations, citations, references or link targets. "
            "Keep those regions verbatim and retry; the original file is untouched."
        )
    if Counter(NUMBER.findall(original)) != Counter(NUMBER.findall(edited)):
        raise UnslopperError(
            "The prose edit changed numeric details. Keep them verbatim and retry; the original file is untouched."
        )
    if Counter(token.lower() for token in QUALIFIER.findall(original)) != Counter(
        token.lower() for token in QUALIFIER.findall(edited)
    ):
        raise UnslopperError(
            "The prose edit changed uncertainty, scope or negation tokens. Keep calibration intact and retry; "
            "the original file is untouched."
        )
