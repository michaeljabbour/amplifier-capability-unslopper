#!/usr/bin/env python3
"""Record real unslopper outputs for the website, with the command, time and outcome of every run.

Run from the repository root with the claude provider configured. Every capability is exercised against
the lesson 3 slop card fixture or a small brief, and the JSON each printed is kept verbatim under
site/artifacts/, alongside a manifest that says what produced it. Failures are recorded, not hidden.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "artifacts"
FIXTURE = Path("tests") / "fixtures" / "audit-slop-card.html"
# Relative paths throughout, so the recorded commands and labels carry nothing about the machine that ran them.
SCRATCH = Path(".capture")
PROVIDER = ["--agent-provider", "claude"]

RUNS: list[tuple[str, list[str]]] = [
    ("route", ["route", "this landing page looks AI generated, what is wrong with it"]),
    ("reference-indicators", ["reference", "indicators"]),
    ("contrast", ["contrast", "#E8EEF2", "#000412"]),
    ("scan", ["scan", str(FIXTURE)]),
    ("audit", ["audit", str(FIXTURE), *PROVIDER]),
    ("direct", ["direct", "a silent retreat in Kyoto, golden hour on water", "--directions", "1", *PROVIDER]),
    (
        "texture",
        [
            "texture",
            "--name",
            "paper",
            "--subject",
            "a small press publishing poetry",
            "--ground",
            "#EFE8D9",
            "--light",
            "#2A2420",
            "--signal",
            "#B5472A",
            *PROVIDER,
        ],
    ),
    ("tutor", ["tutor", "teach", "--term", "tabular numbers", *PROVIDER]),
]


def run(name: str, argv: list[str], cwd: Path = ROOT) -> dict:
    started = time.monotonic()
    completed = subprocess.run(["uv", "run", "unslopper", *argv], cwd=cwd, capture_output=True, text=True)
    record = {
        "name": name,
        "command": "unslopper " + " ".join(_quote(a) for a in argv),
        "exit_code": completed.returncode,
        "seconds": round(time.monotonic() - started, 1),
        "output": f"{name}.json" if completed.returncode == 0 else None,
        "stderr": completed.stderr.strip()[-2000:] if completed.returncode else "",
    }
    if completed.returncode == 0:
        (OUT / f"{name}.json").write_text(completed.stdout, encoding="utf-8")
    print(f"{name}: exit {completed.returncode} in {record['seconds']}s", file=sys.stderr)
    return record


def _quote(argument: str) -> str:
    return f'"{argument}"' if " " in argument or "#" in argument else argument


def main() -> int:
    only = set(sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / FIXTURE, OUT / "before.html")
    records = [run(name, argv) for name, argv in RUNS if not only or name in only]
    # unslop writes only when asked, so it runs on a copy and the written copy becomes the after artifact.
    scratch = ROOT / SCRATCH
    scratch.mkdir(exist_ok=True)
    try:
        copy = SCRATCH / "card.html"
        shutil.copy2(FIXTURE, copy)
        for name, after in (("unslop", "after.html"), ("antislop", "after-antislop.html")):
            if only and name not in only:
                continue
            shutil.copy2(ROOT / FIXTURE, ROOT / copy)
            record = run(name, [name, str(copy), "--write", *PROVIDER])
            record["command"] = f"unslopper {name} {FIXTURE} --write --agent-provider claude"
            if record["exit_code"] == 0:
                shutil.copy2(ROOT / copy, OUT / after)
                record["after"] = after
            records.append(record)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    if only and (OUT / "manifest.json").is_file():
        # A partial rerun replaces only the runs it repeated, so the other records keep their original date.
        previous = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))["runs"]
        redone = {record["name"] for record in records}
        records = [record for record in previous if record["name"] not in redone] + records
        records.sort(
            key=lambda record: [name for name, _ in [*RUNS, ("unslop", []), ("antislop", [])]].index(record["name"])
        )
    manifest = {
        "captured": datetime.now(UTC).isoformat(timespec="seconds"),
        "partial_rerun": sorted(only) or None,
        "fixture": str(FIXTURE),
        "provider": "claude",
        "note": "Every file here is the unedited stdout of the command named, run once on the date given.",
        "runs": records,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    failed = [r["name"] for r in records if r["exit_code"]]
    print(f"captured {len(records) - len(failed)} of {len(records)} runs" + (f"; failed: {failed}" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
