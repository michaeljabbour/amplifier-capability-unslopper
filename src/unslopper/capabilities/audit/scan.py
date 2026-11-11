"""The twenty indicators as static checks over a document. Each returns the evidence it found, or nothing.

Every check errs toward silence: a hit a person cannot confirm by opening the file at the line named is worse
than a miss, since the model-backed audit reads the same source and catches what static code cannot.
"""

from collections.abc import Callable
import colorsys
import re

from unslopper import knowledge
from unslopper.capabilities.audit.document import (
    CODE_TAGS,
    HEADING_TAGS,
    SKIPPED_TEXT_TAGS,
    Document,
    Element,
    last_compounds,
    length_px,
)
from unslopper.color import parse_hex
from unslopper.schemas import Evidence, ScanHit, UnslopperError

MAX_EVIDENCE = 8
SMALL_PX = 13.0
DISPLAY_PX = 24.0
LARGE_RADIUS_PX = 16.0
PILL_RADIUS_PX = 100.0
QUOTE_LENGTH = 100

TREND_SERIFS = ("Instrument Serif", "Playfair Display", "DM Serif Display", "Fraunces", "Cormorant")
MONO_HINTS = ("mono", "courier", "consolas", "menlo", "monaco", "fira code", "source code pro")
HEADING_CLASS = re.compile(r"title|headline|heading|hero|display|^h[1-6]$", re.I)
INTERACTIVE = re.compile(
    r"^(button|input|select|textarea|a|table|td|th|tr|hr|img|iframe|video)$|btn|button|input", re.I
)
EYEBROW_CLASS = re.compile(r"eyebrow|kicker|overline", re.I)
PILL_CLASS = re.compile(r"(^|[-_ ])(pill|badge|tag|chip)s?([-_ ]|$)", re.I)
FILLER = re.compile(
    r"^(new|beta|alpha|ai|ai[- ]powered|powered by ai|coming soon|popular|hot|pro|featured|premium|smart|fast|secure)$",
    re.I,
)
BUZZWORDS = (
    "seamlessly",
    "seamless",
    "powerful",
    "empowering",
    "empower",
    "effortlessly",
    "effortless",
    "leverage",
    "cutting-edge",
    "ai-driven",
    "ai-powered",
    "next-generation",
    "next-gen",
    "revolutionary",
    "revolutionize",
    "game-changing",
    "supercharge",
    "elevate",
    "streamline",
    "robust",
    "state-of-the-art",
    "best-in-class",
    "world-class",
    "all-in-one",
    "frictionless",
    "10x",
)
BUZZWORD = re.compile(r"(?<![\w-])(" + "|".join(re.escape(word) for word in BUZZWORDS) + r")(?![\w-])", re.I)
MONTHS = re.compile(r"^\s*0\d\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)", re.I)
NUMBERED = re.compile(r"^\s*0\d(?:\s*[^\w\s]|\s+[A-Za-z])")
NUMERIC_STAT = re.compile(r"^[+-]?[$\u20ac\u00a3]?\d[\d.,]*\s?[%kKmMxX+]?$")
PATH = re.compile(r"(?<![\w/])[\w.-]+/[\w./-]*\w")
ARROWS = re.compile(r"->|=>|<-|\u2192|\u2190|\u21d2|\u27f6")
COMMENT_SYNTAX = re.compile(r"^\s*(//|/\*|#\s)")
# Hex, rgb()/rgba() and hsl()/hsla() colours carrying an alpha below one, in legacy and slash syntax.
ALPHA_HEX = re.compile(r"#([0-9a-f]{6})([0-9a-f]{2})\b|#([0-9a-f]{3})([0-9a-f])\b", re.I)
ALPHA_FUNCTION = re.compile(
    r"(rgba?|hsla?)\(\s*([\d.]+(?:deg)?)[\s,]+([\d.]+%?)[\s,]+([\d.]+%?)\s*[,/]\s*([\d.]+%?)\s*\)", re.I
)
COLOR_STOP = re.compile(r"#[0-9a-f]{3,8}\b|(?:rgba?|hsla?)\([^)]*\)|\b[a-z]+\b", re.I)
NAMED_HUES = {
    "purple": 270.0,
    "violet": 270.0,
    "indigo": 275.0,
    "blueviolet": 271.0,
    "mediumpurple": 260.0,
    "slateblue": 248.0,
    "blue": 240.0,
    "royalblue": 225.0,
    "dodgerblue": 210.0,
    "cornflowerblue": 219.0,
    "deepskyblue": 195.0,
    "cyan": 180.0,
    "aqua": 180.0,
    "magenta": 300.0,
    "fuchsia": 300.0,
}
BOX_DRAWING = re.compile(r"[\u2500-\u259f]")

