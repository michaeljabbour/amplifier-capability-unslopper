#!/usr/bin/env python3
"""Check the built site: links, structure, offline assets, exact downloads, and fidelity to the sources it renders.

Fails on broken or root-relative links, missing anchors, duplicate ids, more or less than one h1, images without
alternatives, anything loaded from outside, drift between the page and the recorded artifacts, the skills or the
library's own tables, and a scan score above 2 on index.html when the tool can run.
"""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build import (  # noqa: E402
    ARTIFACTS,
    COURSE_FITTING,
    DOWNLOADS,
    FONT_NOTE,
    RECORDED_DOC,
    SITE,
    SKILLS,
    ZIP_NAME,
    capabilities,
    course_counts,
    course_parts,
    escape,
    frame_document,
    knowledge_counts,
    manifest_description,
    non_goal_heads,
    recorded_outputs_markdown,
    routes,
    scope_css,
    skill_files,
    skills,
    texture_code,
    tutor_frame,
)
from build import artifacts as recorded_artifacts  # noqa: E402

MAX_SCORE = 2


class CheckError(AssertionError):
    """A site check that did not hold."""


def require(condition: object, message: str) -> None:
    if not condition:
        raise CheckError(message)


RUNTIME_TAGS = {"script", "img", "source", "track", "iframe", "video", "audio", "embed", "object"}
COURSE_IDS = (
    "terms",
    "slopGroups",
    "cardSlop",
    "cardClean",
    "btnSlop",
    "btnClean",
    "fixGroups",
    "textures",
    "auditForm",
    "score",
    "verdict",
    "todo",
    "resetAudit",
    "prompts",
)


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.duplicates: list[str] = []
        self.links: list[str] = []
        self.remote_runtime: list[str] = []
        self.lang = ""
        self.h1 = 0
        self.images_without_alt: list[str | None] = []
        self.inline_scripts = 0
        self.style_elements = 0
        self.style_attributes = 0
        self.iframes: list[dict[str, str | None]] = []
        self.attributes: dict[str, list[str]] = {
            "data-artifact": [],
            "data-capability": [],
            "data-route": [],
            "data-skill": [],
            "data-row": [],
        }
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        if tag == "html":
            self.lang = found.get("lang") or ""
        if tag == "h1":
            self.h1 += 1
        identifier = found.get("id")
        if identifier:
            if identifier in self.ids:
                self.duplicates.append(identifier)
            self.ids.add(identifier)
        for key in ("href", "src", "poster"):
            value = found.get(key)
            if value:
                self.links.append(value)
                is_stylesheet = tag == "link" and (found.get("rel") or "").split() == ["stylesheet"]
                if (tag in RUNTIME_TAGS or is_stylesheet or tag == "link") and (
                    urlsplit(value).scheme or urlsplit(value).netloc
                ):
                    self.remote_runtime.append(value)
        if tag == "img" and "alt" not in found:
            self.images_without_alt.append(found.get("src"))
        if tag == "script" and not found.get("src"):
            self.inline_scripts += 1
        if tag == "style":
            self.style_elements += 1
        if "style" in found:
            self.style_attributes += 1
        if tag == "iframe":
            self.iframes.append(found)
        for name in self.attributes:
            if found.get(name):
                self.attributes[name].append(str(found[name]))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def parse(path: Path) -> Page:
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def check_links(pages: dict[Path, Page], output: Path) -> int:
    count = 0
    for path, page in pages.items():
        for ref in page.links:
            parsed = urlsplit(ref)
            if parsed.scheme or parsed.netloc:
                require(parsed.scheme == "https", f"Unexpected external protocol in {path.name}: {ref}")
                continue
            require(not parsed.path.startswith("/"), f"Root-relative link breaks subpath hosting: {ref}")
            target = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            require(target.is_relative_to(output), f"Link escapes the site: {ref}")
            require(target.is_file(), f"Missing link target in {path.name}: {ref}")
            if parsed.fragment and target.suffix == ".html":
                require(target in pages, f"Fragment into an unchecked page: {ref}")
                require(unquote(parsed.fragment) in pages[target].ids, f"Missing anchor in {path.name}: {ref}")
            count += 1
    return count


