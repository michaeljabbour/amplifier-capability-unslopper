"""Scoped prose candidates, contextual review, and fidelity-checked proposed edits."""

import difflib
from pathlib import Path
import re

from liquid import Environment, StrictUndefined
from pydantic import BaseModel, Field, ValidationError

from unslopper.intelligence.interface import Intelligence, select_intelligence
from unslopper.intelligence.schemas import AgentRequest
from unslopper.prose import MAX_PROSE_CHARS, check_fidelity, policy_text, scoped_text
from unslopper.roles import review_context_text, role_contract_text, validate_review_comments
from unslopper.schemas import (
    DEFAULT_INTELLIGENCE_MODELS,
    AgentProvider,
    ProseAuditReport,
    ProseEditResult,
    ProseFinding,
    ProseScanReport,
    ReasoningEffort,
    ReviewComment,
    ReviewContext,
    UnslopperError,
)

HERE = Path(__file__).parents[0]
TIMEOUT_SECONDS = 600
SCOPE_WARNING = (
    "Conservative English prose heuristics: code, quotations, blockquotes, link targets, citations and "
    "reference sections are excluded. Markdown parsing is partial; no absence of findings proves quality. "
    "Genre, dialect and intent require human judgment. Authorship is not assessed."
)
FIDELITY_WARNING = (
    "Mechanical fidelity checks preserve protected spans, numeric details and calibration/negation tokens; "
    "they do not verify meaning, names, attribution, factual truth or author voice. Review the diff."
)
REVIEW_WARNING = (
    "This scoped editorial/source/argument review is not comprehensive fact checking. "
    "Source support, applicability and logical validity remain model judgments; exact quotation checks do not prove them. "
    "Author-facing comments are returned to the caller, not sent to an author."
)

RULES: tuple[tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "duplicate-word",
        re.compile(r"\b(the)\s+\1\b", re.I),
        "objective",
        "The same determiner occurs twice consecutively. Check for an accidental duplication.",
    ),
    (
        "empty-announcement",
        re.compile(
            r"(?im)(?:^|(?<=[.!?])\s+)(?:It is (?:important|worthwhile|essential|crucial) to note that|It's worth noting that|It is worth noting that|In this (?:article|post|section),? we will (?:explore|discuss))\b"
        ),
        "review",
        "Check whether this announcement can be removed without losing a qualification or useful navigation.",
    ),
    (
        "performative-emphasis",
        re.compile(r"(?im)(?:^|(?<=[.!?])\s+)(?:Make no mistake|Here's the thing|The truth is)[,:]?"),
        "review",
        "Check whether the emphasis adds meaning or belongs to the author's deliberate voice.",
    ),
    (
        "generic-importance",
        re.compile(
            r"(?im)(?:^|(?<=[.!?])\s+)In (?:today's|the) (?:rapidly evolving|ever-changing|modern) (?:world|landscape)\b[^.!?\n]*[,;:]"
        ),
        "review",
        "Check whether this broad scene-setting supplies context the reader needs rather than generic importance.",
    ),
)
CONTRAST_SCAFFOLD = re.compile(r"(?im)^\s*(?:It(?:'s| is)|This is) not\b[^.!?\n]{1,160}(?:[.;]|,?\s+but\b)")
RULE_IDS = frozenset(
    {rule[0] for rule in RULES}
    | {"repeated-scaffolding", "unsupported-generality", "unclear-accountability", "redundancy"}
)


class ProseAuditAnswer(BaseModel):
    """Model judgments, including deliberate choices and cases lacking enough context."""

    summary: str
    findings: list[ProseFinding]
    warnings: list[str] = Field(default_factory=list)
    author_comments: list[ReviewComment] = Field(default_factory=list)


class ProseEditAnswer(BaseModel):
    """The complete proposed source and a concise account of the justified changes."""

    proposed_text: str
    notes: list[str] = Field(default_factory=list)
    author_comments: list[ReviewComment] = Field(default_factory=list)


