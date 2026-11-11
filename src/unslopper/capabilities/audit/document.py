"""HTML and CSS read as a tree of elements and a list of style rules, with just enough style resolution for heuristics.

A real browser cascade is out of scope. Supported selectors use basic specificity and importance; conditional rules are not resolved. Custom
properties are substituted, and font-size and font-family inherit. That is enough to say "this small div is set
in monospace" with a line number a person can check.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from html.parser import HTMLParser
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unslopper.sources import Stylesheet

VOID_TAGS = frozenset(
    ["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"]
)
SKIPPED_TEXT_TAGS = frozenset(["script", "style", "template", "noscript", "svg"])
CODE_TAGS = frozenset(["code", "pre", "kbd", "samp", "tt", "var"])
HEADING_TAGS = frozenset(["h1", "h2", "h3", "h4", "h5", "h6"])
DEFAULT_FONT_PX = 16.0

COMMENT = re.compile(r"/\*.*?\*/", re.S)
BLOCK = re.compile(r"([^{}]+)\{([^{}]*)\}")
VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^()]*(?:\([^()]*\))?[^()]*))?\)")
LENGTH = re.compile(r"^(-?\d*\.?\d+)(px|em|rem|pt|%)?$")
FONT_SIZE_TOKEN = re.compile(
    r"(?<![\w-])(\d*\.?\d+(?:px|em|rem|pt|%|vw|vh|ch)|x{0,2}-?(?:small|large)r?|medium)(?:/[\w.%-]+)?\s+(.+)$"
)
SELECTOR_SPLIT = re.compile(r",(?![^(]*\))")
PSEUDO = re.compile(r"::?[\w-]+(?:\([^()]*\))?")
COMBINATOR = re.compile(r"\s*([>+~])\s*|\s+")
FONT_URL = re.compile(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)|@import\s+['"]([^'"]+)['"]""")


# Identity equality: a field-wise comparison would recurse through parent and children.
@dataclass(eq=False)
class Element:
    """One HTML element: its tag, attributes, children and the line it opened on."""

    tag: str
    attrs: dict[str, str]
    line: int
    parent: Element | None = None
    children: list[Element | str] = field(default_factory=list)

    @property
    def classes(self) -> list[str]:
        return self.attrs.get("class", "").split()

    @property
    def id(self) -> str | None:
        return self.attrs.get("id")

    def elements(self) -> list[Element]:
        return [child for child in self.children if isinstance(child, Element)]

    def own_text(self) -> str:
        return " ".join(child for child in self.children if isinstance(child, str)).strip()

    def text(self) -> str:
        """All descendant text, skipping scripts, styles and inline SVG."""
        parts: list[str] = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in SKIPPED_TEXT_TAGS:
                parts.append(child.text())
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def ancestors(self) -> Iterator[Element]:
        node = self.parent
        while node is not None:
            yield node
            node = node.parent

    def walk(self) -> Iterator[Element]:
        """This element and every descendant, in document order."""
        yield self
        for child in self.elements():
            yield from child.walk()

    def next_element(self) -> Element | None:
        """The next sibling element, when the text between is only whitespace."""
        if self.parent is None:
            return None
        siblings = self.parent.children
        for index in range(siblings.index(self) + 1, len(siblings)):
            sibling = siblings[index]
            if isinstance(sibling, Element):
                return sibling
            if sibling.strip():
                return None
        return None

    def inside(self, tags: frozenset[str]) -> bool:
        return self.tag in tags or any(ancestor.tag in tags for ancestor in self.ancestors())

    def describe(self) -> str:
        """`<div class="eb" id="x"> (line 12)`: enough for a person to find it."""
        parts = [self.tag]
        if self.id:
            parts.append(f'id="{self.id}"')
        if self.classes:
            parts.append(f'class="{" ".join(self.classes)}"')
        return f"<{' '.join(parts)}> (line {self.line})"


@dataclass(frozen=True)
class Rule:
    """One CSS rule: a selector, its declarations with custom properties substituted, and its line."""

    selector: str
    declarations: dict[str, str]
    line: int

    important: frozenset[str] = frozenset()
    conditional: bool = False
    label: str | None = None

    def where(self) -> str:
        prefix = f"{self.label}: " if self.label else ""
        return f"{prefix}{self.selector} (line {self.line})"


