"""Compare identical synthetic prose fixtures in two checkouts, offline and without model calls."""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DRIVER = """
import inspect, json, sys
from unslopper import lib
from unslopper.schemas import UnslopperError
cases = json.load(sys.stdin)
supports_prose = 'prose' in inspect.signature(lib.scan).parameters
rows = []
for case in cases:
    try:
        options = {'prose': True} if supports_prose else {}
        report = lib.scan(source=case['text'], **options)
        rows.append({'id': case['id'], 'rules': [found.rule_id for found in report.findings]})
    except UnslopperError as error:
        rows.append({'id': case['id'], 'error': str(error)})
print(json.dumps({'supports_prose': supports_prose, 'rows': rows}))
"""


def measure(checkout: Path, cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Run each checkout's actual facade in isolation, using the same interpreter and dependencies."""
    process = subprocess.run(
        [sys.executable, "-c", DRIVER],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        check=True,
        cwd=checkout,
        env={**os.environ, "PYTHONPATH": str(checkout / "src"), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    result = json.loads(process.stdout)
    fingerprint = hashlib.sha256()
    for path in sorted((checkout / "src").rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            fingerprint.update(path.relative_to(checkout).as_posix().encode())
            fingerprint.update(path.read_bytes())
    rows = result["rows"]
    checked = [row for row in rows if "error" not in row]
    expected = {case["id"]: case for case in cases}
    return {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip(),
        "source_sha256": fingerprint.hexdigest(),
        "supports_prose": result["supports_prose"],
        "samples": len(cases),
        "supported_samples": len(checked),
        "input_errors": len(rows) - len(checked),
        "matching_expectations": sum(
            Counter(row["rules"]) == Counter(expected[row["id"]]["expected"]) for row in checked
        ),
        "positive_samples_flagged": sum(
            bool(row["rules"]) for row in checked if expected[row["id"]]["kind"] == "problem"
        ),
        "legitimate_samples_flagged": sum(
            bool(row["rules"]) for row in checked if expected[row["id"]]["kind"] == "legitimate"
        ),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pairs = json.loads((ROOT / "tests/fixtures/prose-pairs.json").read_text(encoding="utf-8"))
    cases = [
        {"id": f"{index + 1}:{kind}", "kind": kind, "text": pair[kind], "expected": pair[key]}
        for index, pair in enumerate(pairs)
        for kind, key in (("problem", "expected_rules"), ("legitimate", "legitimate_rules"))
    ]
    report: dict[str, Any] = {
        "method": "Identical synthetic fixtures through each checkout's library scan. No model calls or detector scores.",
        "limits": "Main lacks prose mode; its input errors indicate unsupported input, not missed detections. Fixture expectations are narrow editorial regressions, not a validated quality or authorship benchmark. Commit is context; source_sha256 fingerprints the actual source, including uncommitted changes.",
        "fixture_sha256": hashlib.sha256((ROOT / "tests/fixtures/prose-pairs.json").read_bytes()).hexdigest(),
        "baseline": measure(args.baseline.resolve(), cases),
        "feature": measure(ROOT, cases),
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for name in ("baseline", "feature"):
        print(name, json.dumps({key: value for key, value in report[name].items() if key != "rows"}))


if __name__ == "__main__":
    main()