Check = Callable[[Document], list[Evidence]]


def scan_document(document: Document) -> list[ScanHit]:
    """Every indicator the checks found, in the course's order, each with at most MAX_EVIDENCE pieces of evidence."""
    hits: list[ScanHit] = []
    for name, check in CHECKS:
        evidence = _distinct(check(document))
        if evidence:
            found = knowledge.indicator(name)
            hits.append(
                ScanHit(
                    indicator=found.name, layer=found.layer, evidence=evidence[:MAX_EVIDENCE], fix_ids=found.fix_ids
                )
            )
    return hits


# region: Type


def instrument_serif(document: Document) -> list[Evidence]:
    evidence: list[Evidence] = []
    for source in document.declared():
        family = source.declarations.get("font-family", "")
        for serif in TREND_SERIFS:
            if serif.lower() in family.lower():
                evidence.append(Evidence(location=source.where, detail=f"font-family: {family}"))
                break
    for url in document.font_urls:
        for serif in TREND_SERIFS:
            if serif.replace(" ", "+").lower() in url.lower():
                evidence.append(Evidence(location="Google Fonts stylesheet", detail=f"loads {serif}: {url}"))
    return evidence


def excessive_italics(document: Document) -> list[Evidence]:
    evidence: list[Evidence] = []
    for heading in document.headings():
        italics = [
            node
            for node in heading.walk()
            if node is not heading and node.tag in {"em", "i"} and not document.hidden(node)
        ]
        if not italics:
            continue
        italic_text = " ".join(document.text(node) for node in italics)
        if len(italic_text) < len(document.text(heading)):
            evidence.append(
                Evidence(
                    location=heading.describe(),
                    detail=f"{quote(document.text(heading))} with {quote(italic_text)} in italics",
                )
            )
    for source in document.declared():
        if source.declarations.get("font-style", "").lower() == "italic" and targets_headings(source.selector):
            evidence.append(Evidence(location=source.where, detail="font-style: italic on a heading"))
    return evidence


def negative_kerning(document: Document) -> list[Evidence]:
    """Slight tightening on display type is the course's own advice, so only small text or collisions count."""
    evidence: list[Evidence] = []
    for source in document.declared():
        value = source.declarations.get("letter-spacing")
        if value is None or not value.strip().startswith("-"):
            continue
        # em and rem are scaled against 1 so the number stays in em; -0.05em is where letters start to touch.
        amount = length_px(value, 1.0)
        size = source.px("font-size")
        on_small = size is not None and size < DISPLAY_PX
        on_body = not targets_headings(source.selector) and (
            on_small or (size is None and targets_text(source.selector))
        )
        colliding = amount is not None and (("em" in value and amount <= -0.05) or ("px" in value and amount <= -1))
        if on_body or colliding:
            evidence.append(
                Evidence(location=source.where, detail=f"letter-spacing: {value}" + (f" at {size:g}px" if size else ""))
            )
    return evidence


def excessive_mono(document: Document) -> list[Evidence]:
    evidence: list[Evidence] = []
    small = False
    for source in document.declared():
        family = source.declarations.get("font-family", "")
        if source.code or not is_mono(family):
            continue
        size = source.px("font-size")
        small = small or (size is not None and size <= SMALL_PX - 1)
        evidence.append(
            Evidence(location=source.where, detail=f"font-family: {family}" + (f" at {size:g}px" if size else ""))
        )
    return evidence if small or len(evidence) >= 2 else []