@dataclass(frozen=True)
class Compound:
    """One compound selector: an optional tag, an optional id and the classes it needs."""

    tag: str | None
    id: str | None
    classes: frozenset[str]

    def matches(self, element: Element) -> bool:
        if self.tag is not None and self.tag != element.tag:
            return False
        if self.id is not None and self.id != element.id:
            return False
        return self.classes <= set(element.classes)


@dataclass(frozen=True)
class Declared:
    """One place declarations come from, a rule or a style attribute, described the same way for the checks."""

    where: str
    selector: str
    declarations: dict[str, str]
    code: bool

    def px(self, name: str) -> float | None:
        value = self.declarations.get(name)
        return None if value is None else length_px(value)


class Document:
    """What a scan reads: the element tree (None for a stylesheet), the rules, the comments and the font URLs."""

    def __init__(self, root: Element | None, rules: list[Rule], comments: list[str], font_urls: list[str]) -> None:
        self.root = root
        self.rules = rules
        self.comments = comments
        self.font_urls = font_urls
        self._styles: dict[int, dict[str, str]] = {}
        self._elements: list[Element] | None = None
        self._declared: list[Declared] | None = None
        self._matches: dict[int, list[Element]] = {}
        self.warnings: list[str] = []
        if any(rule.conditional for rule in rules):
            self.warnings.append("Conditional and nested CSS rules are not resolved against a browser environment.")
        if root is not None and any(
            not _supported_selector(single) for rule in rules for single in SELECTOR_SPLIT.split(rule.selector)
        ):
            self.warnings.append(
                "Unsupported CSS selectors are excluded from HTML style resolution; this is not a browser cascade."
            )
        if any("var(" in value for rule in rules for value in rule.declarations.values()):
            self.warnings.append("Some CSS custom properties could not be resolved.")

    def elements(self) -> list[Element]:
        if self._elements is None:
            self._elements = (
                [element for element in self.root.walk() if element is not self.root and not self.hidden(element)]
                if self.root is not None
                else []
            )
        return self._elements

    def headings(self) -> list[Element]:
        return [element for element in self.elements() if element.tag in HEADING_TAGS]

    def hidden(self, element: Element) -> bool:
        """Only explicit hidden markup and supported display:none declarations are excluded."""
        return any(
            "hidden" in node.attrs
            or self.style(node).get("display", "").lower() == "none"
            or node.tag in {"template", "noscript"}
            for node in (element, *element.ancestors())
        )

    def text(self, element: Element) -> str:
        """Descendant text without known hidden subtrees."""
        if self.hidden(element):
            return ""
        parts = [
            child if isinstance(child, str) else self.text(child)
            for child in element.children
            if isinstance(child, str) or child.tag not in SKIPPED_TEXT_TAGS
        ]
        return re.sub(r"\s+", " ", "".join(parts)).strip()

    def declared(self) -> list[Declared]:
        """Stylesheet candidates, or declarations that survive on a visible HTML element."""
        if self._declared is not None:
            return self._declared
        sources: list[Declared] = []
        elements = self.elements()
        visible = set(elements)
        for rule in self.rules:
            declarations = rule.declarations
            if self.root is not None:
                matches = [element for element in self._matches.get(id(rule), []) if element in visible]
                declarations = {
                    name: value
                    for name, value in declarations.items()
                    if any(self.style(element).get(name) == value for element in matches)
                }
            if declarations:
                sources.append(Declared(rule.where(), rule.selector, declarations, targets_code(rule.selector)))
        for element in elements:
            if "style" in element.attrs:
                selector = element.tag + "".join(f".{name}" for name in element.classes)
                declarations = substitute_all(parse_declarations(element.attrs["style"]), self.variables())
                declarations = {
                    name: value for name, value in declarations.items() if self.style(element).get(name) == value
                }
                if declarations:
                    sources.append(Declared(element.describe(), selector, declarations, element.inside(CODE_TAGS)))
        self._declared = sources
        return sources

    def variables(self) -> dict[str, str]:
        found: dict[str, str] = {}
        for rule in self.rules:
            if rule.conditional:
                continue
            for name, value in rule.declarations.items():
                if name.startswith("--"):
                    found.setdefault(name, value)
        return found

    def style(self, element: Element) -> dict[str, str]:
        """Resolve supported selectors by importance, specificity, then source order."""
        cached = self._styles.get(id(element))
        if cached is not None:
            return cached
        resolved: dict[str, str] = {}
        priorities: dict[str, tuple[int, int, int, int, int, int]] = {}
        for order, rule in enumerate(self.rules):
            if rule.conditional:
                continue
            matching = [single for single in SELECTOR_SPLIT.split(rule.selector) if _matches_single(single, element)]
            if not matching:
                continue
            self._matches.setdefault(id(rule), []).append(element)
            specificity = max(_specificity(single) for single in matching)
            for name, value in rule.declarations.items():
                priority = (int(name in rule.important), 0, *specificity, order)
                if priority >= priorities.get(name, (-1, 0, 0, 0, 0, 0)):
                    resolved[name] = value
                    priorities[name] = priority
        if "style" in element.attrs:
            declarations, important = _declarations(element.attrs["style"])
            for name, value in substitute_all(declarations, self.variables()).items():
                priority = (int(name in important), 1, 0, 0, 0, 0)
                if priority >= priorities.get(name, (-1, 0, 0, 0, 0, 0)):
                    resolved[name] = value
        self._styles[id(element)] = resolved
        return resolved

    def font_size(self, element: Element) -> float | None:
        """The element's font size in px when the cascade states one, inheriting through its ancestors."""
        parent_size = self.font_size(element.parent) if element.parent is not None else None
        own = self.style(element).get("font-size")
        if own is None:
            return parent_size
        return length_px(own, parent_size or DEFAULT_FONT_PX)

    def font_family(self, element: Element) -> str | None:
        """The element's font family, inherited."""
        for node in (element, *element.ancestors()):
            family = self.style(node).get("font-family")
            if family is not None:
                return family
        return None


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Element("document", {}, 1)
        self.stack = [self.root]
        self.styles: list[tuple[str, int]] = []
        self.style_order: list[tuple[str | None, int, int, bool]] = []
        self.comments: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        element = Element(tag, {name: value or "" for name, value in attrs}, self.getpos()[0], self.stack[-1])
        self.stack[-1].children.append(element)
        if tag == "link" and "stylesheet" in element.attrs.get("rel", "").lower().split():
            self.style_order.append(
                (None, *self.getpos(), element.attrs.get("media", "").strip().lower() not in {"", "all", "screen"})
            )
        if tag not in VOID_TAGS:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        current = self.stack[-1]
        if current.tag == "style":
            self.styles.append((data, self.getpos()[0]))
            self.style_order.append(
                (data, *self.getpos(), current.attrs.get("media", "").strip().lower() not in {"", "all", "screen"})
            )
        current.children.append(data)

    def handle_comment(self, data: str) -> None:
        self.comments.append(data)