def check_markdown_links(output: Path) -> int:
    """Markdown downloads resolve inside the site; the generated record is a repository document and resolves there."""
    count = 0
    for path in output.rglob("*.md"):
        relative = path.relative_to(output)
        base, root = (ROOT / relative, ROOT) if relative == RECORDED_DOC.relative_to(ROOT) else (path, output)
        for ref in re.findall(r"!?\[[^\]]*\]\(([^)\s]+)\)", path.read_text(encoding="utf-8")):
            parsed = urlsplit(ref)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (base.parent / unquote(parsed.path)).resolve()
            require(target.is_relative_to(root) and target.exists(), f"Missing Markdown target in {relative}: {ref}")
            count += 1
    return count


def check_downloads(output: Path) -> int:
    """Everything offered as a file is byte for byte the source it came from."""
    count = 0
    pairs: list[tuple[Path, Path]] = []
    pairs += [
        (path, output / "artifacts" / path.relative_to(ARTIFACTS))
        for path in sorted(ARTIFACTS.rglob("*"))
        if path.is_file()
    ]
    pairs += [(path, output / "skills" / path.relative_to(SKILLS)) for path in skill_files()]
    pairs += [
        (path, output / "docs" / path.relative_to(ROOT / "docs")) for path in sorted((ROOT / "docs").rglob("*.md"))
    ]
    pairs += [(ROOT / name, output / name) for name in DOWNLOADS if (ROOT / name).is_file()]
    pairs += [
        (SITE / "theme" / "style.css", output / "assets" / "family.css"),
        (SITE / "theme" / "LICENSE", output / "assets" / "family-LICENSE.txt"),
    ]
    for source, copy in pairs:
        require(copy.is_file(), f"Download missing: {copy.relative_to(output)}")
        require(
            copy.read_bytes() == source.read_bytes(), f"Download differs from its source: {copy.relative_to(output)}"
        )
        count += 1
    for path in output.rglob("*"):
        require(not path.is_symlink(), f"Symlink in the built site: {path}")
    require((output / ".nojekyll").is_file(), "Missing .nojekyll")
    return count


def check_zip(output: Path) -> str:
    files = skill_files()
    with ZipFile(output / ZIP_NAME) as archive:
        expected = [f"skills/{path.relative_to(SKILLS).as_posix()}" for path in files]
        require(archive.namelist() == expected, "Zip membership differs from the skills directory")
        require(archive.testzip() is None, "Zip is corrupt")
        for path, name in zip(files, expected, strict=True):
            require(archive.read(name) == path.read_bytes(), f"Zip content differs: {name}")
    digest = hashlib.sha256((output / ZIP_NAME).read_bytes()).hexdigest()
    require(
        (output / f"{ZIP_NAME}.sha256").read_text(encoding="utf-8") == f"{digest}  {ZIP_NAME}\n",
        "sha256 file differs from the zip",
    )
    return digest


def check_assets(output: Path) -> None:
    for name in ("family.css", "style.css", "artifacts.css", "course.css"):
        css = (output / "assets" / name).read_text(encoding="utf-8")
        require(not re.search(r"@import|url\(\s*['\"]?(?:https?:)?//", css), f"External CSS runtime asset in {name}")
    for name in ("site.js", "course.js", "texture-artifact.js"):
        path = output / "assets" / name
        if path.is_file():
            js = path.read_text(encoding="utf-8")
            require(
                not re.search(
                    r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|localStorage|sessionStorage|indexedDB)\b|\bimport\s*\(",
                    js,
                ),
                f"Network or storage code in {name}",
            )
    theme = json.loads((SITE / "site.json").read_text(encoding="utf-8"))["theme"]
    family = (output / "assets" / "family.css").read_text(encoding="utf-8")
    for token in ("paper", "ink", "muted", "line", "gold", "wash"):
        value = re.search(r"--" + token + r":\s*([^;]+);", family)
        require(value and value.group(1).strip() == theme[token], f"Family token differs: {token}")
    require(f"v{theme['version']}" in family.splitlines()[0], "Family theme version differs from site.json")
    style = (output / "assets" / "style.css").read_text(encoding="utf-8")
    require(f"--accent: {theme['accent']}" in style, "The accent in style.css differs from site.json")
    require("gradient(" not in style, "No gradients on the tool's own page")