def all_caps_subtitles(document: Document) -> list[Evidence]:
    if document.root is None:
        return [
            Evidence(location=source.where, detail="text-transform: uppercase on small text")
            for source in document.declared()
            if source.declarations.get("text-transform", "").lower() == "uppercase"
            and is_small(source.px("font-size"))
            and not targets_headings(source.selector)
            and not EYEBROW_CLASS.search(source.selector)
        ]
    evidence: list[Evidence] = []
    for element in document.elements():
        if element.tag in HEADING_TAGS or element.inside(SKIPPED_TEXT_TAGS | CODE_TAGS | {"button", "a", "nav"}):
            continue
        if is_eyebrow(document, element) or not is_small(document.font_size(element)):
            continue
        text = element.own_text() or document.text(element)
        if shouting(text) or (document.style(element).get("text-transform", "").lower() == "uppercase" and text):
            evidence.append(Evidence(location=element.describe(), detail=quote(text)))
    return evidence


def periods_in_titles(document: Document) -> list[Evidence]:
    evidence: list[Evidence] = []
    ending: list[Evidence] = []
    for heading in document.headings():
        text = document.text(heading)
        if not text.endswith("."):
            continue
        sentences = [part.strip() for part in re.split(r"[.!?](?:\s+|$)", text) if part.strip()]
        if len(sentences) >= 2 and all(len(part.split()) <= 5 for part in sentences):
            evidence.append(Evidence(location=heading.describe(), detail=quote(text)))
        elif len(text.split()) <= 6:
            ending.append(Evidence(location=heading.describe(), detail=quote(text)))
    return evidence or (ending if len(ending) >= 2 else [])


# endregion

# region: Surface


def gradient_backgrounds(document: Document) -> list[Evidence]:
    cool: list[Evidence] = []
    plain: list[Evidence] = []
    for source in document.declared():
        for name in ("background", "background-image"):
            value = source.declarations.get(name, "")
            if "-gradient(" not in value:
                continue
            hues = [hue for hue in (hue_of(stop) for stop in COLOR_STOP.findall(value)) if hue is not None]
            blue_purple = [hue for hue in hues if 200 <= hue <= 300]
            if len(blue_purple) >= 2 and len(blue_purple) * 2 >= len(hues):
                cool.append(Evidence(location=source.where, detail=f"{name}: {clip(value)} (purple to blue)"))
            else:
                plain.append(Evidence(location=source.where, detail=f"{name}: {clip(value)}"))
    return cool or (plain if len(plain) >= 3 else [])


def shades_and_opacities(document: Document) -> list[Evidence]:
    alphas: dict[str, dict[str, str]] = {}
    opacities: dict[str, str] = {}
    mixes: list[Evidence] = []
    for source in document.declared():
        for name, value in source.declarations.items():
            for base, alpha, literal in translucent_colors(value):
                alphas.setdefault(base, {})[alpha] = f"{source.where}: {name}: {literal}"
            if name == "opacity":
                number = _number(value)
                if number is not None and 0.3 < number < 1:
                    opacities[value] = source.where
            if "color-mix(" in value:
                mixes.append(Evidence(location=source.where, detail=f"{name}: {clip(value)}"))
    evidence: list[Evidence] = []
    for base, found in alphas.items():
        if len(found) >= 4:
            evidence.extend(
                Evidence(
                    location=where.split(": ", 1)[0],
                    detail=where.split(": ", 1)[1] + f" (one of {len(found)} alphas of {base})",
                )
                for where in found.values()
            )
    if len(opacities) >= 3:
        evidence.extend(Evidence(location=where, detail=f"opacity: {value}") for value, where in opacities.items())
    if len(mixes) >= 3:
        evidence.extend(mixes)
    return evidence


def squircles(document: Document) -> list[Evidence]:
    large: list[Evidence] = []
    for source in document.declared():
        radius = radius_px(source.declarations)
        if radius is not None and LARGE_RADIUS_PX <= radius < PILL_RADIUS_PX:
            large.append(
                Evidence(location=source.where, detail=f"border-radius: {source.declarations['border-radius']}")
            )
    nested: list[Evidence] = []
    for element in document.elements():
        inner = radius_px(document.style(element))
        if inner is None or inner < 12 or inner >= PILL_RADIUS_PX:
            continue
        for ancestor in element.ancestors():
            style = document.style(ancestor)
            outer = radius_px(style)
            if outer is None or outer >= PILL_RADIUS_PX:
                continue
            padding = length_px(style.get("padding", "0").split()[0])
            if outer >= 12 and padding and inner >= outer:
                nested.append(
                    Evidence(
                        location=element.describe(),
                        detail=f"radius {inner:g}px inside {ancestor.describe()} with radius {outer:g}px and padding {padding:g}px; concentric would be {max(outer - padding, 0):g}px",
                    )
                )
            break
    return (large if len(large) >= 3 else []) + nested