def parse_html(text: str, stylesheets: tuple[Stylesheet, ...] = ()) -> Document:
    """The page as a document: its tree, every inline <style> block parsed, comments and font stylesheet links."""
    builder = _TreeBuilder()
    builder.feed(text)
    builder.close()
    pending = list(stylesheets)
    blocks: list[tuple[str, int, bool, str | None]] = []
    for block, line, column, conditional in builder.style_order:
        if block is not None:
            blocks.append((block, line, conditional, None))
        else:
            sheet = next((sheet for sheet in pending if sheet.line == line and sheet.column == column), None)
            if sheet is not None:
                pending.remove(sheet)
                blocks.append((sheet.text, 1, conditional, sheet.label))
    css = "\n".join(block for block, _, _, _ in blocks)
    comments = list(builder.comments)
    comments.extend(match.group() for match in COMMENT.finditer(css))
    rules: list[Rule] = []
    variables: dict[str, str] = {}
    for block, line, conditional, label in blocks:
        rules.extend(
            Rule(rule.selector, rule.declarations, rule.line, rule.important, conditional or rule.conditional, label)
            for rule in parse_rules(block, line, {} if conditional else variables)
        )
    rules = [
        Rule(
            rule.selector,
            substitute_all(rule.declarations, variables),
            rule.line,
            rule.important,
            rule.conditional,
            rule.label,
        )
        for rule in rules
    ]
    font_urls = [
        element.attrs.get("href", "")
        for element in builder.root.walk()
        if element.tag == "link" and "fonts.googleapis.com/css" in element.attrs.get("href", "")
    ]
    font_urls.extend(url for url in _import_urls(css) if "fonts.googleapis.com" in url)
    return Document(builder.root, rules, comments, font_urls)