def _load(source: str | None, path: Path | None) -> tuple[str, str]:
    if (source is None) == (path is None):
        raise UnslopperError("Give exactly one of a prose file path or inline source text.")
    if path is not None:
        if not path.is_file() or path.suffix.lower() not in {".txt", ".md", ".markdown"}:
            raise UnslopperError(f"{path} is not a prose file. Pass an existing .txt, .md or .markdown file.")
        try:
            text, label = path.read_text(encoding="utf-8"), str(path)
        except (OSError, UnicodeError) as error:
            raise UnslopperError(f"Could not read prose file {path}: {error}. Pass a UTF-8 text file.") from None
    else:
        text, label = source or "", "inline"
    if not text.strip():
        raise UnslopperError("The prose source is empty. Pass text to review.")
    if len(text) > MAX_PROSE_CHARS:
        raise UnslopperError(
            f"The prose source exceeds {MAX_PROSE_CHARS} characters. Split it into smaller sections; no text was reviewed or edited."
        )
    return text, label


def _finding(text: str, match: re.Match[str], rule_id: str, category: str, rationale: str) -> ProseFinding:
    start = match.start() + len(match.group()) - len(match.group().lstrip())
    return ProseFinding(
        rule_id=rule_id,
        category="objective" if category == "objective" else "review",
        start=start,
        end=match.end(),
        line=text.count("\n", 0, start) + 1,
        evidence=text[start : match.end()],
        rationale=rationale,
        disposition="review",
    )


def _scan(text: str, label: str, path: Path | None) -> ProseScanReport:
    scoped, spans = scoped_text(text)
    findings = [
        _finding(text, match, rule_id, category, rationale)
        for rule_id, pattern, category, rationale in RULES
        for match in pattern.finditer(scoped)
    ]
    contrasts = list(CONTRAST_SCAFFOLD.finditer(scoped))
    if len(contrasts) >= 3:
        findings.extend(
            _finding(
                text,
                match,
                "repeated-scaffolding",
                "review",
                "This contrast setup recurs at least three times. Review repetition in context; intentional rhetoric may be kept.",
            )
            for match in contrasts
        )
    findings = [found for found in findings if scoped[found.start : found.end] == text[found.start : found.end]]
    findings.sort(key=lambda found: (found.start, found.end, found.rule_id))
    return ProseScanReport(
        source=label,
        source_kind="markdown" if path is not None and path.suffix.lower() in {".md", ".markdown"} else "text",
        findings=findings,
        protected_spans=len(spans),
        warnings=[SCOPE_WARNING],
    )


def scan_prose(source: str | None = None, path: Path | None = None) -> ProseScanReport:
    """Locate a small set of inspectable editorial candidates without a model or network."""
    text, label = _load(source, path)
    return _scan(text, label, path)


def _prompt(
    template: str,
    text: str,
    scanned: ProseScanReport,
    audit_report: ProseAuditReport | None = None,
    context: ReviewContext | None = None,
) -> str:
    environment = Environment(undefined=StrictUndefined)
    return environment.from_string((HERE / template).read_text(encoding="utf-8")).render(
        policy=policy_text(),
        role_contract=role_contract_text(),
        review_context=review_context_text(context),
        source_text=text,
        scan_json=scanned.model_dump_json(indent=2),
        audit_json=audit_report.model_dump_json(indent=2) if audit_report is not None else "",
    )


def _ask[AnswerType: BaseModel](
    intelligence: Intelligence, model: str, effort: ReasoningEffort, prompt: str, answer_type: type[AnswerType]
) -> AnswerType:
    result = intelligence.run(
        AgentRequest(
            prompt=prompt,
            model=model,
            reasoning_effort=effort,
            timeout_seconds=TIMEOUT_SECONDS,
            output_schema=answer_type.model_json_schema(),
        )
    )
    if result.error:
        raise UnslopperError(
            f"The prose model call through {intelligence.implementation} failed: {result.error}. Check credentials and network, then retry; the original file is untouched."
        )
    try:
        return answer_type.model_validate(result.output)
    except ValidationError as error:
        raise UnslopperError(
            f"The prose model answer has an invalid shape ({error.error_count()} problem(s)). Retry with a valid structured answer; the original file is untouched."
        ) from None


def _validate_findings(text: str, findings: list[ProseFinding]) -> None:
    scoped, _ = scoped_text(text)
    for found in findings:
        if (
            found.rule_id not in RULE_IDS
            or found.end <= found.start
            or found.end > len(text)
            or text[found.start : found.end] != found.evidence
            or not scoped[found.start : found.end].strip()
            or scoped[found.start : found.end] != text[found.start : found.end]
            or found.line != text.count("\n", 0, found.start) + 1
            or (found.category == "objective" and found.rule_id != "duplicate-word")
            or (found.category == "objective" and RULES[0][1].fullmatch(found.evidence) is None)
        ):
            raise UnslopperError(
                "The prose model returned an ungrounded or protected-span finding. Retry with exact source offsets and evidence; the original file is untouched."
            )