def containers_with_borders(document: Document) -> list[Evidence]:
    bordered = [
        Evidence(
            location=source.where,
            detail=f"border: {source.declarations.get('border') or source.declarations.get('border-width', '')}",
        )
        for source in document.declared()
        if hairline_border(source.declarations) and not targets_interactive(source.selector)
    ]
    nested: list[Evidence] = []
    for element in document.elements():
        if (
            element.tag in SKIPPED_TEXT_TAGS
            or INTERACTIVE.match(element.tag)
            or not hairline_border(document.style(element))
        ):
            continue
        for ancestor in element.ancestors():
            if hairline_border(document.style(ancestor)):
                nested.append(
                    Evidence(location=element.describe(), detail=f"bordered box inside bordered {ancestor.describe()}")
                )
                break
    return (bordered if len(bordered) >= 3 else []) + nested


def overusing_dividers(document: Document) -> list[Evidence]:
    rules = [
        Evidence(location=source.where, detail=f"{name}: {source.declarations[name]}")
        for source in document.declared()
        for name in ("border-top", "border-bottom")
        if name in source.declarations
        and "solid" in source.declarations[name]
        and (length_px(source.declarations[name].split()[0]) or 0) <= 1
        and not hairline_border(source.declarations)
        and not re.search(r"\b(table|td|th|tr|input|nav|footer|header)\b", source.selector)
    ]
    hrs = [
        Evidence(location=element.describe(), detail="<hr>") for element in document.elements() if element.tag == "hr"
    ]
    return (hrs if len(hrs) >= 2 else []) + (rules if len(rules) >= 3 else [])


def dithering(document: Document) -> list[Evidence]:
    evidence = [
        Evidence(location=element.describe(), detail=f"class or id names dithering: {name}")
        for element in document.elements()
        for name in (*element.classes, element.id or "")
        if "dither" in name.lower()
    ]
    evidence.extend(
        Evidence(location=rule.where, detail="selector names dithering")
        for rule in document.declared()
        if "dither" in rule.selector.lower()
    )
    evidence.extend(
        Evidence(location="comment", detail=clip(comment.strip()))
        for comment in document.comments
        if "dither" in comment.lower()
    )
    return evidence


def ascii_images(document: Document) -> list[Evidence]:
    evidence: list[Evidence] = []
    for element in document.elements():
        if any("ascii" in name.lower() for name in (*element.classes, element.id or "")):
            evidence.append(Evidence(location=element.describe(), detail="class or id names ASCII art"))
            continue
        if element.tag != "pre" or any(ancestor.tag == "pre" for ancestor in element.ancestors()):
            continue
        text = document.text(element)
        lines = [
            line
            for line in "".join(child for child in element.children if isinstance(child, str)).splitlines()
            if line.strip()
        ]
        compact = text.replace(" ", "")
        symbols = sum(1 for char in compact if not char.isalnum())
        if (
            len(lines) >= 3
            and len(compact) >= 40
            and (symbols * 2 >= len(compact) or len(BOX_DRAWING.findall(text)) >= 20)
        ):
            evidence.append(
                Evidence(location=element.describe(), detail=f"{len(lines)} lines of symbols, {quote(lines[0])} first")
            )
    return evidence


# endregion

# region: Structure


def tags_and_pills(document: Document) -> list[Evidence]:
    if document.root is None:
        return [
            Evidence(
                location=source.where, detail=f"border-radius: {source.declarations['border-radius']} on small text"
            )
            for source in document.declared()
            if (radius_px(source.declarations) or 0) >= PILL_RADIUS_PX
            and PILL_CLASS.search(source.selector)
            and is_small(source.px("font-size"))
            and not targets_interactive(source.selector)
        ]
    found: list[tuple[Element, str]] = []
    for element in document.elements():
        if functional_control(element) or element.inside(SKIPPED_TEXT_TAGS | CODE_TAGS):
            continue
        text = document.text(element)
        if not text or len(text.split()) > 3:
            continue
        radius = radius_px(document.style(element))
        if (radius is not None and radius >= PILL_RADIUS_PX) or any(
            PILL_CLASS.search(name) for name in element.classes
        ):
            found.append((element, text))
    if len(found) >= 2 or any(FILLER.match(text) for _, text in found):
        return [Evidence(location=element.describe(), detail=quote(text)) for element, text in found]
    return []


