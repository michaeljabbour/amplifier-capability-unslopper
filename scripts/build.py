#!/usr/bin/env python3
"""Build the Unslopper website into _site/ from the repository's own sources, with the standard library only.

index.html presents the tool with the recorded outputs under site/artifacts rendered as they are. course.html is
the Unslop School, generated from docs/unslop-school.html so the lessons have one source. Downloads: every skill
as plain files and one zip with a sha256, the docs and the artifacts. Every link is relative so the site works
under a repository subpath.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import sys
import tomllib
from typing import Any, NamedTuple
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
ARTIFACTS = SITE / "artifacts"
SKILLS = ROOT / "skills"
COURSE = ROOT / "docs" / "unslop-school.html"
KNOWLEDGE = ROOT / "src" / "unslopper" / "knowledge.py"
ROUTES_SOURCE = ROOT / "src" / "unslopper" / "capabilities" / "route" / "capability.py"
CAPABILITIES_SOURCE = ROOT / "src" / "unslopper" / "core" / "skill.py"
MANIFEST = ROOT / "src" / "unslopper" / "SMART_TOOL.md"
VISION = ROOT / "docs" / "00-vision.md"
RECORDED_DOC = ROOT / "docs" / "RECORDED-OUTPUTS.md"
ZIP_NAME = "unslopper-skills.zip"
ROUTER_SKILL = "unslopper"
MOVES = ("Subtract", "Focus", "Systematize", "Respond")
DOWNLOADS = ("README.md", "CONTRIBUTING.md", "LICENSE", "site/README.md", "docs/unslop-school.html")
# Frames hold model-written markup with inline styles, so each gets its own policy and no network at all.
FRAME_CSP = "default-src 'none'; style-src 'unsafe-inline'"
REMOTE_LINK = re.compile(r"[ \t]*<link\b[^>]*\bhref=\"https?://[^\"]*\"[^>]*>[ \t]*\n?")
NUMBER_WORDS = (
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
)


class Skill(NamedTuple):
    name: str
    description: str
    files: list[str]


class CapabilityRow(NamedTuple):
    name: str
    summary: str
    model_backed: bool


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def must(match: re.Match[str] | None, what: str) -> re.Match[str]:
    if match is None:
        raise ValueError(f"Expected to find {what}")
    return match


def words(count: int) -> str:
    return NUMBER_WORDS[count].capitalize() if count < len(NUMBER_WORDS) else str(count)


# region: Sources


def project() -> dict[str, str]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return {"version": data["version"], "repository": data["urls"]["Repository"], "description": data["description"]}


def folded(frontmatter: str, key: str) -> str:
    """The value of `key` in YAML frontmatter, joining a `>-` folded block into one line."""
    block = re.search(rf"^{key}: >-\n((?:[ \t]+\S.*\n?)+)", frontmatter, re.M)
    if block:
        return " ".join(line.strip() for line in block.group(1).splitlines())
    return must(re.search(rf"^{key}:[ \t]*(.+)$", frontmatter, re.M), f"frontmatter key {key}").group(1).strip()


def manifest_description() -> str:
    return folded(MANIFEST.read_text(encoding="utf-8").split("---", 2)[1], "description")


def assigned(source: Path, name: str) -> ast.expr:
    for node in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            if node.value is None:
                break
            return node.value
    raise ValueError(f"{source.name} has no assignment to {name}")


def keywords(call: ast.expr) -> dict[str, object]:
    if not isinstance(call, ast.Call):
        raise ValueError("Expected a call")
    return {str(keyword.arg): ast.literal_eval(keyword.value) for keyword in call.keywords}


def capabilities() -> list[CapabilityRow]:
    """The CAPABILITIES table in core/skill.py: name, summary and whether a model is involved."""
    table = assigned(CAPABILITIES_SOURCE, "CAPABILITIES")
    if not isinstance(table, ast.Tuple):
        raise ValueError("CAPABILITIES must be a tuple")
    rows: list[CapabilityRow] = []
    for call in table.elts:
        if not isinstance(call, ast.Call):
            raise ValueError("Each capability must be a Capability(...) call")
        positional = [ast.literal_eval(argument) for argument in call.args]
        named = keywords(call)
        rows.append(CapabilityRow(str(positional[0]), str(positional[1]), bool(named["model_backed"])))
    return rows


def routes() -> list[dict[str, str]]:
    """The ROUTES table in route/capability.py: capability, skill, when and the example command."""
    table = assigned(ROUTES_SOURCE, "ROUTES")
    if not isinstance(table, ast.Tuple):
        raise ValueError("ROUTES must be a tuple")
    rows: list[dict[str, str]] = []
    for entry in table.elts:
        if not isinstance(entry, ast.Tuple) or len(entry.elts) != 3:
            raise ValueError("Each route must be (RouteOption, command, words)")
        option = keywords(entry.elts[0])
        command = ast.literal_eval(entry.elts[1])
        rows.append(
            {
                "capability": str(option["capability"]),
                "skill": str(option["skill"]),
                "when": str(option["when"]),
                "command": str(command),
            }
        )
    return rows


def skills() -> list[Skill]:
    """Every skills/*/SKILL.md with its frontmatter name and description, the router first."""
    found: list[Skill] = []
    for path in sorted(SKILLS.glob("*/SKILL.md")):
        frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
        name = must(re.search(r"^name:\s*(\S+)", frontmatter, re.M), f"name in {path}").group(1)
        files = sorted(
            child.relative_to(SKILLS).as_posix()
            for child in path.parent.rglob("*")
            if child.is_file() and not child.name.startswith(".")
        )
        found.append(Skill(name, folded(frontmatter, "description"), files))
    return sorted(found, key=lambda skill: (skill.name != ROUTER_SKILL, skill.name))


def non_goals() -> list[str]:
    section = must(
        re.search(r"^## Non-Goals\n(.*?)(?=^## |\Z)", VISION.read_text(encoding="utf-8"), re.M | re.S), "Non-Goals"
    )
    return [line[2:].strip() for line in section.group(1).splitlines() if line.startswith("- ")]


def knowledge_counts() -> dict[str, int]:
    text = KNOWLEDGE.read_text(encoding="utf-8")
    return {
        "terms": len(re.findall(r"^\s+Term\(", text, re.M)),
        "indicators": len(re.findall(r"^\s+Indicator\(", text, re.M)),
        "fixes": len(re.findall(r"^\s+Fix\(", text, re.M)),
        "textures": len(re.findall(r"^\s+Texture\(", text, re.M)),
    }


