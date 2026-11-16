"""Role routing, local context and operational scope controls without a live model."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError
import pytest
from typer.testing import CliRunner

from unslopper import lib
from unslopper.cli import app
from unslopper.intelligence.schemas import AgentRequest, AgentResult
from unslopper.roles import load_review_context, role_contract_text, validate_review_comments
from unslopper.schemas import ReviewComment, ReviewContext, UnslopperError


class FakeIntelligence:
    implementation = "fake"

    def __init__(self, output: dict[str, Any]) -> None:
        self.output = output
        self.requests: list[AgentRequest] = []

    def preflight(self) -> None:
        pass

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        return AgentResult(output=self.output)


@pytest.mark.parametrize(
    ("intent", "roles", "command"),
    [
        ("editor review of this memo", ["editor"], "audit"),
        ("research the claims and deductive logic", ["research-partner"], "audit"),
        ("designer audit this screenshot", ["designer"], "audit"),
        ("editor fix this page navigation", ["editor", "designer"], "unslop"),
        ("edit this HTML page", ["designer"], "unslop"),
    ],
)
def test_roles_route_to_existing_commands_with_artifact_boundaries(intent: str, roles: list[str], command: str) -> None:
    result = lib.route(intent)
    assert result.roles == roles
    assert result.capability == command
    if "research-partner" in roles:
        assert "--prose --context" in result.command
    elif "designer" in roles:
        assert "--prose" not in result.command


def test_combined_and_offline_routes_do_not_invent_evidence_or_force_a_model() -> None:
    combined = lib.route("editor research this memo and designer review of the page")
    assert set(combined.roles) == {"editor", "research-partner", "designer"}
    assert "explicit scope" in combined.reason
    offline = lib.route("scan prose claims offline")
    assert offline.capability == "scan"
    assert "editorial candidates only" in offline.reason
    assert "--context" not in offline.command


def test_combined_roles_need_scope_and_context_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError, match="explicit scope"):
        ReviewContext(roles=["editor", "research-partner"])
    with pytest.raises(ValidationError):
        ReviewContext.model_validate({"roles": ["editor"], "invent_sources": True})


def test_cli_context_reaches_existing_prose_audit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from unslopper.capabilities.prose import capability

    context = tmp_path / "review.json"
    context.write_text(
        json.dumps(
            {"roles": ["editor"], "purpose": "Clarify the update", "audience": "Operators", "voice": "Keep the dialect"}
        ),
        encoding="utf-8",
    )
    fake = FakeIntelligence({"summary": "Keep the intentional voice.", "findings": []})
    monkeypatch.setattr(capability, "select_intelligence", lambda *args: (fake, "test/model"))
    result = CliRunner().invoke(
        app, ["audit", "--prose", "--source", "We ain't changing the limits.", "--context", str(context)]
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["author_comments"] == []
    prompt = fake.requests[0].prompt
    assert prompt.count(role_contract_text()) == 1
    assert "Clarify the update" in prompt
    assert "Operators" in prompt
    assert "Keep the dialect" in prompt
    assert fake.requests[0].workspace is None


def test_context_loader_names_invalid_input_and_design_boundary_before_provider(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text("not JSON", encoding="utf-8")
    with pytest.raises(UnslopperError, match="review context"):
        load_review_context(path)
    with pytest.raises(UnslopperError, match="scoped to prose"):
        lib.audit(source="<p>Existing design.</p>", context=ReviewContext())


def test_research_only_edit_cannot_silently_rewrite_without_comments(tmp_path: Path) -> None:
    original = "Every approved release passed the tests. Release R passed the tests. Therefore, release R is approved."
    path = tmp_path / "argument.md"
    path.write_text(original, encoding="utf-8")
    fake = FakeIntelligence(
        {"proposed_text": original.replace("release R is approved.", "release R passed the tests.")}
    )
    with pytest.raises(UnslopperError, match="Research-only"):
        lib.unslop(
            path,
            write=True,
            prose=True,
            context=ReviewContext(roles=["research-partner"], scope="Review reasoning only"),
            intelligence=fake,
        )
    assert path.read_text(encoding="utf-8") == original


def test_reasoning_criticism_requires_an_argument_trace() -> None:
    passage = "The next launch may need review."
    comment = ReviewComment(
        start=0,
        end=len(passage),
        passage=passage,
        kind="inference",
        issue="weak_induction",
        explanation="The sample may not apply.",
        action="ask_author",
        question_or_repair="What makes the next launch comparable?",
    )
    with pytest.raises(UnslopperError, match="charitable"):
        validate_review_comments(passage, [comment], ReviewContext(roles=["research-partner"]))


def test_packaged_router_contract_matches_the_canonical_contract() -> None:
    root = Path(__file__).parents[1]
    assert (root / "skills/unslopper/references/role-contract.md").read_text(
        encoding="utf-8"
    ).strip() == role_contract_text()