def functional_control(element: Element) -> bool:
    """Pill-shaped navigation and controls are not decorative badges."""
    children = element.elements()
    if children and not element.own_text() and all(functional_control(child) for child in children):
        return True
    roles = {"button", "link", "tab", "checkbox", "radio", "option", "switch", "menuitem", "searchbox"}
    return any(
        INTERACTIVE.match(node.tag)
        or node.tag in {"nav", "label", "summary"}
        or node.attrs.get("role", "").lower() in roles
        for node in (element, *element.ancestors())
    )


def eyebrows(document: Document) -> list[Evidence]:
    if document.root is None:
        return [
            Evidence(
                location=source.where,
                detail="an eyebrow class"
                + (", uppercase" if source.declarations.get("text-transform") == "uppercase" else ""),
            )
            for source in document.declared()
            if EYEBROW_CLASS.search(source.selector)
        ]
    evidence: list[Evidence] = []
    for element in document.elements():
        if is_eyebrow(document, element):
            following = element.next_element()
            assert following is not None
            evidence.append(
                Evidence(
                    location=element.describe(),
                    detail=f"{quote(document.text(element))} above {quote(document.text(following))}",
                )
            )
    return evidence


def section_numbering(document: Document) -> list[Evidence]:
    evidence = [
        Evidence(location=source.where, detail=f"{name}: {value}")
        for source in document.declared()
        for name, value in source.declarations.items()
        if "decimal-leading-zero" in value
    ]
    for element in document.elements():
        if element.tag == "time" or element.inside(SKIPPED_TEXT_TAGS | CODE_TAGS):
            continue
        text = element.own_text() or document.text(element)
        if len(text.split()) <= 8 and NUMBERED.match(text) and not MONTHS.match(text):
            evidence.append(Evidence(location=element.describe(), detail=quote(text)))
    return evidence


def code_breadcrumbs(document: Document) -> list[Evidence]:
    """A one-line path or arrow in monospace outside code. A multi-line mono block is output, not decoration."""
    evidence: list[Evidence] = []
    for element in document.elements():
        if element.inside(SKIPPED_TEXT_TAGS | CODE_TAGS) or not is_mono(document.font_family(element) or ""):
            continue
        text = element.own_text() or document.text(element)
        if not text or len(text.split()) > 12:
            continue
        if any(
            is_block_of_output(document, node)
            for node in (element, *element.ancestors())
            if is_mono(document.font_family(node) or "")
        ):
            continue
        if PATH.search(text) or ARROWS.search(text) or COMMENT_SYNTAX.match(text):
            evidence.append(Evidence(location=element.describe(), detail=quote(text)))
    return evidence


# endregion

# region: Content


def verbose_text(document: Document) -> list[Evidence]:
    found: dict[str, Evidence] = {}
    for element in document.elements():
        if element.inside(SKIPPED_TEXT_TAGS | CODE_TAGS):
            continue
        for match in BUZZWORD.finditer(element.own_text()):
            found.setdefault(
                match.group(1).lower(),
                Evidence(location=element.describe(), detail=f"{quote(match.group(1))} in {quote(element.own_text())}"),
            )
    restated: list[Evidence] = []
    for heading in document.headings():
        following = heading.next_element()
        if following is None or document.hidden(following) or following.tag not in {"p", "div"}:
            continue
        heading_words = content_words(document.text(heading))
        if (
            len(heading_words) >= 3
            and len(heading_words & content_words(document.text(following))) * 10 >= len(heading_words) * 6
        ):
            restated.append(Evidence(location=following.describe(), detail=f"restates {quote(document.text(heading))}"))
    if len(found) >= 2 or (found and restated) or len(restated) >= 2:
        return [*found.values(), *restated]
    return []


