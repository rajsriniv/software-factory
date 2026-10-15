"""Execute a test command and translate its fresh JUnit report into TDD evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


def execute(command: list[str], report: Path, output: Path, timeout: int = 1800) -> int:
    if not command or report.exists() or output.exists():
        raise ValueError("Command required; report and evidence must be fresh paths")
    completed = subprocess.run(
        [arg.replace("{junit}", str(report)) for arg in command], check=False, timeout=timeout
    )
    root = ET.parse(report).getroot()
    tests = list(root.iter("testcase"))
    passing, failures = [], []
    errors = 0
    assertion_only = True
    for test in tests:
        name = test.get("classname", "") + "::" + test.get("name", "")
        failure = test.find("failure")
        if test.find("error") is not None:
            errors += 1
        elif failure is not None:
            failures.append(name)
            message = " ".join(
                (failure.get("type", ""), failure.get("message", ""), failure.text or "")
            )
            assertion_only = assertion_only and (
                "AssertionError" in message or "AssertionFailedError" in message
            )
        elif test.find("skipped") is None:
            passing.append(name)
    # Missing/empty reports, collection failures and skipped-only runs cannot turn green.
    passed = completed.returncode == 0 and bool(passing) and not failures and not errors
    red = completed.returncode == 1 and bool(failures) and assertion_only and not errors
    data = {
        "summary": "Executed JUnit test results",
        "passed": passed,
        "failure_kind": "assertion" if red else "execution",
        "failing_tests": failures,
        "passing_tests": passing,
        "errors": errors,
        "exit_code": completed.returncode,
        "test_report": {
            "path": str(report.resolve()),
            "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2) + "\n")
    return 0 if passed else (1 if red else 2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--output", type=Path, default=os.environ.get("FACTORY_EVIDENCE_OUTPUT"))
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if args.output is None:
        parser.error("--output or FACTORY_EVIDENCE_OUTPUT required")
    report = args.report or args.output.with_suffix(".xml")
    report.parent.mkdir(parents=True, exist_ok=True)
    try:
        raise SystemExit(execute(command, report, args.output, args.timeout))
    except (ValueError, OSError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