def course_counts(script: str) -> dict[str, int]:
    """How many entries each data table in the course script carries, by its own formatting."""

    def block(name: str, opener: str, closer: str) -> str:
        return must(
            re.search(rf"const {name}\s*=\s*{re.escape(opener)}(.*?)\n{re.escape(closer)};", script, re.S), name
        ).group(1)

    return {
        "terms": len(re.findall(r'^ \["', block("TERMS", "[", "]"), re.M)),
        "indicators": len(re.findall(r'^  \["', block("SLOP", "[", "]"), re.M)),
        "fixes": len(re.findall(r"^ \d+:\[", block("FIXES", "{", "}"), re.M)),
        "textures": len(re.findall(r'^ \["', block("TX", "[", "]"), re.M)),
        "prompts": len(re.findall(r'^ \["[^"]+","[^"]+",$', block("PROMPTS", "[", "]"), re.M)),
    }


def artifacts() -> dict[str, object]:
    manifest = json.loads((ARTIFACTS / "manifest.json").read_text(encoding="utf-8"))
    runs: dict[str, dict[str, object]] = {}
    for run in manifest["runs"]:
        output = run.get("output")
        data = json.loads((ARTIFACTS / output).read_text(encoding="utf-8")) if output else None
        runs[run["name"]] = {**run, "data": data}
    return {"manifest": manifest, "runs": runs, "date": manifest["captured"][:10]}


# endregion

# region: Frames and derived assets


def frame_document(source: str, origin: str) -> str:
    """A recorded HTML file made embeddable: remote link elements removed, a no-network policy added, nothing else."""
    stripped = REMOTE_LINK.sub("", source)
    marker = '<meta charset="utf-8">\n'
    if marker not in stripped:
        raise ValueError(f"{origin} needs a utf-8 charset meta on its own line")
    head = (
        f'<meta http-equiv="Content-Security-Policy" content="{FRAME_CSP}">\n'
        f"<!-- Built from {origin}: remote link elements removed so this frame loads nothing from outside; "
        "the rest is the file as recorded. -->\n"
    )
    return stripped.replace(marker, marker + head, 1)


def tutor_frame(demo_html: str, term: str) -> str:
    return (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{FRAME_CSP}">'
        f"<title>{escape(term)}: the demo from unslopper tutor</title></head>\n"
        f"<body>\n{demo_html}\n</body></html>\n"
    )


def texture_code(data: dict[str, object]) -> tuple[str, str, str]:
    """The texture artifact split for a strict page: (kind, markup for the page, code to ship as a file)."""
    code = str(data["code"])
    if data["kind"] == "canvas":
        script = must(re.search(r"<script>\n?(.*?)\n?</script>", code, re.S), "the texture script").group(1)
        canvas = must(re.search(r"<canvas\b[^>]*>", code), "the texture canvas").group(0)
        return "canvas", canvas, script
    return "css", "", code


def hex_class(value: str) -> str:
    return "hex-" + value.lstrip("#").lower()


def swatch(value: str, label: str) -> str:
    return f'<span class="swatch {hex_class(value)}" role="img" aria-label="{escape(label)}"></span>'


def artifacts_css(runs: dict[str, dict[str, object]]) -> str:
    """Colours the artifacts name, as classes, so the page can show them without inline styles."""
    colours: dict[str, str] = {}
    data = runs.get("direct", {}).get("data")
    if isinstance(data, dict):
        for direction in data["directions"]:
            for colour in direction["palette"]:
                colours[hex_class(colour["hex"])] = colour["hex"]
    data = runs.get("contrast", {}).get("data")
    if isinstance(data, dict):
        for key in ("foreground", "background"):
            colours[hex_class(data[key])] = data[key]
    data = runs.get("texture", {}).get("data")
    lines = ["/* Generated by scripts/build.py from site/artifacts; colours are the recorded values. */"]
    if isinstance(data, dict):
        palette = data["palette"]
        for key in ("ground", "light", "signal"):
            colours[hex_class(palette[key])] = palette[key]
        lines.append(f".texture-panel {{ background: {palette['ground']}; }}")
        lines.append(f".texture-text {{ color: {palette['light']}; }}")
        lines.append(f".texture-text .texture-signal {{ color: {palette['signal']}; }}")
        kind, _, code = texture_code(data)
        if kind == "css":
            lines.append(code)
    lines.extend(f".{name} {{ background: {value}; }}" for name, value in sorted(colours.items()))
    return "\n".join(lines) + "\n"


# endregion

# region: index.html


def run_line(run: dict[str, object], date: str) -> str:
    output = run.get("output")
    link = f' <a href="artifacts/{escape(output)}">{escape(output)}</a>' if output else ""
    return (
        f'<p class="run"><code>{escape(run["command"])}</code>'
        f'<span class="run-meta">{escape(date)}, {float(str(run["seconds"])):.1f} s, exit {run["exit_code"]}{link}</span></p>'
    )


def article(run: dict[str, object], date: str, title: str, body: str) -> str:
    name = str(run["name"])
    return (
        f'<article class="artifact" id="artifact-{escape(name)}" data-artifact="{escape(name)}">'
        f"<h3>{escape(title)}</h3>{run_line(run, date)}{body}</article>"
    )


def failed_article(run: dict[str, object], date: str, title: str) -> str:
    body = (
        f"<p>This run failed on {escape(date)} with exit code {run['exit_code']} after "
        f"{float(str(run['seconds'])):.1f} seconds, so there is no output file and nothing to show. "
        "The error it printed:</p>"
        f'<pre class="stderr">{escape(run.get("stderr") or "(no message)")}</pre>'
    )
    return article(run, date, title, body)


def score_line(report: dict[str, object], measure: str, extra: str = "") -> str:
    also = f' <span class="measure-also">{extra}</span>' if extra else ""
    return f'<p class="measure"><b class="num">{report["score"]}</b> of 20 by {measure}: {escape(report["verdict"])}{also}</p>'


def evidence_list(items: list[dict[str, str]]) -> str:
    return (
        '<ul class="evidence">'
        + "".join(
            f"<li><code>{escape(item['location'])}</code> <code>{escape(item['detail'])}</code></li>" for item in items
        )
        + "</ul>"
    )