def detailed_ui(document: Document) -> list[Evidence]:
    stats: list[Evidence] = []
    dots: list[Evidence] = []
    for element in document.elements():
        if element.inside(SKIPPED_TEXT_TAGS | CODE_TAGS):
            continue
        text = document.text(element)
        if text and looks_like_stat(text) and not element.elements() and is_small(document.font_size(element), 12):
            stats.append(Evidence(location=element.describe(), detail=quote(text)))
        style = document.style(element)
        width = length_px(style.get("width", ""))
        if (
            not text
            and width is not None
            and width <= 12
            and (style.get("border-radius", "").strip() == "50%" or (radius_px(style) or 0) >= width / 2)
        ):
            dots.append(Evidence(location=element.describe(), detail=f"{width:g}px status dot"))
    return (stats if len(stats) >= 6 else []) + (dots if len(dots) >= 4 else [])


def detailed_diagrams(document: Document) -> list[Evidence]:
    evidence: list[Evidence] = []
    for element in document.elements():
        if element.tag != "svg" or any(ancestor.tag == "svg" for ancestor in element.ancestors()):
            continue
        nodes = list(element.walk())
        labels = sum(1 for node in nodes if node.tag == "text")
        effects = sum(1 for node in nodes if node.tag in {"marker", "filter", "fegaussianblur", "lineargradient"})
        if len(nodes) >= 80 and (labels >= 5 or effects >= 2):
            evidence.append(
                Evidence(
                    location=element.describe(),
                    detail=f"inline svg with {len(nodes)} elements, {labels} text labels and {effects} markers, filters or gradients",
                )
            )
    return evidence


# endregion

# Names are the indicator names in knowledge.INDICATORS, so layer and fixes are read from there, never retyped.
CHECKS: tuple[tuple[str, Check], ...] = (
    ("Instrument Serif", instrument_serif),
    ("Excessive italics", excessive_italics),
    ("Negative kerning", negative_kerning),
    ("Excessive mono fonts", excessive_mono),
    ("ALL CAPS subtitles", all_caps_subtitles),
    ("Periods in titles", periods_in_titles),
    ("Gradient backgrounds", gradient_backgrounds),
    ("Color shades and opacities", shades_and_opacities),
    ("Squircles", squircles),
    ("Containers with borders", containers_with_borders),
    ("Overusing dividers", overusing_dividers),
    ("Dithering", dithering),
    ("ASCII images", ascii_images),
    ("Tags and pills", tags_and_pills),
    ("Eyebrows", eyebrows),
    ("Section numbering", section_numbering),
    ("Code breadcrumbs", code_breadcrumbs),
    ("Verbose, redundant text", verbose_text),
    ("Over-the-top detailed UI", detailed_ui),
    ("Overly detailed diagrams", detailed_diagrams),
)

# region: Helpers


def is_eyebrow(document: Document, element: Element) -> bool:
    """A short, small or uppercase line whose next sibling is a heading."""
    following = element.next_element()
    if (
        following is None
        or document.hidden(following)
        or following.tag not in HEADING_TAGS
        or element.tag in HEADING_TAGS
    ):
        return False
    if element.inside(SKIPPED_TEXT_TAGS | CODE_TAGS):
        return False
    text = element.own_text() or document.text(element)
    if not text or len(text.split()) > 8:
        return False
    if any(EYEBROW_CLASS.search(name) for name in element.classes) or shouting(text):
        return True
    uppercase = document.style(element).get("text-transform", "").lower() == "uppercase" or all_caps(text)
    return uppercase and is_small(document.font_size(element))


def all_caps(text: str) -> bool:
    """At least three letters, every one uppercase; enough right above a heading, where the position does the rest."""
    letters = [char for char in text if char.isalpha()]
    return len(letters) >= 3 and all(char.isupper() for char in letters)


def is_block_of_output(document: Document, element: Element) -> bool:
    return any(child.tag == "br" for child in element.elements()) or len(document.text(element).split()) > 12


def shouting(text: str) -> bool:
    """At least two words and six letters, every letter uppercase."""
    letters = [char for char in text if char.isalpha()]
    words = [word for word in re.split(r"\s+", text) if any(char.isalpha() for char in word)]
    return len(letters) >= 6 and len(words) >= 2 and all(char.isupper() for char in letters)


def looks_like_stat(text: str) -> bool:
    """A figure with a unit, a sign or at least two digits; a lone digit is a marker, not a stat."""
    return bool(NUMERIC_STAT.match(text)) and (
        len(re.sub(r"\D", "", text)) >= 2 or bool(re.search(r"[%$\u20ac\u00a3kKmMxX+]", text))
    )


