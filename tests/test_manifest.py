from importlib.metadata import version
import json
from pathlib import Path
import tomllib

from typer.testing import CliRunner
import yaml

from unslopper.cli import app
from unslopper.core.manifest import MANIFEST_PATH
from unslopper.lib import load_manifest

DISTRIBUTION_ROOT = Path(__file__).parents[1]


def test_manifest_matches_the_descriptor_and_package() -> None:
    manifest = load_manifest()
    descriptor = json.loads((DISTRIBUTION_ROOT / "smart-tool.json").read_text(encoding="utf-8"))

    assert DISTRIBUTION_ROOT / descriptor["manifest"] == MANIFEST_PATH
    assert manifest.name == descriptor["cli_argv"][0]
    assert manifest.version == version("unslopper")


def test_release_version_matches_package_lock_cli_and_every_skill() -> None:
    expected = load_manifest().version
    project = tomllib.loads((DISTRIBUTION_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    lock = tomllib.loads((DISTRIBUTION_ROOT / "uv.lock").read_text(encoding="utf-8"))

    assert project["project"]["version"] == expected
    assert next(package for package in lock["package"] if package["name"] == "unslopper")["version"] == expected
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"unslopper {expected}"
    skills = list((DISTRIBUTION_ROOT / "skills").glob("*/SKILL.md"))
    assert skills
    for skill in skills:
        metadata = yaml.safe_load(skill.read_text(encoding="utf-8").split("---", 2)[1])
        assert metadata["metadata"]["version"] == expected, skill