def frames_block(runs: dict[str, dict[str, object]], fixture: str) -> tuple[str, dict[str, str]]:
    """The recorded card before and after, side by side, as sandboxed frames with their scores."""
    frames: dict[str, str] = {}
    figures: list[str] = []

    def figure(label: str, file: str, measure: str) -> None:
        frames[file] = frame_document((ARTIFACTS / file).read_text(encoding="utf-8"), f"site/artifacts/{file}")
        figures.append(
            f'<figure class="frame"><figcaption><b>{escape(label)}</b>{measure}</figcaption>'
            f'<iframe src="frames/{escape(file)}" title="{escape(label)}, rendered without its web fonts" '
            f'sandbox width="640" height="420"></iframe>'
            f'<p class="frame-links"><a href="artifacts/{escape(file)}">{escape(file)}</a></p></figure>'
        )

    unslop = runs.get("unslop", {})
    unslop_data = unslop.get("data")
    if isinstance(unslop_data, dict):
        figure("Before", "before.html", score_line(unslop_data["before"], "scan"))
        after = unslop.get("after")
        if after and (ARTIFACTS / str(after)).is_file():
            figure("After unslop", str(after), score_line(unslop_data["after"], "scan"))
    else:
        figure("Before", "before.html", "")
    antislop = runs.get("antislop", {})
    antislop_data = antislop.get("data")
    after = antislop.get("after")
    if isinstance(antislop_data, dict) and after and (ARTIFACTS / str(after)).is_file():
        report = antislop_data["after"]
        scan = report.get("scan")
        extra = f"Scan of the same file: {scan['score']} of 20." if scan else ""
        figure("After antislop", str(after), score_line(report, "audit", extra))
    note = (
        f"<p>The card is <code>{escape(fixture)}</code>, the lesson 3 feature card for an imaginary coding agent. "
        "Each frame is the recorded file with its remote font links removed, because this site loads nothing from "
        "outside; the headline falls back to a system serif where the file asked for Instrument Serif.</p>"
    )
    return f'<div class="frames">{"".join(figures)}</div>{note}', frames


def scan_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "scan")
    hits = "".join(
        f'<li><b>{escape(hit["indicator"])}</b><span class="layer">{escape(hit["layer"])}</span>{evidence_list(hit["evidence"])}</li>'
        for hit in data["hits"]
    )
    body = (
        score_line(data, "scan")
        + f"<p>{len(data['hits'])} indicators found statically, each with the line a person can open.</p>"
        + f'<ul class="hits">{hits}</ul>'
        + f"<p>Fixes first: {escape(', '.join(data['fixes_first']))}.</p>"
    )
    return article(run, date, "scan", body)


def audit_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "audit")
    findings = "".join(
        f'<li><b>{escape(f["indicator"])}</b><span class="layer">{escape(f["layer"])}</span>'
        f'<p class="where">{"Deliberate, left alone" if f["deliberate"] else "Default"} at <code>{escape(f["location"])}</code></p>'
        f"<p><code>{escape(f['evidence'])}</code></p><p>{escape(f['rationale'])}</p></li>"
        for f in data["findings"]
    )
    body = (
        score_line(data, "audit")
        + f"<p>{escape(data['summary'])}</p>"
        + f'<ul class="hits findings">{findings}</ul>'
        + f"<p>Fixes first: {escape(', '.join(data['fixes_first']))}.</p>"
    )
    return article(run, date, "audit", body)


def diff_details(diff: str, summary: str) -> str:
    lines = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(f"<ins>{escape(line)}</ins>")
        elif line.startswith("-") and not line.startswith("---"):
            lines.append(f"<del>{escape(line)}</del>")
        else:
            lines.append(escape(line))
    return f'<details><summary>{escape(summary)}</summary><pre class="diff">{chr(10).join(lines)}</pre></details>'


def unslop_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "unslop")
    groups = []
    for move in MOVES:
        changes = [c for c in data["plan"] if c["move"] == move]
        if changes:
            items = "".join(f"<li><b>{escape(c['fix'])}</b> {escape(c['change'])}</li>" for c in changes)
            groups.append(f"<li><h4>{escape(move)}</h4><ul>{items}</ul></li>")
    notes = "".join(f"<li>{escape(note)}</li>" for note in data["notes"])
    body = (
        f"<p>Scan {data['before']['score']} of 20 before, {data['after']['score']} of 20 after; "
        f"{len(data['plan'])} planned changes; written: {'yes' if data['written'] else 'no'}.</p>"
        f'<ul class="plan">{"".join(groups)}</ul>'
        f"<h4>What to check by hand</h4><ul>{notes}</ul>" + diff_details(data["diff"], "The unified diff")
    )
    return article(run, date, "unslop", body)


def antislop_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "antislop")
    steps = "".join(
        f"<li><b>{escape(step['name'])}</b> {'ran' if step['ran'] else 'skipped'}: {escape(step['note'])}</li>"
        for step in data["steps"]
    )
    summary = "".join(f"<p>{escape(line)}</p>" for line in str(data["summary"]).splitlines())
    body = (
        f"<p>Audit {data['before']['score']} of 20 before, {data['after']['score']} of 20 after; "
        f"written: {'yes' if data['written'] else 'no'}.</p>"
        f'<ol class="steps">{steps}</ol><h4>The three-line summary</h4><div class="summary">{summary}</div>'
        + diff_details(data["diff"], "The unified diff")
    )
    return article(run, date, "antislop", body)


def direct_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "direct")
    blocks = []
    for direction in data["directions"]:
        swatches = "".join(
            f"<li>{swatch(c['hex'], f'{c["role"]} colour {c["hex"]}')}<b>{escape(c['role'])}</b> {escape(c['name'])}"
            f"<br><code>{escape(c['hex'])}</code> <code>{escape(c['oklch'])}</code></li>"
            for c in direction["palette"]
        )
        contrast = direction["contrast"]
        passes = [
            name
            for name, key in (("AA body", "aa_body"), ("AA large", "aa_large"), ("AAA body", "aaa_body"))
            if contrast[key]
        ]
        typography = direction["typography"]
        blocks.append(
            f'<p class="scene">{escape(direction["scene"])}</p>'
            f'<ul class="swatches">{swatches}</ul>'
            f"<p>Light on ground <code>{escape(contrast['foreground'])}</code> on <code>{escape(contrast['background'])}</code>: "
            f'<b class="num">{contrast["ratio"]}</b> to 1, passes {escape(", ".join(passes) or "nothing")}.</p>'
            f"<p>Type: {escape(typography['display'])} for display, {escape(typography['body'])} for body. {escape(typography['rationale'])}</p>"
            f"<p>Hero: {escape(direction['hero'])}</p>"
            f"<pre><code>{escape(direction['css'])}</code></pre>"
        )
    body = f"<p>Brief: {escape(data['brief'])}</p>" + "".join(blocks)
    return article(run, date, "direct", body)