def is_small(size: float | None, limit: float = SMALL_PX) -> bool:
    return size is not None and size <= limit


def is_mono(family: str) -> bool:
    lowered = family.lower()
    return any(hint in lowered for hint in MONO_HINTS)


def targets_headings(selector: str) -> bool:
    compounds = last_compounds(selector)
    return bool(compounds) and all(
        re.match(r"^h[1-6]\b", compound) or HEADING_CLASS.search(compound) for compound in compounds
    )


def targets_text(selector: str) -> bool:
    """Selectors that reach running text: the page, paragraphs, lists, spans and the universal selector."""
    return any(
        re.match(r"^(\*|html|body|p|li|span|a|small|label|td|dd|dt|blockquote)\b", compound) or compound == "*"
        for compound in last_compounds(selector)
    )


def targets_interactive(selector: str) -> bool:
    return any(INTERACTIVE.search(compound) for compound in last_compounds(selector))


def hairline_border(declarations: dict[str, str]) -> bool:
    border = declarations.get("border", "")
    if "solid" in border:
        width = length_px(border.split()[0])
        return width is not None and 0 < width <= 2
    if declarations.get("border-style", "") == "solid":
        width = length_px(declarations.get("border-width", "1px").split()[0])
        return width is not None and 0 < width <= 2
    return False


def radius_px(declarations: dict[str, str]) -> float | None:
    value = declarations.get("border-radius")
    if value is None:
        return None
    sizes = [length_px(part) for part in value.split("/")[0].split()]
    known = [size for size in sizes if size is not None]
    if value.strip().endswith("%"):
        return None
    return max(known) if known else None


def translucent_colors(value: str) -> list[tuple[str, str, str]]:
    """Each colour with an alpha below one in the value, as (base colour, alpha, the literal as written)."""
    found: list[tuple[str, str, str]] = []
    for match in ALPHA_FUNCTION.finditer(value):
        alpha = _number(match.group(5))
        if alpha is not None and alpha < (100 if match.group(5).endswith("%") else 1):
            base = f"{match.group(1).rstrip('a')}({match.group(2)}, {match.group(3)}, {match.group(4)})"
            found.append((base, match.group(5), match.group()))
    for match in ALPHA_HEX.finditer(value):
        base, alpha = (match.group(1), match.group(2)) if match.group(1) else (match.group(3), match.group(4))
        if alpha.lower() not in {"ff", "f"}:
            found.append((f"#{base}", alpha, match.group()))
    return found


def hue_of(stop: str) -> float | None:
    """The hue of a colour stop in degrees, or None for anything that is not a colour."""
    token = stop.strip().lower()
    if token.startswith("#"):
        try:
            red, green, blue = parse_hex(token[:7] if len(token) >= 7 else token[:4])
        except UnslopperError:
            return None
        hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
        return hue * 360 if saturation > 0.15 and 0.05 < lightness < 0.95 else None
    if token.startswith("hsl"):
        number = re.search(r"[\d.]+", token)
        return float(number.group()) if number else None
    if token.startswith("rgb"):
        numbers = re.findall(r"[\d.]+", token)
        if len(numbers) >= 3:
            hue, lightness, saturation = colorsys.rgb_to_hls(*(min(float(part), 255) / 255 for part in numbers[:3]))
            return hue * 360 if saturation > 0.15 and 0.05 < lightness < 0.95 else None
    return NAMED_HUES.get(token)


def content_words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", text.lower()))


def quote(text: str) -> str:
    return f'"{clip(text)}"'


def clip(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    return collapsed if len(collapsed) <= QUOTE_LENGTH else collapsed[: QUOTE_LENGTH - 3] + "..."


def _distinct(evidence: list[Evidence]) -> list[Evidence]:
    seen: set[tuple[str, str]] = set()
    kept: list[Evidence] = []
    for item in evidence:
        if (item.location, item.detail) not in seen:
            seen.add((item.location, item.detail))
            kept.append(item)
    return kept


def _number(value: str) -> float | None:
    match = re.match(r"^\s*(-?\d*\.?\d+)", value)
    return float(match.group(1)) if match else None


# endregion