def check_chrome(name: str, page: Page, raw: str) -> None:
    require(
        "default-src 'self'" in raw
        and "script-src 'self'" in raw
        and "style-src 'self'" in raw
        and "connect-src 'none'" in raw,
        f"{name} must carry the strict policy",
    )
    require(page.inline_scripts == 0, f"{name} must not carry inline scripts")
    require(page.style_elements == 0 and page.style_attributes == 0, f"{name} must not carry inline style")
    require(
        'class="brand-name">Amplifier Smart Tools' in raw and 'class="footer-brand">Amplifier Smart Tools' in raw,
        f"{name} is missing the family masthead and footer identity",
    )
    require("<hr" not in raw, f"No dividers on {name}")
    for frame in page.iframes:
        require("sandbox" in frame and frame.get("title"), f"Frames need sandbox and a title in {name}: {frame}")


def check_index(output: Path, page: Page, raw: str) -> int:
    """The short front page: scores, one row per run, every capability named, one primary action."""
    text = " ".join(page.text)
    check_chrome("index.html", page, raw)
    require(escape(manifest_description()) in raw, "Manifest description differs")
    for row in capabilities():
        require(row.name in page.attributes["data-capability"], f"Capability not named on index.html: {row.name}")
    for head in non_goal_heads():
        require(escape(head).lower() in raw.lower(), f"Non-goal missing from index.html: {head}")
    for phrase in ("Unedited outputs of one run", "A different run can answer differently", "agent provider"):
        require(phrase in text, f"Honesty note missing from index.html: {phrase}")
    require(raw.count('class="button primary"') == 1, "One primary call to action")
    require(
        'href="outputs.html"' in raw and "Read the full recorded outputs" in text,
        "index.html must link to the full outputs",
    )
    require(f'href="{ZIP_NAME}"' in raw, "index.html must link to the skills download")
    manifest = json.loads((ARTIFACTS / "manifest.json").read_text(encoding="utf-8"))
    for run in manifest["runs"]:
        name = run["name"]
        require(name in page.attributes["data-row"], f"No row on index.html for {name}")
        block = re.search(
            rf'<li class="row" data-row="{re.escape(name)}">.*?<p class="row-links">.*?</p></li>', raw, re.S
        )
        if block is None:
            raise CheckError(f"Row block missing: {name}")
        require(
            f'href="outputs.html#artifact-{name}"' in block.group(0), f"Row does not link to the full output: {name}"
        )
        if run.get("output"):
            require(f'href="artifacts/{run["output"]}"' in block.group(0), f"Row does not link to the JSON: {name}")
        else:
            require("Failed" in block.group(0), f"Failed run not reported on index.html: {name}")
    return len(manifest["runs"])


def check_outputs(page: Page, raw: str) -> None:
    """The full page: every route and skill rendered, the manifest table present."""
    check_chrome("outputs.html", page, raw)
    for route in routes():
        require(route["capability"] in page.attributes["data-route"], f"Route missing: {route['capability']}")
        for key in ("when", "skill", "command"):
            require(escape(route[key]) in raw, f"Route text differs for {route['capability']}: {key}")
    for skill in skills():
        require(skill.name in page.attributes["data-skill"], f"Skill not listed: {skill.name}")
        require(escape(skill.description) in raw, f"Skill description differs: {skill.name}")
        for file in skill.files:
            require(f'href="skills/{file}"' in raw, f"Skill file not linked: {file}")
    require('<table class="manifest">' in raw, "Manifest table missing from outputs.html")
    require("A different run can answer differently" in " ".join(page.text), "Honesty note missing from outputs.html")