def parse_css(text: str) -> Document:
    """A stylesheet as a document with no element tree."""
    variables: dict[str, str] = {}
    rules = parse_rules(text, 1, variables)
    rules = [
        Rule(rule.selector, substitute_all(rule.declarations, variables), rule.line, rule.important, rule.conditional)
        for rule in rules
    ]
    comments = [match.group() for match in COMMENT.finditer(text)]
    font_urls = [url for url in _import_urls(text) if "fonts.googleapis.com" in url]
    return Document(None, rules, comments, font_urls)


def parse_rules(css: str, first_line: int, variables: dict[str, str]) -> list[Rule]:
    """Every `selector { declarations }` block, innermost ones inside at-rules included, collecting custom properties."""
    # Comments become spaces of the same shape so line numbers stay true.
    stripped = COMMENT.sub(lambda match: re.sub(r"[^\n]", " ", match.group()), css)
    rules: list[Rule] = []
    for match in BLOCK.finditer(stripped):
        selector = match.group(1).strip().rsplit("}", 1)[-1].strip()
        if not selector or selector.startswith("@"):
            continue
        declarations, important = _declarations(match.group(2))
        conditional = stripped[: match.start()].count("{") > stripped[: match.start()].count("}")
        for name, value in declarations.items():
            # The first definition wins, so a dark-theme override later in the sheet does not replace the base.
            if name.startswith("--") and not conditional:
                variables.setdefault(name, value)
        line = first_line + stripped.count("\n", 0, match.start(1) + match.group(1).index(selector))
        rules.append(Rule(selector, declarations, line, important, conditional))
    return rules


def parse_declarations(text: str) -> dict[str, str]:
    """Property values, with font shorthand expanded and importance preserved during parsing."""
    return _declarations(text)[0]


def _declarations(text: str) -> tuple[dict[str, str], frozenset[str]]:
    declarations: dict[str, str] = {}
    important: set[str] = set()
    for part in re.split(r";(?![^(]*\))", text):
        name, separator, raw_value = part.partition(":")
        if not separator:
            continue
        name = name.strip().lower()
        is_important = bool(re.search(r"!\s*important\s*$", raw_value, re.I))
        value = re.sub(r"\s*!\s*important\s*$", "", raw_value.strip(), flags=re.I)
        if not name or not value:
            continue
        expanded = {name: value}
        if name == "font":
            size, family = split_font_shorthand(value)
            if size is not None:
                expanded["font-size"] = size
            if family is not None:
                expanded["font-family"] = family
        for prop, val in expanded.items():
            if prop in important and not is_important:
                continue
            declarations[prop] = val
            if is_important:
                important.add(prop)
    return declarations, frozenset(important)


def split_font_shorthand(value: str) -> tuple[str | None, str | None]:
    """The size and the family out of `font: 600 11px/1.4 var(--display)`."""
    match = FONT_SIZE_TOKEN.search(value)
    if match is None:
        return None, None
    return match.group(1), match.group(2).strip()


def substitute_all(declarations: dict[str, str], variables: dict[str, str]) -> dict[str, str]:
    return {name: substitute(value, variables) for name, value in declarations.items()}


def substitute(value: str, variables: dict[str, str], depth: int = 0) -> str:
    """`var(--x, fallback)` replaced by its definition, recursively, leaving unknown ones to their fallback."""
    if depth > 8 or "var(" not in value:
        return value

    def replace(match: re.Match[str]) -> str:
        name, fallback = match.group(1), match.group(2)
        if name in variables:
            return variables[name]
        return fallback.strip() if fallback else match.group()

    return substitute(VAR.sub(replace, value), variables, depth + 1)


def length_px(value: str, reference: float = DEFAULT_FONT_PX) -> float | None:
    """A CSS length in px, with em and rem taken against `reference`; None for anything not that simple."""
    match = LENGTH.match(value.strip().lower())
    if match is None:
        return None
    number = float(match.group(1))
    match match.group(2):
        case "px" | None:
            return number
        case "em" | "rem":
            return number * reference
        case "pt":
            return number * 4 / 3
        case "%":
            return number / 100 * reference
    return None


