"""The website builds from the repository's sources and passes its own checks."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name: str) -> ModuleType:
    """Import a script from scripts/ by path; the directory is not a package."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_site_builds_and_passes_its_checks(capsys: pytest.CaptureFixture[str]) -> None:
    build = load("build")
    check = load("check")
    output = ROOT / "_site"

    build.build(output)
    check.check(output)

    out = capsys.readouterr().out
    assert (output / "index.html").is_file()
    assert (output / "course.html").is_file()
    assert out.count("PASS:") == 5
    assert "Dogfood scan:" in out


def test_course_counts_match_knowledge() -> None:
    build = load("build")

    counts = build.course_counts(build.course_parts()["script"])
    knowledge = build.knowledge_counts()

    assert counts == {"terms": 20, "indicators": 20, "fixes": 20, "textures": 22, "prompts": 6}
    assert all(counts[key] == value for key, value in knowledge.items())