def check_recorded_doc() -> None:
    require(RECORDED_DOC.is_file(), f"{RECORDED_DOC.relative_to(ROOT)} is missing; run scripts/build.py")
    require(
        RECORDED_DOC.read_text(encoding="utf-8") == recorded_outputs_markdown(recorded_artifacts()),
        f"{RECORDED_DOC.relative_to(ROOT)} is stale; run scripts/build.py",
    )


def check_artifacts(output: Path, page: Page, raw: str, index_raw: str) -> int:
    manifest = json.loads((ARTIFACTS / "manifest.json").read_text(encoding="utf-8"))
    date = manifest["captured"][:10]
    require(
        escape(manifest["note"]) in raw and date in raw and manifest["provider"] in raw,
        "Run note must quote the manifest",
    )
    checked = 0
    for run in manifest["runs"]:
        name = run["name"]
        require(name in page.attributes["data-artifact"], f"Artifact not rendered: {name}")
        block = re.search(rf'<article class="artifact" id="artifact-{re.escape(name)}".*?</article>', raw, re.S)
        if block is None:
            raise CheckError(f"Artifact block missing: {name}")
        article = block.group(0)
        require(escape(run["command"]) in article, f"Command differs: {name}")
        require(
            f"{date}, {float(run['seconds']):.1f} s, exit {run['exit_code']}" in article, f"Run label differs: {name}"
        )
        if not run.get("output"):
            require(
                "This run failed" in article and escape(run["stderr"]) in article,
                f"Failed run not reported honestly: {name}",
            )
            checked += 1
            continue
        data = json.loads((ARTIFACTS / run["output"]).read_text(encoding="utf-8"))
        require(f'href="artifacts/{run["output"]}"' in article, f"Raw output not linked: {name}")
        if name == "scan":
            require(f'<b class="num">{data["score"]}</b>' in article, "Score not rendered as a figure")
            require(escape(data["verdict"]) in article, "Verdict missing")
            for hit in data["hits"]:
                require(escape(hit["indicator"]) in article, f"Scan hit missing: {hit['indicator']}")
                for item in hit["evidence"]:
                    require(escape(item["detail"]) in article, f"Scan evidence missing: {item['detail']}")
        elif name == "audit":
            require(escape(data["summary"]) in article, "Audit summary missing")
            require(f'<b class="num">{data["score"]}</b>' in article, "Score not rendered as a figure")
            for finding in data["findings"]:
                require(escape(finding["rationale"]) in article, f"Audit finding missing: {finding['indicator']}")
        elif name in ("unslop", "antislop"):
            require(escape(data["diff"].splitlines()[0]) in article, f"Diff missing: {name}")
            after = run.get("after")
            require(
                after
                and (output / "frames" / after).read_text(encoding="utf-8")
                == frame_document((ARTIFACTS / after).read_text(encoding="utf-8"), f"site/artifacts/{after}"),
                f"Frame differs: {after}",
            )
            require(
                f'src="frames/{after}"' in raw and f'src="frames/{after}"' in index_raw, f"Frame not shown: {after}"
            )
            if name == "unslop":
                for change in data["plan"]:
                    require(escape(change["change"]) in article, f"Plan change missing: {change['fix']}")
            else:
                for step in data["steps"]:
                    require(escape(step["note"]) in article, f"Pipeline step missing: {step['name']}")
                for line in str(data["summary"]).splitlines():
                    require(escape(line) in article, "Antislop summary line missing")
        elif name == "direct":
            for direction in data["directions"]:
                for colour in direction["palette"]:
                    require(escape(colour["hex"]) in article, "Palette hex missing")
                    require(escape(colour["oklch"]) in article, "Palette OKLCH missing")
                require(escape(direction["css"]) in article, "Direction CSS tokens missing")
                require(escape(direction["scene"]) in article, "Direction scene missing")
                require(str(direction["contrast"]["ratio"]) in article, "Direction contrast ratio missing")
        elif name == "texture":
            kind, canvas, code = texture_code(data)
            require(escape(data["contrast"]) in article, "Texture contrast note missing")
            for recommendation in data["recommendations"]:
                require(escape(recommendation["why"]) in article, "Texture recommendation missing")
            if kind == "canvas":
                require(
                    (output / "assets" / "texture-artifact.js").read_text(encoding="utf-8") == code + "\n",
                    "Texture script differs from the artifact",
                )
                require(re.sub(r"\s*>$", "", canvas) in article, "Texture canvas differs from the artifact")
            else:
                require(
                    code in (output / "assets" / "artifacts.css").read_text(encoding="utf-8"),
                    "Texture CSS differs from the artifact",
                )
        elif name == "tutor":
            require(escape(data["prompt_line"]) in article, "Tutor prompt line missing")
            require(
                (output / "frames" / "tutor-demo.html").read_text(encoding="utf-8")
                == tutor_frame(data["demo_html"], data["term"]),
                "Tutor demo frame differs from the artifact",
            )
        elif name == "contrast":
            require(str(data["ratio"]) in article, "Contrast ratio missing")
            require(escape(data["foreground"]) in article, "Contrast foreground missing")
        elif name == "route":
            require(escape(data["reason"]) in article, "Route reason missing")
            require(escape(data["capability"]) in article, "Route capability missing")
        elif name == "reference-indicators":
            for item in data["items"]:
                require(escape(item["description"]) in article, f"Indicator missing: {item['name']}")
        checked += 1
    require(
        (output / "frames" / "before.html").read_text(encoding="utf-8")
        == frame_document((ARTIFACTS / "before.html").read_text(encoding="utf-8"), "site/artifacts/before.html"),
        "Before frame differs from the artifact",
    )
    return checked