def texture_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "texture")
    palette = data["palette"]
    kind, canvas, _ = texture_code(data)
    recommendations = "".join(
        f"<li><b>{escape(r['name'])}</b> {escape(r['why'])}</li>" for r in data["recommendations"]
    )
    swatches = "".join(
        f"<li>{swatch(palette[key], f'{key} colour {palette[key]}')}<b>{key}</b><br><code>{escape(palette[key])}</code></li>"
        for key in ("ground", "light", "signal")
    )
    if kind == "canvas":
        surface = (
            re.sub(r"\s*>$", "", canvas) + ' role="img" aria-label="The paper texture the artifact draws"></canvas>'
        )
        shipping = (
            "The code is a canvas drawing with its own seeded random, so it draws the same every load. Its script "
            "runs here from <code>assets/texture-artifact.js</code>, moved out of the inline tag unchanged because "
            "this page allows no inline scripts."
        )
    else:
        surface = '<div class="texture" role="img" aria-label="The texture the artifact draws"></div>'
        shipping = "The code is a stylesheet, loaded here from <code>assets/artifacts.css</code> unchanged."
    panel = (
        f'<div class="texture-panel">{surface}<div class="texture-text">'
        f'<p class="texture-title">{escape(data["texture"])}, drawn live in <span class="texture-signal">{escape(palette["ground"])}</span>, '
        f"{escape(palette['light'])} and {escape(palette['signal'])}</p>"
        f"<p>{escape(data['contrast'])}</p></div></div>"
    )
    warning = f"<p>Warning: {escape(data['warning'])}</p>" if data.get("warning") else "<p>Warning: none.</p>"
    body = (
        f'<ul class="swatches">{swatches}</ul>'
        f"<h4>Recommended for the subject</h4><ul>{recommendations}</ul>"
        f"<p>Drawn: {escape(data['texture'])}, as {escape(kind)}, {data['size_bytes']} bytes.</p>"
        + panel
        + f"<p>{shipping}</p>"
        + warning
        + f"<details><summary>The code</summary><pre><code>{escape(data['code'])}</code></pre></details>"
    )
    return article(run, date, "texture", body)


def tutor_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "tutor")
    paragraphs = "".join(f"<p>{escape(part)}</p>" for part in str(data["text"]).split("\n\n"))
    body = (
        f"<p>Mode {escape(data['mode'])}, term {escape(data['term'])}. Next term: {escape(data['next_term'])}.</p>"
        + paragraphs
        + '<iframe class="demo-frame" src="frames/tutor-demo.html" title="The wrong and right demo from the tutor" sandbox width="640" height="200"></iframe>'
        + f'<p class="prompt-line" id="tutor-prompt">{escape(data["prompt_line"])}</p>'
        + '<p class="copy-row"><button class="copy-button" type="button" data-copy="tutor-prompt">Copy the prompt line</button><span class="copy-status" role="status"></span></p>'
    )
    return article(run, date, "tutor", body)


def contrast_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "contrast")
    passes = [
        name for name, key in (("AA body", "aa_body"), ("AA large", "aa_large"), ("AAA body", "aaa_body")) if data[key]
    ]
    body = (
        '<ul class="swatches pair">'
        f"<li>{swatch(data['foreground'], f'foreground {data["foreground"]}')}<b>foreground</b><br><code>{escape(data['foreground'])}</code></li>"
        f"<li>{swatch(data['background'], f'background {data["background"]}')}<b>background</b><br><code>{escape(data['background'])}</code></li></ul>"
        f'<p><b class="num">{data["ratio"]}</b> to 1, passes {escape(", ".join(passes) or "nothing")}.</p>'
    )
    return article(run, date, "contrast", body)


def route_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "route")
    body = (
        f"<p>Job: {escape(data['intent'])}</p>"
        f"<p>Capability <code>{escape(data['capability'])}</code>, skill <code>{escape(data['skill'])}</code>, "
        f"start from <code>{escape(data['command'])}</code>.</p>"
        f"<p>{escape(data['reason'])}</p>"
        f'<p>The {len(data["alternatives"])} alternatives it returned are the table under <a href="#which">which capability for which job</a>.</p>'
    )
    return article(run, date, "route", body)


def reference_article(run: dict[str, object], date: str) -> str:
    data = run["data"]
    if not isinstance(data, dict):
        return failed_article(run, date, "reference")
    items = "".join(
        f'<li><b>{escape(item["name"])}</b><span class="layer">{escape(item["layer"])}</span> {escape(item["description"])} '
        f"Fixes {escape(', '.join(str(i) for i in item['fix_ids']))}.</li>"
        for item in data["items"]
    )
    body = (
        f"<p>Topic {escape(data['topic'])}: {len(data['items'])} items, the same data the scan, the audit and the course read.</p>"
        f'<details><summary>The {len(data["items"])} items</summary><ul class="hits">{items}</ul></details>'
    )
    return article(run, date, "reference", body)


RENDERERS = {
    "scan": scan_article,
    "audit": audit_article,
    "unslop": unslop_article,
    "antislop": antislop_article,
    "direct": direct_article,
    "contrast": contrast_article,
    "texture": texture_article,
    "tutor": tutor_article,
    "route": route_article,
    "reference-indicators": reference_article,
}


def outputs_block(recorded: dict[str, object]) -> tuple[str, str, dict[str, str]]:
    """The frames, the full articles and the frame documents, from the manifest as it is."""
    runs = recorded["runs"]
    manifest = recorded["manifest"]
    date = str(recorded["date"])
    if not isinstance(runs, dict) or not isinstance(manifest, dict):
        raise ValueError("Artifacts manifest has an unexpected shape")
    frames_html, frames = frames_block(runs, str(manifest["fixture"]))
    unknown = [name for name in runs if name not in RENDERERS]
    if unknown:
        raise ValueError(f"No renderer for recorded runs: {unknown}")
    articles = "".join(RENDERERS[name](runs[name], date) for name in RENDERERS if name in runs)
    tutor = runs.get("tutor", {}).get("data")
    if isinstance(tutor, dict):
        frames["tutor-demo.html"] = tutor_frame(str(tutor["demo_html"]), str(tutor["term"]))
    return frames_html, articles, frames


def rerun_note(manifest: dict[str, object]) -> str:
    rerun = manifest.get("partial_rerun")
    if not rerun:
        return ""
    names = ", ".join(str(name) for name in rerun) if isinstance(rerun, list) else str(rerun)
    return f" The manifest marks {names} as rerun on that date after a first attempt failed."


