"""Reference: the course material as data, for a caller that wants to read it rather than ask a model."""

from unslopper import knowledge
from unslopper.schemas import Fix, Indicator, PaletteStudy, ReferenceResult, Term, Texture, Topic, UnslopperError


def reference(topic: Topic, name: str | None = None) -> ReferenceResult:
    """Every entry of a topic, or the one entry whose name matches `name`, case-insensitively."""
    items = _items(topic)
    if name is None:
        return ReferenceResult(topic=topic, items=items)
    wanted = name.strip().lower()
    matches = [item for item in items if item.name.lower() == wanted or wanted in item.name.lower()]
    if not matches:
        known = ", ".join(item.name for item in items)
        raise UnslopperError(f"No {topic} entry matches '{name}'. The entries are: {known}.")
    return ReferenceResult(topic=topic, items=matches)


def _items(topic: Topic) -> list[Term | Indicator | Fix | Texture | PaletteStudy]:
    match topic:
        case "terms":
            return list(knowledge.TERMS)
        case "indicators":
            return list(knowledge.INDICATORS)
        case "fixes":
            return list(knowledge.FIXES)
        case "textures":
            return list(knowledge.TEXTURES)
        case "palettes":
            return list(knowledge.PALETTE_STUDIES)