def selector_matches(selector: str, element: Element) -> bool:
    """Whether any selector in the comma list matches, on tag, id, class and the descendant and child combinators."""
    return any(_matches_single(single, element) for single in SELECTOR_SPLIT.split(selector))


def last_compounds(selector: str) -> list[str]:
    """The rightmost compound of each selector in the comma list, pseudo-classes removed."""
    compounds: list[str] = []
    for single in SELECTOR_SPLIT.split(selector):
        parts = [part for part in COMBINATOR.split(PSEUDO.sub("", single).strip()) if part and part not in "+>~"]
        if parts:
            compounds.append(parts[-1])
    return compounds


def targets_code(selector: str) -> bool:
    """Whether every selector in the list ends in a code-like element or class."""
    compounds = last_compounds(selector)
    return bool(compounds) and all(_compound_is_code(compound) for compound in compounds)


def _compound_is_code(compound: str) -> bool:
    parsed = _parse_compound(compound)
    if parsed is None:
        return False
    if parsed.tag in CODE_TAGS:
        return True
    return any(re.search(r"code|pre|terminal|console|shell|snippet", name) for name in parsed.classes)


@lru_cache(maxsize=8192)
def _supported_selector(selector: str) -> bool:
    compound = r"(?:(?:[a-zA-Z_][\w-]*|\*)(?:[.#][\w-]+)*|(?:[.#][\w-]+)+)"
    return (
        bool(selector.strip())
        and re.fullmatch(rf"{compound}(?:\s*>\s*{compound}|\s+{compound})*", selector.strip()) is not None
    )


def _matches_single(selector: str, element: Element) -> bool:
    compounds, combinators = _selector_parts(selector)
    return bool(compounds) and _match_from_right(element, compounds, combinators, len(compounds) - 1)


@lru_cache(maxsize=8192)
def _selector_parts(selector: str) -> tuple[tuple[Compound, ...], tuple[str, ...]]:
    cleaned = selector.strip()
    if not _supported_selector(cleaned):
        return (), ()
    compounds: list[Compound] = []
    combinators: list[str] = []
    for token in COMBINATOR.split(cleaned):
        if token == ">":
            if not combinators:
                return (), ()
            combinators[-1] = token
            continue
        if not token:
            continue
        parsed = _parse_compound(token)
        if parsed is None:
            return (), ()
        compounds.append(parsed)
        combinators.append(" ")
    return tuple(compounds), tuple(combinators)


def _match_from_right(
    element: Element, compounds: tuple[Compound, ...], combinators: tuple[str, ...], index: int
) -> bool:
    if not compounds[index].matches(element):
        return False
    if index == 0:
        return True
    match combinators[index - 1]:
        case ">":
            return element.parent is not None and _match_from_right(element.parent, compounds, combinators, index - 1)
        case " ":
            return any(_match_from_right(node, compounds, combinators, index - 1) for node in element.ancestors())
    # Sibling combinators are not tracked; the right-hand side alone decides, which errs toward matching.
    return True


def _parse_compound(token: str) -> Compound | None:
    if re.fullmatch(r"(?:[a-zA-Z_][\w-]*|\*)?(?:[.#][\w-]+)*", token) is None:
        return None
    tag: str | None = None
    identifier: str | None = None
    classes: set[str] = set()
    for match in re.finditer(r"([.#]?)([\w-]+)|(\*)", token):
        prefix, name, star = match.groups()
        if star:
            continue
        if prefix == ".":
            classes.add(name)
        elif prefix == "#":
            identifier = name
        else:
            tag = name.lower()
    if tag is None and identifier is None and not classes and token.strip() != "*":
        return None
    return Compound(tag, identifier, frozenset(classes))


@lru_cache(maxsize=8192)
def _specificity(selector: str) -> tuple[int, int, int]:
    return (
        selector.count("#"),
        selector.count("."),
        len(re.findall(r"(?:^|[ >])([a-zA-Z_][\w-]*)", selector)),
    )


def _import_urls(css: str) -> list[str]:
    return [first or second for first, second in FONT_URL.findall(css)]