def check_course(output: Path, page: Page, raw: str) -> dict[str, int]:
    parts = course_parts()
    require(
        "fonts.googleapis.com" not in raw and "fonts.gstatic.com" not in raw, "The course must not load remote fonts"
    )
    require(
        (output / "assets" / "course.js").read_text(encoding="utf-8") == parts["script"] + "\n",
        "course.js differs from the course source",
    )
    require(
        (output / "assets" / "course.css").read_text(encoding="utf-8")
        == scope_css(parts["style"], ".course") + COURSE_FITTING,
        "course.css differs from the scoped course source",
    )
    css = re.sub(r"/\*.*?\*/", "", (output / "assets" / "course.css").read_text(encoding="utf-8"), flags=re.S)
    for prelude in re.findall(r"([^{}]+)\{", css):
        if not prelude.strip().startswith("@"):
            for selector in prelude.split(","):
                require(selector.strip().startswith(".course"), f"Unscoped course selector: {selector.strip()}")
    for identifier in COURSE_IDS:
        require(identifier in page.ids, f"Course hook missing: {identifier}")
    require(FONT_NOTE.strip() in raw, "The course must say the demo card is shown without its web font")
    require(
        "style-src-attr 'unsafe-inline'" in raw and "script-src 'self'" in raw,
        "Course policy must allow its demos' inline style attributes and nothing more",
    )
    require(
        page.inline_scripts == 0 and page.style_elements == 0,
        "course.html must not carry inline script or style elements",
    )
    counts = course_counts(parts["script"])
    require(
        counts == {"terms": 20, "indicators": 20, "fixes": 20, "textures": 22, "prompts": 6},
        f"Course counts changed: {counts}",
    )
    knowledge = knowledge_counts()
    for key, value in knowledge.items():
        require(counts[key] == value, f"Course has {counts[key]} {key}, knowledge.py has {value}")
    model_backed = sum(1 for row in capabilities() if row.model_backed)
    require(
        counts["prompts"] == model_backed,
        f"{counts['prompts']} course prompts but {model_backed} model-backed capabilities",
    )
    return counts