def run_note(recorded: dict[str, object], counts: dict[str, int]) -> str:
    manifest = recorded["manifest"]
    if not isinstance(manifest, dict):
        raise ValueError("Artifacts manifest has an unexpected shape")
    runs = manifest["runs"]
    failed = [run["name"] for run in runs if run["exit_code"]]
    note = (
        f"{escape(manifest['note'])} That date is {escape(recorded['date'])}; "
        f"{counts['model_backed']} of the {len(runs)} commands are model-backed and ran through the "
        f"<code>{escape(manifest['provider'])}</code> agent provider. A different run can answer differently."
        + escape(rerun_note(manifest))
    )
    if failed:
        note += f" {escape(', '.join(failed))} failed and has no output file; the page says so where it would have appeared."
    return note


def manifest_table(manifest: dict[str, Any]) -> str:
    rows = []
    for run in manifest["runs"]:
        output = run.get("output")
        link = f'<a href="artifacts/{escape(output)}">{escape(output)}</a>' if output else "none, the run failed"
        rows.append(
            f"<tr><td><code>{escape(run['name'])}</code></td><td><code>{escape(run['command'])}</code></td>"
            f'<td class="num">{run["exit_code"]}</td><td class="num">{float(run["seconds"]):.1f}</td><td>{link}</td></tr>'
        )
    return (
        '<div class="table-scroll" tabindex="0" role="region" aria-label="The manifest of recorded runs; scroll horizontally to read all columns">'
        '<table class="manifest"><thead><tr><th scope="col">Run</th><th scope="col">Command</th><th scope="col">Exit</th>'
        '<th scope="col">Seconds</th><th scope="col">Output</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


def passes(contrast: dict[str, Any]) -> str:
    levels = [
        name
        for name, key in (("AA body", "aa_body"), ("AA large", "aa_large"), ("AAA body", "aaa_body"))
        if contrast[key]
    ]
    return ", ".join(levels) or "nothing"


def key_figures(name: str, data: dict[str, Any] | None) -> str:
    """One plain sentence per run: the figure a reader would quote. Shared by the front page and the Markdown."""
    if data is None:
        return "Failed; no output."
    if name == "scan":
        return f"{data['score']} of 20 by scan, {data['verdict']}: {len(data['hits'])} indicators found statically, each with the line to open."
    if name == "audit":
        return f"{data['score']} of 20 by audit, {data['verdict']}. {data['summary']}"
    if name == "unslop":
        return f"{len(data['plan'])} fixes; scan {data['before']['score']} of 20 to {data['after']['score']} of 20."
    if name == "antislop":
        return f"{str(data['summary']).splitlines()[0]} {len(data['steps'])} pipeline steps."
    if name == "direct":
        direction = data["directions"][0]
        typography = direction["typography"]
        hexes = ", ".join(colour["hex"] for colour in direction["palette"])
        return (
            f"{len(data['directions'])} direction: {hexes}; {typography['display']} for display, {typography['body']} for body; "
            f"light on ground {direction['contrast']['ratio']} to 1."
        )
    if name == "texture":
        recommended = ", ".join(r["name"] for r in data["recommendations"])
        return f"{data['texture']} as {data['kind']}, {data['size_bytes']} bytes; recommended {recommended}."
    if name == "tutor":
        return f"{data['term']}: {data['prompt_line']}"
    if name == "contrast":
        return f"{data['foreground']} on {data['background']}: {data['ratio']} to 1, passes {passes(data)}."
    if name == "route":
        return f"{data['capability']}, through the {data['skill']} skill, for: {data['intent']}."
    if name == "reference-indicators":
        return f"{len(data['items'])} {data['topic']} as data, the same list the scan, the audit and the course read."
    raise ValueError(f"No key figure for {name}")


def compact_rows(recorded: dict[str, object]) -> str:
    """One short row per recorded run for the front page, each linking to its full rendering and its JSON."""
    runs = recorded["runs"]
    date = str(recorded["date"])
    if not isinstance(runs, dict):
        raise ValueError("Artifacts manifest has an unexpected shape")
    rows = []
    for name in RENDERERS:
        run = runs.get(name)
        if run is None:
            continue
        data = run["data"]
        title = "reference" if name == "reference-indicators" else name
        if not isinstance(data, dict):
            body = f"<p>Failed on {escape(date)} with exit code {run['exit_code']}; there is no output to show.</p>"
        elif name == "audit":
            body = f'<p class="measure"><b class="num">{data["score"]}</b> of 20 by audit</p><p>{escape(data["summary"])}</p>'
        elif name == "unslop":
            body = f"<p>{len(data['plan'])} fixes, scan {data['before']['score']} to {data['after']['score']}.</p>"
        elif name == "antislop":
            body = f"<p>{escape(str(data['summary']).splitlines()[0])}</p>"
        elif name == "direct":
            direction = data["directions"][0]
            swatches = "".join(
                f"<li>{swatch(c['hex'], f'{c["role"]} colour {c["hex"]}')}<code>{escape(c['hex'])}</code></li>"
                for c in direction["palette"]
            )
            typography = direction["typography"]
            body = (
                f'<ul class="swatches small">{swatches}</ul>'
                f"<p>{escape(typography['display'])} with {escape(typography['body'])}; light on ground "
                f'<b class="num">{direction["contrast"]["ratio"]}</b> to 1.</p>'
            )
        elif name == "texture":
            kind, canvas, _ = texture_code(data)
            surface = (
                re.sub(r"\s*>$", "", canvas) + ' role="img" aria-label="The paper texture the artifact draws"></canvas>'
                if kind == "canvas"
                else '<div class="texture" role="img" aria-label="The texture the artifact draws"></div>'
            )
            body = (
                f'<div class="texture-panel compact">{surface}<div class="texture-text">'
                f'<p class="texture-title">{escape(data["texture"])}</p><p>{escape(kind)}, {data["size_bytes"]} bytes, drawn live from the recorded code.</p></div></div>'
            )
        elif name == "tutor":
            body = (
                '<iframe class="demo-frame" src="frames/tutor-demo.html" title="The wrong and right demo from the tutor" sandbox width="640" height="200"></iframe>'
                f'<p class="prompt-line">{escape(data["prompt_line"])}</p>'
            )
        elif name == "contrast":
            body = f'<p><b class="num">{data["ratio"]}</b> to 1, <code>{escape(data["foreground"])}</code> on <code>{escape(data["background"])}</code>, passes {escape(passes(data))}.</p>'
        elif name == "route":
            body = f"<p><code>{escape(data['capability'])}</code> for the job {escape(data['intent'])}.</p>"
        else:
            body = f"<p>{escape(key_figures(name, data))}</p>"
        output = run.get("output")
        links = f'<a href="outputs.html#artifact-{escape(name)}">Full output</a>'
        if output:
            links += f' <a href="artifacts/{escape(output)}">{escape(output)}</a>'
        rows.append(
            f'<li class="row" data-row="{escape(name)}"><h3>{escape(title)}</h3><div class="row-body">{body}</div><p class="row-links">{links}</p></li>'
        )
    return "".join(rows)


def non_goal_heads() -> list[str]:
    return [goal.split(".")[0] for goal in non_goals()]


def non_goal_sentences() -> str:
    """The vision's non-goals as two sentences: their heads joined, then the last one's explanation."""
    goals = non_goals()
    heads = non_goal_heads()
    lower = [head[0].lower() + head[1:] for head in heads[1:]]
    joined = heads[0] + ", " + ", ".join(lower[:-1]) + " and " + lower[-1]
    tail = goals[-1].split(". ", 1)[1] if ". " in goals[-1] else ""
    return f"{joined}. {tail}".strip()


def index_page(config: dict[str, object], info: dict[str, str], recorded: dict[str, object], frames_html: str) -> str:
    table = capabilities()
    deterministic = [row for row in table if not row.model_backed]
    model_backed = [row for row in table if row.model_backed]
    counts = {"deterministic": len(deterministic), "model_backed": len(model_backed)}
    manifest = recorded["manifest"]
    if not isinstance(manifest, dict):
        raise ValueError("Artifacts manifest has an unexpected shape")

    def capability_list(rows: list[CapabilityRow]) -> str:
        return "".join(
            f'<li data-capability="{escape(row.name)}"><code>{escape(row.name)}</code> {escape(row.summary)}</li>'
            for row in rows
        )

    short_note = (
        f"Unedited outputs of one run on {escape(recorded['date'])} over the lesson 3 fixture, "
        f"<code>{escape(manifest['fixture'])}</code>; model-backed commands ran through the <code>{escape(manifest['provider'])}</code> "
        "agent provider. A different run can answer differently." + escape(rerun_note(manifest))
    )
    replacements = {
        "NAME": escape(config["name"]),
        "PROMISE": escape(config["promise"]),
        "DESCRIPTION": escape(manifest_description()),
        "INTRO": escape(str(config["intro"]).format(**counts)),
        "VERSION": escape(info["version"]),
        "REPOSITORY": escape(info["repository"]),
        "SHORT_NOTE": short_note,
        "FRAMES": frames_html,
        "ROWS": compact_rows(recorded),
        "DETERMINISTIC": capability_list(deterministic),
        "MODEL_BACKED": capability_list(model_backed),
        "SKILL_COUNT": words(len(skills())),
        "NON_GOALS": escape(non_goal_sentences()),
        "ZIP": ZIP_NAME,
    }
    page = (SITE / "template.html").read_text(encoding="utf-8")
    for key, value in replacements.items():
        page = page.replace("@@" + key + "@@", value)
    unresolved = re.findall(r"@@[A-Z_]+@@", page)
    if unresolved:
        raise ValueError(f"Unresolved placeholders: {unresolved}")
    return page


def outputs_page(
    info: dict[str, str], recorded: dict[str, object], frames_html: str, articles: str, zip_sha: str
) -> str:
    """Everything recorded, in full: the manifest, the frames, every artifact, the routing table and the skills."""
    manifest = recorded["manifest"]
    if not isinstance(manifest, dict):
        raise ValueError("Artifacts manifest has an unexpected shape")
    counts = {"model_backed": sum(1 for row in capabilities() if row.model_backed)}
    route_rows = "".join(
        f'<tr data-route="{escape(r["capability"])}"><td>{escape(r["when"])}</td><td><code>{escape(r["capability"])}</code></td>'
        f'<td><a href="skills/{escape(r["skill"])}/SKILL.md">{escape(r["skill"])}</a></td><td><code>{escape(r["command"])}</code></td></tr>'
        for r in routes()
    )
    skill_items = "".join(
        f'<li data-skill="{escape(s.name)}"><h3>{escape(s.name)}</h3><p>{escape(s.description)}</p>'
        f'<p class="skill-files">{" ".join(f'<a href="skills/{escape(f)}">{escape(f.split("/", 1)[1])}</a>' for f in s.files)}</p></li>'
        for s in skills()
    )
    body = f"""<main id="main">
<section class="section wrap" id="recorded" aria-labelledby="recorded-title">
<div class="section-heading"><h2 id="recorded-title">The recorded outputs</h2><p>{run_note(recorded, counts)}</p></div>
<h1 class="page-title">One run of every capability against one slop card</h1>
{manifest_table(manifest)}
<p class="downloads">The same table, with the key figures, is kept in <a href="docs/RECORDED-OUTPUTS.md">docs/RECORDED-OUTPUTS.md</a>, generated by the same build. The raw files are under <a href="artifacts/manifest.json">artifacts/</a>.</p>
</section>
<section class="section wrap" id="outputs" aria-labelledby="outputs-title">
<div class="section-heading"><h2 id="outputs-title">The card, before and after</h2><p>The scores come from the tool itself: the scan is deterministic, the audit is the model's reading checked in code.</p></div>
{frames_html}
{articles}
</section>
<section class="section wrap" id="which" aria-labelledby="which-title">
<div class="section-heading"><h2 id="which-title">Which capability for which job</h2><p>The table <code>unslopper route</code> reads. Each row names the capability, the Agent Skill that teaches the same method by hand, and a command to start from.</p></div>
<div class="table-scroll" tabindex="0" role="region" aria-label="Capabilities by job; scroll horizontally to read all columns"><table><thead><tr><th scope="col">When</th><th scope="col">Capability</th><th scope="col">Skill</th><th scope="col">Start from</th></tr></thead><tbody>{route_rows}</tbody></table></div>
</section>
<section class="section wrap" id="skills" aria-labelledby="skills-title">
<div class="section-heading"><h2 id="skills-title">{words(len(skills()))} Agent Skills</h2><p>One router and six method skills. Each prefers the tool when it is installed and carries the method for doing the job by hand when it is not.</p></div>
<ul class="skill-list">{skill_items}</ul>
<div class="skill-install"><pre id="skills-command"><code>npx skills add michaeljabbour/amplifier-capability-unslopper
npx skills add michaeljabbour/amplifier-capability-unslopper --skill design-slop-audit</code></pre><p class="copy-row"><button class="copy-button" type="button" data-copy="skills-command">Copy the commands</button><span class="copy-status" role="status"></span></p>
<p>Or download <a href="{ZIP_NAME}" download>{ZIP_NAME}</a>, the whole <code>skills/</code> directory. Its SHA-256 is <code class="sha">{zip_sha}</code>, also in <a href="{ZIP_NAME}.sha256">{ZIP_NAME}.sha256</a>.</p></div>
</section>
</main>"""
    head = (
        '<link rel="stylesheet" href="assets/artifacts.css">\n<script src="assets/site.js" defer></script>\n'
        '<script src="assets/texture-artifact.js" defer></script>\n'
    )
    return shell(
        "The recorded outputs of Unslopper",
        f"Every capability of Unslopper run once on {recorded['date']} against one slop card, rendered in full from the unedited files.",
        INDEX_CSP,
        body,
        info,
        "outputs.html",
        head,
    )


def recorded_outputs_markdown(recorded: dict[str, object]) -> str:
    """docs/RECORDED-OUTPUTS.md, generated so the repository never carries a hand-maintained duplicate."""
    manifest = recorded["manifest"]
    runs = recorded["runs"]
    if not isinstance(manifest, dict) or not isinstance(runs, dict):
        raise ValueError("Artifacts manifest has an unexpected shape")
    cell = lambda value: str(value).replace("|", "\\|")  # noqa: E731
    lines = [
        "# Recorded outputs",
        "",
        "Generated by `python3 scripts/build.py` from `site/artifacts/manifest.json` and the JSON beside it. Do not edit by hand; `scripts/check.py` fails when this file is stale.",
        "",
        f"{manifest['note']} That date is {recorded['date']}, the fixture is `{manifest['fixture']}`, and model-backed commands ran through the `{manifest['provider']}` agent provider. A different run can answer differently.{rerun_note(manifest)}",
        "",
        "| Run | Command | Exit | Seconds | Output |",
        "| --- | --- | --- | --- | --- |",
    ]
    for run in manifest["runs"]:
        output = run.get("output")
        link = f"[{output}](../site/artifacts/{output})" if output else "none, the run failed"
        lines.append(
            f"| {cell(run['name'])} | `{cell(run['command'])}` | {run['exit_code']} | {float(run['seconds']):.1f} | {link} |"
        )
    for run in manifest["runs"]:
        name = run["name"]
        data = runs[name]["data"]
        output = run.get("output")
        lines += [
            "",
            f"## {name}",
            "",
            f"- Command: `{run['command']}`",
            f"- Run on {recorded['date']}, {float(run['seconds']):.1f} s, exit {run['exit_code']}",
        ]
        lines.append(f"- Result: {key_figures(name, data if isinstance(data, dict) else None)}")
        if output:
            lines.append(f"- Output: [{output}](../site/artifacts/{output})")
            after = run.get("after")
            if after:
                lines.append(f"- Written file: [{after}](../site/artifacts/{after})")
        else:
            lines.append(f"- Error: {run.get('stderr') or '(no message)'}")
    return "\n".join(lines) + "\n"


INDEX_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-src 'self'; "
    "connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)


# endregion

# region: course.html


def scope_selectors(prelude: str, scope: str) -> str:
    scoped = []
    for selector in prelude.split(","):
        selector = selector.strip()
        if selector in {":root", "html", "body"}:
            scoped.append(scope)
        elif selector == "main":
            scoped.append(f"{scope} .course-main")
        else:
            scoped.append(f"{scope} {selector}")
    return ",".join(scoped)


def scope_css(css: str, scope: str) -> str:
    """Every rule prefixed with the scope; colour-scheme overrides dropped, since the family has one paper."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out: list[str] = []
    index = 0
    while True:
        opening = css.find("{", index)
        if opening < 0:
            break
        prelude = css[index:opening].strip()
        depth, cursor = 1, opening + 1
        while cursor < len(css) and depth:
            depth += {"{": 1, "}": -1}.get(css[cursor], 0)
            cursor += 1
        body = css[opening + 1 : cursor - 1]
        index = cursor
        if "prefers-color-scheme" in prelude or "data-theme" in prelude:
            continue
        if prelude.startswith(("@media", "@supports")):
            out.append(prelude + "{" + scope_css(body, scope) + "}")
        elif prelude.startswith("@"):
            out.append(prelude + "{" + body + "}")
        else:
            out.append(scope_selectors(prelude, scope) + "{" + " ".join(body.split()) + "}")
    return "\n".join(out) + "\n"


# Where the family theme's own class names collide with the course's, the course keeps its look.
COURSE_FITTING = """
/* Fitting: the family theme shares a few class names with the course; the course's rules win inside .course. */
.course { padding-top: 0; }
.course .hero { padding-top: 0; }
.course .note { font-size: 17px !important; margin-top: 28px !important; color: inherit; }
.course .pr .copy:hover { background: var(--ink); color: var(--paper); }
.course .font-note { margin-top: 14px; max-width: 36em; font-size: 15px; color: var(--muted); }
"""

FONT_NOTE = (
    '<p class="font-note">Shown without the web fonts the course loads online. This site loads nothing from '
    "outside, so the default card's Instrument Serif headline falls back to a system serif and the rest of the page "
    "to Arial, Georgia and the system monospace.</p>\n"
)


def course_parts() -> dict[str, str]:
    """The course page split into the pieces the site needs: style, script, body and its description."""
    source = COURSE.read_text(encoding="utf-8")
    style = must(re.search(r"<style>\n(.*?)\n</style>", source, re.S), "the course stylesheet").group(1)
    script = must(re.search(r"<script>\n(.*?)\n</script>", source, re.S), "the course script").group(1)
    body = must(re.search(r"<body>\n(.*?)\n<script>", source, re.S), "the course body").group(1)
    description = must(
        re.search(r'<meta name="description" content="([^"]*)">', source), "the course description"
    ).group(1)
    title = must(re.search(r"<title>([^<]*)</title>", source), "the course title").group(1)
    return {"style": style, "script": script, "body": body, "description": description, "title": title}


def course_body(body: str) -> str:
    if body.count('<main id="top">') != 1 or body.count("</main>") != 1 or body.count('<div class="lab">') != 1:
        raise ValueError("The course body changed shape; update the course transformation")
    body = body.replace('<main id="top">', '<div id="top" class="course-main">').replace("</main>", "</div>")
    return body.replace('  <div class="lab">', FONT_NOTE + '  <div class="lab">')


def shell(
    title: str, description: str, csp: str, body: str, info: dict[str, str], current: str, extra_head: str = ""
) -> str:
    """The family masthead and footer around a page body."""
    repository = escape(info["repository"])
    links = (
        ("index.html#outputs", "Outputs"),
        ("outputs.html", "Full outputs"),
        ("index.html#install", "Install"),
        ("course.html", "Course"),
        (repository, "GitHub"),
    )
    nav = "".join(
        f'<a href="{href}"' + (' aria-current="page"' if href == current else "") + f">{label}</a>"
        for href, label in links
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
<meta name="theme-color" content="#f6f4ee">
<link rel="icon" type="image/svg+xml" href="assets/favicon.svg">
<link rel="stylesheet" href="assets/family.css">
<link rel="stylesheet" href="assets/style.css">
{extra_head}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="masthead"><div class="wrap">
<a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true"></span><span class="brand-name">Amplifier Smart Tools</span></a>
<nav class="nav" aria-label="Main navigation">{nav}</nav>
</div></header>
{body}
<footer class="site-footer"><div class="wrap footer-grid"><div><strong class="footer-brand">Amplifier Smart Tools</strong><p>Unslopper v{escape(info["version"])} is an independent Smart Tool built to the Amplifier Smart Tools specification. The family theme is MIT licensed by Microsoft; the tool, these pages and the recorded outputs are the repository's own.</p></div><nav class="footer-links" aria-label="Footer"><a href="outputs.html">Full outputs</a><a href="course.html">Course</a><a href="{repository}">GitHub</a><a href="assets/family-LICENSE.txt">Theme license</a><a href="#main">Back to top</a></nav></div></footer>
</body>
</html>
"""


COURSE_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; style-src-attr 'unsafe-inline'; img-src 'self'; "
    "connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)


def course_page(parts: dict[str, str], info: dict[str, str]) -> str:
    body = f'<main id="main" class="course">\n{course_body(parts["body"])}\n</main>'
    head = '<link rel="stylesheet" href="assets/course.css">\n<script src="assets/course.js" defer></script>\n'
    return shell(
        f"{parts['title']}: the course behind Unslopper",
        parts["description"],
        COURSE_CSP,
        body,
        info,
        "course.html",
        head,
    )


# endregion

# region: Build


def copy_tree(source: Path, target: Path, keep: str = "*") -> int:
    count = 0
    for path in sorted(source.rglob(keep)):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not copied: {path}")
        if path.is_file() and not any(
            part.startswith(".") or part == "__pycache__" for part in path.relative_to(source).parts
        ):
            destination = target / path.relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
            count += 1
    return count


def skill_files() -> list[Path]:
    return sorted(path for path in SKILLS.rglob("*") if path.is_file() and not path.name.startswith("."))


def write_zip(target: Path) -> str:
    """The whole skills/ directory as one reproducible zip; fixed timestamps keep the sha256 stable."""
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in skill_files():
            info = zipfile.ZipInfo(f"skills/{path.relative_to(SKILLS).as_posix()}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return hashlib.sha256(target.read_bytes()).hexdigest()


def build(output: Path) -> None:
    output = output.resolve()
    # A builder must never erase an arbitrary directory.
    if output != ROOT / "_site":
        raise ValueError("Build output must be this checkout's _site directory")
    if output.is_symlink():
        raise ValueError("Build output must not be a symlink")
    config = json.loads((SITE / "site.json").read_text(encoding="utf-8"))
    info = project()
    recorded = artifacts()
    runs = recorded["runs"]
    if not isinstance(runs, dict):
        raise ValueError("Artifacts manifest has an unexpected shape")
    parts = course_parts()
    course = course_counts(parts["script"])
    knowledge = knowledge_counts()
    for key, value in knowledge.items():
        if course[key] != value:
            raise ValueError(f"The course page has {course[key]} {key} but knowledge.py has {value}")
    # The Markdown record lives in docs/ beside the other references and is regenerated, never edited.
    markdown = recorded_outputs_markdown(recorded)
    if not RECORDED_DOC.is_file() or RECORDED_DOC.read_text(encoding="utf-8") != markdown:
        RECORDED_DOC.write_text(markdown, encoding="utf-8")
    if output.exists():
        shutil.rmtree(output)
    assets = output / "assets"
    frames_dir = output / "frames"
    assets.mkdir(parents=True)
    frames_dir.mkdir()
    zip_sha = write_zip(output / ZIP_NAME)
    (output / f"{ZIP_NAME}.sha256").write_text(f"{zip_sha}  {ZIP_NAME}\n", encoding="utf-8")
    frames_html, articles, frames = outputs_block(recorded)
    (output / "index.html").write_text(index_page(config, info, recorded, frames_html), encoding="utf-8")
    (output / "outputs.html").write_text(outputs_page(info, recorded, frames_html, articles, zip_sha), encoding="utf-8")
    for name, document in frames.items():
        (frames_dir / name).write_text(document, encoding="utf-8")
    (output / "course.html").write_text(course_page(parts, info), encoding="utf-8")
    (assets / "course.css").write_text(scope_css(parts["style"], ".course") + COURSE_FITTING, encoding="utf-8")
    (assets / "course.js").write_text(parts["script"] + "\n", encoding="utf-8")
    (assets / "artifacts.css").write_text(artifacts_css(runs), encoding="utf-8")
    texture = runs.get("texture", {}).get("data")
    if isinstance(texture, dict):
        kind, _, code = texture_code(texture)
        if kind == "canvas":
            (assets / "texture-artifact.js").write_text(code + "\n", encoding="utf-8")
    for source, target in (
        ("site/theme/style.css", "family.css"),
        ("site/style.css", "style.css"),
        ("site/site.js", "site.js"),
        ("site/theme/LICENSE", "family-LICENSE.txt"),
    ):
        shutil.copy2(ROOT / source, assets / target)
    copy_tree(SITE / "assets", assets)
    copied = copy_tree(ARTIFACTS, output / "artifacts") + copy_tree(SKILLS, output / "skills")
    copied += copy_tree(ROOT / "docs", output / "docs", "*.md")
    for name in DOWNLOADS:
        source = ROOT / name
        if source.is_file():
            (output / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, output / name)
            copied += 1
    (output / ".nojekyll").touch()
    print(
        f"Built {output}: {len(runs)} recorded runs, {len(frames)} frames, {len(skill_files())} skill files in {ZIP_NAME} "
        f"(sha256 {zip_sha}), {copied} downloads; course counts {course}; {RECORDED_DOC.relative_to(ROOT)} current"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    build(parser.parse_args().output)


# endregion
