"""Route: pick the capability and the Agent Skill a job calls for, from a plain statement of the job."""

import re

from unslopper.schemas import RouteOption, RouteResult, UnslopperError

ROUTER_SKILL = "unslopper"

# Each route: the capability, the Agent Skill that teaches its method by hand, when it is the right
# choice, an example command, and the words in a job description that point at it.
ROUTES: tuple[tuple[RouteOption, str, tuple[str, ...]], ...] = (
    (
        RouteOption(
            capability="antislop",
            skill="design-antislopper",
            when="The whole pass on one file: audit, fix, direct, texture, polish, re-audit.",
        ),
        "unslopper antislop page.html",
        (
            "everything",
            "whole",
            "end to end",
            "end-to-end",
            "pipeline",
            "full pass",
            "all of it",
            "antislop",
            "just fix it",
            "make it good",
        ),
    ),
    (
        RouteOption(
            capability="unslop",
            skill="unslop-pass",
            when="You have the HTML or CSS and want the fixes applied as a reviewable diff.",
        ),
        "unslopper unslop page.html",
        (
            "fix",
            "remove",
            "clean up",
            "unslop",
            "de-slop",
            "deslop",
            "apply",
            "strip",
            "tidy",
            "less ai",
            "less generic",
            "make it look",
            "look designed",
            "look less",
            "improve",
        ),
    ),
    (
        RouteOption(
            capability="audit",
            skill="design-slop-audit",
            when="You need to say why a design reads as generated, with evidence and a score, including screenshots.",
        ),
        "unslopper audit page.html",
        (
            "audit",
            "review",
            "score",
            "is this slop",
            "slop",
            "looks ai",
            "looks generated",
            "generic",
            "tell",
            "why",
            "evidence",
            "screenshot",
            "image",
            "png",
            "jpg",
            "judge",
        ),
    ),
    (
        RouteOption(
            capability="scan",
            skill="design-slop-audit",
            when="The same question answered statically and for free, on HTML or CSS only.",
        ),
        "unslopper scan page.html",
        ("scan", "static", "free", "quick", "quickly", "no model", "offline", "lint"),
    ),
    (
        RouteOption(
            capability="direct",
            skill="palette-director",
            when="A brief needs a committed direction: scene, three colours with roles, type, hero, CSS tokens.",
        ),
        'unslopper direct "a mechanical watch brand lit like the aurora"',
        (
            "palette",
            "direction",
            "brand",
            "brief",
            "typography",
            "fonts",
            "font",
            "identity",
            "look and feel",
            "colours",
            "colors",
            "color scheme",
            "colour scheme",
            "theme",
            "tokens",
        ),
    ),
    (
        RouteOption(
            capability="contrast",
            skill="palette-director",
            when="Check one colour pair against WCAG.",
        ),
        'unslopper contrast "#E8EEF2" "#000412"',
        ("contrast", "wcag", "readable", "legible", "accessible", "accessibility", "ratio", "a11y"),
    ),
    (
        RouteOption(
            capability="texture",
            skill="texture-backgrounds",
            when="A background is flat or a purple gradient and should come from the subject's world.",
        ),
        'unslopper texture --subject "developer tools" --ground "#1C4E8A" --light "#F5F7FA" --signal "#FFB020"',
        ("background", "texture", "gradient", "flat", "grain", "noise", "pattern", "backdrop", "canvas"),
    ),
    (
        RouteOption(
            capability="tutor",
            skill="design-terms-tutor",
            when="Someone needs the vocabulary: teach a term, quiz on it, or name what a screenshot gets wrong.",
        ),
        'unslopper tutor teach --term "tabular numbers"',
        (
            "teach",
            "learn",
            "lesson",
            "explain",
            "what is",
            "what does",
            "quiz",
            "term",
            "terms",
            "vocabulary",
            "mean",
            "glossary",
            "tutor",
        ),
    ),
    (
        RouteOption(
            capability="reference",
            skill="unslopper",
            when="Hand an agent the course material as data: terms, indicators, fixes, textures, palettes.",
        ),
        "unslopper reference indicators",
        (
            "list",
            "catalog",
            "catalogue",
            "reference",
            "which indicators",
            "the fixes",
            "the terms",
            "the textures",
            "show me",
            "data",
        ),
    ),
)


def route(intent: str) -> RouteResult:
    """The capability whose words the intent uses most, with every route attached for the caller to override."""
    text = " ".join(intent.split()).lower()
    if not text:
        raise UnslopperError("Describe the job in a sentence, for instance 'make this landing page look less AI'.")
    scores = [(_score(text, words), index) for index, (_, _, words) in enumerate(ROUTES)]
    best_score, best = max(scores, key=lambda pair: (pair[0], -pair[1]))
    alternatives = [option for option, _, _ in ROUTES]
    if best_score == 0:
        return RouteResult(
            intent=intent,
            capability=None,
            skill=ROUTER_SKILL,
            command="unslopper --help",
            reason="Nothing in the job points at one capability. Read the table and pick, or start with scan.",
            alternatives=alternatives,
        )
    option, command, words = ROUTES[best]
    matched = [word for word in words if _matches(text, word)]
    return RouteResult(
        intent=intent,
        capability=option.capability,
        skill=option.skill,
        command=command,
        reason=f"The job says {', '.join(repr(word) for word in matched)}. {option.when}",
        alternatives=alternatives,
    )


def _score(text: str, words: tuple[str, ...]) -> int:
    # Longer phrases are more specific, so they count for more than single words.
    return sum(len(word.split()) for word in words if _matches(text, word))


def _matches(text: str, word: str) -> bool:
    return re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text) is not None