def audit_prose(
    source: str | None = None,
    path: Path | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    context: ReviewContext | None = None,
) -> ProseAuditReport:
    """Judge prose candidates in context, retaining keep and uncertain outcomes. Model-backed."""
    text, label = _load(source, path)
    scanned = _scan(text, label, path)
    prompt = _prompt("audit.md.liquid", text, scanned, context=context)
    intelligence, model = select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)
    intelligence.preflight()
    answer = _ask(intelligence, model, reasoning_effort, prompt, ProseAuditAnswer)
    _validate_findings(text, answer.findings)
    validate_review_comments(text, answer.author_comments, context)
    return ProseAuditReport(
        source=label,
        summary=answer.summary,
        findings=answer.findings,
        scan=scanned,
        warnings=[*scanned.warnings, REVIEW_WARNING, *answer.warnings],
        author_comments=answer.author_comments,
    )


def unslop_prose(
    path: Path,
    write: bool = False,
    audit_report: ProseAuditReport | None = None,
    agent_provider: AgentProvider | None = None,
    model: str | None = None,
    reasoning_effort: ReasoningEffort = "medium",
    intelligence: Intelligence | None = None,
    context: ReviewContext | None = None,
) -> ProseEditResult:
    """Propose a minimal prose edit and diff; write only after mechanical fidelity checks. Model-backed."""
    original, label = _load(None, path)
    before = _scan(original, label, path)
    if audit_report is not None:
        if audit_report.source != label:
            raise UnslopperError(
                "The prose audit belongs to a different source. Audit this file before reusing its report."
            )
        _validate_findings(original, audit_report.findings)
        validate_review_comments(original, audit_report.author_comments, context)
    prompt = _prompt("unslop.md.liquid", original, before, audit_report, context)
    intelligence, model = select_intelligence(intelligence, agent_provider, model, DEFAULT_INTELLIGENCE_MODELS)
    intelligence.preflight()
    answer = _ask(
        intelligence,
        model,
        reasoning_effort,
        prompt,
        ProseEditAnswer,
    )
    edited = answer.proposed_text.replace("\r\n", "\n")
    if len(edited) > MAX_PROSE_CHARS:
        raise UnslopperError(
            "The prose edit exceeds the source size limit. Retry a smaller edit; the original file is untouched."
        )
    check_fidelity(original, edited)
    validate_review_comments(original, answer.author_comments, context)
    comments = list(audit_report.author_comments) if audit_report is not None else []
    comments.extend(comment for comment in answer.author_comments if comment not in comments)
    for comment in comments:
        if (comment.action == "ask_author" or comment.argument is not None) and edited.count(
            comment.passage
        ) < original.count(comment.passage):
            raise UnslopperError(
                "The prose edit changed an argument or passage awaiting the author's response. "
                "Keep it intact and return the focused author comment; the original file is untouched."
            )
    if context is not None and "editor" not in context.roles and edited != original:
        raise UnslopperError(
            "Research-only scope returns author comments without rewriting. Add an explicit editor scope for prose edits; the original file is untouched."
        )
    if audit_report is not None:
        for found in audit_report.findings:
            if found.disposition in {"keep", "uncertain"} and edited.count(found.evidence) < original.count(
                found.evidence
            ):
                raise UnslopperError(
                    "The prose edit changed a keep or uncertain audit finding. Preserve that text and retry; the original file is untouched."
                )
    after = _scan(edited, label, path)
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            edited.splitlines(keepends=True),
            fromfile=f"a/{path.name}",
            tofile=f"b/{path.name}",
        )
    )
    if write:
        if path.read_text(encoding="utf-8") != original:
            raise UnslopperError(
                "The prose file changed during review. Re-read it before editing; this run did not write the file."
            )
        newline = "\r\n" if b"\r\n" in path.read_bytes() else "\n"
        try:
            path.write_text(edited, encoding="utf-8", newline=newline)
        except OSError as error:
            raise UnslopperError(
                f"Could not write prose file {path}: {error}. Review the proposed edit and file access."
            ) from None
    return ProseEditResult(
        path=path,
        proposed_text=edited,
        diff=diff,
        before=before,
        after=after,
        written=write,
        notes=[*answer.notes, FIDELITY_WARNING, REVIEW_WARNING],
        author_comments=comments,
    )
