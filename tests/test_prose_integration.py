"""Exercise the explicit prose switch and the shared policy across existing entry points."""

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from unslopper import lib
from unslopper.capabilities.antislop.capability import render
from unslopper.capabilities.audit.capability import render_prompt as audit_prompt
from unslopper.capabilities.unslop.capability import render_prompt as edit_prompt
from unslopper.cli import app
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.prose import policy_text
from unslopper.schemas import UnslopperError
from unslopper.sources import load_source


def test_cli_prose_scan_is_offline_and_has_no_authorship_score(tmp_path: Path) -> None:
    draft = tmp_path / "draft.md"
    draft.write_text("It is important to note that most teams may need another review [1].", encoding="utf-8")
    runner = CliRunner()
    for args in ([str(draft), "--prose"], ["--prose", "--source", draft.read_text()]):
        result = runner.invoke(app, ["scan", *args])
        assert result.exit_code == 0, result.output
        report = json.loads(result.stdout)
        assert report["authorship"] == "not_assessed"
        assert "score" not in report
        assert "probability" not in report
        assert report["findings"]


@pytest.mark.parametrize("command", ["scan", "audit", "unslop"])
def test_all_prose_entry_points_explain_the_switch(command: str) -> None:
    result = CliRunner().invoke(app, [command, "--help"])
    assert result.exit_code == 0
    assert "--prose" in result.stdout
    assert "prose-quality.md" in result.stdout
    assert "THIRD_PARTY_NOTICES.md" in result.stdout


@pytest.mark.parametrize(("command", "write"), [("audit", False), ("unslop", False), ("unslop", True)])
def test_cli_model_paths_forward_options_and_respect_requested_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str, write: bool
) -> None:
    from unslopper.capabilities.prose import capability

    original = "It is important to note that most teams may need another review [1].\n"
    proposed = "Most teams may need another review [1].\n"
    draft = tmp_path / "draft.md"
    draft.write_text(original, encoding="utf-8")
    requests: list[AgentRequest] = []
    selections: list[tuple[Any, ...]] = []

    class FakeIntelligence:
        implementation = "fake"

        def preflight(self) -> None:
            pass

        def run(self, request: AgentRequest) -> AgentResult:
            requests.append(request)
            output = (
                {"summary": "Review in context.", "findings": []} if command == "audit" else {"proposed_text": proposed}
            )
            return AgentResult(output=output)

    def select(*args: Any) -> tuple[FakeIntelligence, str]:
        selections.append(args)
        return FakeIntelligence(), "test/model"

    monkeypatch.setattr(capability, "select_intelligence", select)
    args = [
        command,
        str(draft),
        "--prose",
        "--agent-provider",
        "claude",
        "--model",
        "test/model",
        "--reasoning-effort",
        "high",
    ]
    result = CliRunner().invoke(app, [*args, *(["--write"] if write else [])])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["authorship"] == "not_assessed"
    assert selections[0][1:3] == ("claude", "test/model")
    assert requests[0].reasoning_effort == "high"
    assert requests[0].workspace is None
    assert requests[0].writable is False
    assert draft.read_text(encoding="utf-8") == (proposed if write else original)
    if command == "unslop":
        assert report["written"] is write
        assert report["diff"]


def test_prose_mode_rejects_url_and_image_before_selecting_a_provider() -> None:
    with pytest.raises(UnslopperError, match="not a URL"):
        lib.scan(url="https://example.invalid", prose=True)
    with pytest.raises(UnslopperError, match="not a URL or image"):
        lib.audit(image=Path("missing.png"), prose=True)
    with pytest.raises(UnslopperError, match="not a URL or image"):
        lib.audit(url="https://example.invalid", prose=True)


@pytest.mark.parametrize(
    ("intent", "command"),
    [("scan my prose offline", "scan"), ("review this writing", "audit"), ("rewrite this essay", "unslop")],
)
def test_router_selects_existing_commands_with_prose(intent: str, command: str) -> None:
    route = lib.route(intent)
    assert route.capability == command
    assert route.command == f"unslopper {command} draft.md --prose"
    assert "do not establish authorship" in route.reason


def test_design_audit_edit_and_polish_share_one_prose_policy() -> None:
    loaded = load_source(source="<p>Most teams may need another review [1].</p>")
    scan = lib.scan(source=loaded.text)
    policy = policy_text()
    for prompt in (
        audit_prompt(loaded, scan),
        edit_prompt("page.html", scan, None),
        render("polish.md.liquid", file_name="page.html"),
    ):
        assert policy in prompt
        assert "No buzzwords:" not in prompt
        assert "authorship" in prompt
        assert '"most teams"' in prompt