def dogfood(output: Path) -> str:
    """Scan index.html with the tool itself; course.html is exempt because it embeds the slop card on purpose."""
    if shutil.which("unslopper"):
        command = ["unslopper", "scan", str(output / "index.html")]
    elif shutil.which("uv"):
        command = ["uv", "run", "unslopper", "scan", str(output / "index.html")]
    else:
        return "Dogfood scan: skipped, neither unslopper nor uv is on PATH"
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300, check=False)
    require(completed.returncode == 0, f"unslopper scan failed: {completed.stderr.strip()}")
    report = json.loads(completed.stdout)
    hits = "; ".join(f"{hit['indicator']} ({len(hit['evidence'])} evidence)" for hit in report["hits"]) or "none"
    require(report["score"] <= MAX_SCORE, f"index.html scans at {report['score']} of 20, above {MAX_SCORE}: {hits}")
    return f"Dogfood scan: index.html scores {report['score']} of 20 ({report['verdict']}); hits: {hits}. course.html is exempt: it embeds the slop card on purpose"


def check(output: Path) -> None:
    output = output.resolve()
    pages: dict[Path, Page] = {}
    for path in sorted(output.rglob("*.html")):
        relative = path.relative_to(output)
        if relative.parts[0] in {"artifacts", "docs"}:
            continue  # verbatim downloads, compared to their sources below
        page = parse(path)
        require(page.lang == "en", f"Expected lang=en in {relative}")
        require(not page.duplicates, f"Duplicate ids in {relative}: {page.duplicates}")
        require(not page.remote_runtime, f"External runtime dependency in {relative}: {page.remote_runtime}")
        require(not page.images_without_alt, f"Images without alt in {relative}: {page.images_without_alt}")
        if relative.parts[0] != "frames":
            require(page.h1 == 1, f"Expected exactly one h1 in {relative}, found {page.h1}")
        pages[path] = page
    index, outputs_page, course = output / "index.html", output / "outputs.html", output / "course.html"
    require(
        index in pages and outputs_page in pages and course in pages,
        "index.html, outputs.html and course.html are required",
    )
    links = check_links(pages, output)
    markdown_links = check_markdown_links(output)
    downloads = check_downloads(output)
    digest = check_zip(output)
    check_assets(output)
    index_raw = index.read_text(encoding="utf-8")
    outputs_raw = outputs_page.read_text(encoding="utf-8")
    rows = check_index(output, pages[index], index_raw)
    check_outputs(pages[outputs_page], outputs_raw)
    check_recorded_doc()
    artifacts = check_artifacts(output, pages[outputs_page], outputs_raw, index_raw)
    counts = check_course(output, pages[course], course.read_text(encoding="utf-8"))
    scan_note = dogfood(output)
    frames = sum(1 for path in pages if path.parent.name == "frames")
    print(
        f"PASS: {len(pages)} HTML documents ({frames} frames); {links} local links and fragments; {markdown_links} Markdown targets"
    )
    print(
        f"PASS: {downloads} downloads byte-identical to their sources; {len(skill_files())} skill files in {ZIP_NAME}, sha256 {digest}"
    )
    print(
        f"PASS: {artifacts} recorded runs rendered in full on outputs.html and as {rows} rows on index.html; "
        f"{len(capabilities())} capabilities named on index.html, {len(routes())} routes and {len(skills())} skills on outputs.html; "
        f"{RECORDED_DOC.relative_to(ROOT)} current"
    )
    print(
        f"PASS: course.html generated from docs/unslop-school.html with scoped CSS; counts {counts} match knowledge.py"
    )
    print(
        "PASS: strict policies, no inline script or style, no remote assets, one h1 per page, alt text, sandboxed frames"
    )
    print(scan_note)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    check(parser.parse_args().output)
