"""Unslop: apply the twenty fixes to an HTML or CSS file, as a diff first and a write on request.

Purpose: turn a scan (and an audit, when one is given) into an edited copy of one file that keeps the
content, brand colours, links and form behaviour, and report the change as a unified diff.
Inputs: the path of an .html, .htm or .css file, whether to write, an optional AuditReport, and the
agent provider, model, reasoning effort or injected Intelligence every model-backed capability takes.
Outputs: UnslopResult with the plan, the diff, the scan before and after, and whether the file was written.
Side effects: one agent run in a temporary directory; the original is replaced only when `write` is true.
Dependencies: knowledge (the moves and fixes), the sibling scan, the Intelligence interface, python-liquid.
"""

import difflib
from pathlib import Path
import re
import shutil
import tempfile

from liquid import Environment, StrictUndefined
from pydantic import BaseModel, Field

from unslopper import knowledge
from unslopper.capabilities.audit import capability as audit_capability
from unslopper.intelligence.interface import Intelligence, select_intelligence
from unslopper.intelligence.schemas import AgentRequest, HostWorkspace
from unslopper.schemas import (
    DEFAULT_INTELLIGENCE_MODELS,
    AgentProvider,
    AuditReport,
    Move,
    PlannedChange,
    ReasoningEffort,
    ScanReport,
    UnslopperError,
    UnslopResult,
)

TEMPLATE = Path(__file__).with_name("unslop.md.liquid")
SUFFIXES = (".html", ".htm", ".css")
# The order the four moves are applied in; a pass that systematizes before it subtracts polishes what should go.
MOVE_ORDER: tuple[Move, ...] = ("Subtract", "Focus", "Systematize", "Respond")
# A full pass over a long page reads, edits and re-reads many times; a tight limit would cut good runs short.
TIMEOUT_SECONDS = 1800
UNTOUCHED = "The original file is untouched."

ATTRIBUTE = re.compile(r"""\b(?:href|src|action)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""", re.IGNORECASE)
# A <link> href names a stylesheet or font, which the fixes may legitimately replace; it is not a link a reader follows.
LINK_TAG = re.compile(r"<link\b[^>]*>", re.IGNORECASE)
ANCHOR = re.compile(r"<a\b", re.IGNORECASE)
FORM = re.compile(r"<form\b", re.IGNORECASE)


class UnslopAnswer(BaseModel):
    """What the agent submits once the file is edited: the plan it carried out and what to check by hand."""

    plan: list[PlannedChange] = Field(description="One entry per change made, in the order the moves were applied")
    notes: list[str] = Field(default_factory=list, description="Anything the caller should check by hand")


def unslop(
    path: Path,
    write: bool = False,
    audit_report: AuditReport | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
) -> UnslopResult:
    """Plan and propose the fixes as a diff; replace the file only when `write` is true.

    Args:
        path: An existing .html, .htm or .css file.
        write: Replace the file with the edited text; otherwise nothing on disk changes.
        audit_report: A model's reading of the same file, when one was made; it guides the plan.
        agent_provider: The agent provider to run through; the first installed when omitted.
        model: The model to run on; the agent provider's default when omitted.
        reasoning_effort: How hard the model thinks.
        intelligence: An Intelligence to run through instead of the shipped one.

    Returns:
        The plan, the unified diff, the scan before and after, and whether the file was written.

    Raises:
        UnslopperError: The path is not an HTML or CSS file, the agent failed, or the edited file dropped
            a link or a form. The original is never changed on any failure.
    """
    if path.suffix.lower() not in SUFFIXES or not path.is_file():
        raise UnslopperError(
            f"{path} is not an HTML or CSS file. Pass the path of an existing .html, .htm or .css file to fix."
        )
    intelligence, model = select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)
    intelligence.preflight()

    raw = path.read_text(encoding="utf-8", newline="")
    newline = "\r\n" if "\r\n" in raw else "\n"
    original = path.read_text(encoding="utf-8")
    before = audit_capability.scan(path=path)

    with tempfile.TemporaryDirectory(prefix="unslop-") as workspace:
        copy = Path(workspace) / path.name
        shutil.copyfile(path, copy)
        result = intelligence.run(
            AgentRequest(
                prompt=render_prompt(path.name, before, audit_report),
                model=model,
                workspace=HostWorkspace(path=Path(workspace)),
                writable=True,
                output_schema=UnslopAnswer.model_json_schema(),
                reasoning_effort=reasoning_effort,
                timeout_seconds=TIMEOUT_SECONDS,
            )
        )
        if result.error:
            raise UnslopperError(
                f"The unslop agent failed: {result.error} Check the agent provider's credentials and model, or "
                f"retry with --reasoning-effort high. {UNTOUCHED}"
            )
        if result.output is None:
            raise UnslopperError(f"The unslop agent gave no structured plan. Retry the run. {UNTOUCHED}")
        answer = UnslopAnswer.model_validate(result.output)
        edited = copy.read_text(encoding="utf-8")

    check_preserved(original, edited, path.suffix.lower() != ".css")
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            edited.splitlines(keepends=True),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
        )
    )
    after = audit_capability.scan(source=edited)
    if write:
        path.write_text(edited, encoding="utf-8", newline=newline)
    return UnslopResult(
        path=path, plan=answer.plan, diff=diff, before=before, after=after, written=write, notes=answer.notes
    )


def render_prompt(file_name: str, scan: ScanReport, audit_report: AuditReport | None) -> str:
    """The agent's brief: the file to edit, the four moves with their fixes, the reports, the rules and the answer."""
    moves = [
        {
            "name": move,
            "why": knowledge.MOVES[move],
            "fixes": [fix.model_dump() for fix in knowledge.FIXES if fix.move == move],
        }
        for move in MOVE_ORDER
    ]
    template = Environment(undefined=StrictUndefined).from_string(TEMPLATE.read_text(encoding="utf-8"))
    return template.render(
        file_name=file_name,
        moves=moves,
        scan_json=scan.model_dump_json(indent=2),
        audit_json=audit_report.model_dump_json(indent=2) if audit_report is not None else None,
    )


def check_preserved(original: str, edited: str, html: bool) -> None:
    """Raise when the edit emptied the file or, for HTML, dropped a link target, an anchor or a form."""
    if not edited.strip():
        raise UnslopperError(f"The unslop agent left the file empty. Retry the run. {UNTOUCHED}")
    if not html:
        return
    targets = {
        next(group for group in match.groups() if group is not None)
        for match in ATTRIBUTE.finditer(LINK_TAG.sub("", original))
    }
    missing = sorted(target for target in targets if target and target not in edited)
    if missing:
        raise UnslopperError(
            f"The edited file dropped these link targets: {', '.join(missing)}. Every href, src and action must "
            f"survive an unslop pass. Retry the run. {UNTOUCHED}"
        )
    for name, pattern in (("<a>", ANCHOR), ("<form>", FORM)):
        if len(pattern.findall(edited)) < len(pattern.findall(original)):
            raise UnslopperError(
                f"The edited file has fewer {name} elements than the original. Every link and form must survive "
                f"an unslop pass. Retry the run. {UNTOUCHED}"
            )
