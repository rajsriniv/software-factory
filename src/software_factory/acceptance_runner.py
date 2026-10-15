"""Run configured E2E tests and bind criterion coverage to their fresh JUnit report."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from . import evidence
from .test_receipt import execute


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    output = Path(os.environ["FACTORY_EVIDENCE_OUTPUT"])
    packet = json.loads(Path(os.environ["FACTORY_CONTEXT"]).read_text())
    design = next(e for e in packet["prior_outputs"] if e["phase"] == "test-design")
    evidence.artifact({"path": design["output"], "sha256": design["sha256"]}, Path.cwd())
    mapping = json.loads(Path(design["output"]).read_text())["test_map"]
    report = output.with_suffix(".xml")
    test_output = output.with_suffix(".tests.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    code = execute(command, report, test_output)
    receipt = json.loads(test_output.read_text())
    coverage = {
        criterion: [{**receipt["test_report"], "test_ids": tests}]
        for criterion, tests in mapping.items()
    }
    expected = evidence.acceptance_ids(packet["specification"], Path.cwd())
    if code == 0:
        evidence.coverage(coverage, expected, Path.cwd())
    output.write_text(
        json.dumps(
            {
                "summary": "Executed E2E acceptance suite",
                "passed": code == 0,
                "input_sha256": os.environ["FACTORY_INPUT_SHA256"],
                "coverage": coverage,
            },
            indent=2,
        )
        + "\n"
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
