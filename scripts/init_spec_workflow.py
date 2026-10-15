#!/usr/bin/env python3
"""Create a local, verification-only workflow; never guess project test/scan commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from software_factory.spec_workflow import phases
from software_factory.workflow import GATES, PHASES, Workflow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument(
        "--checks", type=Path, required=True, help="Operator-reviewed gate command mapping"
    )
    parser.add_argument("--host", choices=("claude", "codex", "copilot"), required=True)
    parser.add_argument("--high-model", required=True)
    parser.add_argument("--low-model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--task-templates",
        type=Path,
        help="Reviewed Java/React/Python task template mapping; overrides the Python default",
    )
    parser.add_argument("--frontend", action="store_true")
    parser.add_argument("--existing-system", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; write a new version instead")
    repo = args.repository.resolve()
    source = args.spec.resolve()
    if not source.is_relative_to(repo):
        parser.error("Specification must be inside the project checkout")
    if args.high_model == args.low_model:
        parser.error("Choose distinct explicit high and low model IDs")
    spec = json.loads(source.read_text())
    checks = json.loads(args.checks.read_text())
    if set(checks) != set(GATES) | {"e2e"}:
        parser.error("Checks file must map every gate plus e2e to actual command argument arrays")
    manifest = {
        "schema_version": 2,
        "assurance": "local",
        "delivery": "verify",
        "requirements": [r["id"] for r in spec["requirements"]],
        "specification": {
            "path": str(source.relative_to(repo)),
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        },
        "frontend": args.frontend,
        "existing_system": args.existing_system,
        "max_attempts": 3,
        "council": ["architect", "security-architect", "architecture-challenger"],
        "task_templates": {},
        "tasks": [],
        "regression_tests": [
            {"path": str(p.relative_to(repo)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in (repo / "tests").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        ],
        "gate_commands": {g: checks[g] for g in GATES},
        "gate_reports": {g: f".factory-state/evidence/gates/{g}.json" for g in GATES},
    }
    roles = {
        "refine": "prompt-refiner",
        "company-context": "company-brain",
        "architecture": "architect",
        "architecture-challenge": "architecture-challenger",
        "security-architecture": "security-architect",
        "architecture-review": "reviewer",
        "plan": "planner",
        "test-design": "sdet",
        "e2e": "sdet",
        "verification": "quality",
        "security": "security",
        "knowledge-proposal": "company-brain",
        "discovery": "reverse-engineer",
        "ux-design": "ux",
        "ui-review": "reviewer",
    }

    def agent(phase: str, role: str, low: bool = False) -> dict[str, object]:
        tier = "low" if low else "high"
        model = args.low_model if low else args.high_model
        return {
            "actor": role,
            "execution": "agent",
            "model": model,
            "tier": tier,
            "command": [
                sys.executable,
                "-m",
                "software_factory.worker",
                "--host",
                args.host,
                "--role",
                role,
                "--model",
                model,
                "--tier",
                tier,
            ],
            "output": f".factory-state/evidence/{phase}/result.json",
        }

    manifest["steps"] = {
        p: agent(p, roles.get(p, p))
        for p in phases(manifest, PHASES)
        if p != "tasks" and not p.endswith("approval")
    }
    manifest["steps"]["e2e"] = {
        "actor": "e2e-runner",
        "execution": "tool",
        "command": [
            sys.executable,
            "-m",
            "software_factory.acceptance_runner",
            "--",
            *checks["e2e"],
        ],
        "output": ".factory-state/evidence/e2e/result.json",
    }
    template = {
        p: agent(
            p,
            {"test": "sdet", "implement": "python", "review": "reviewer"}.get(p, p),
            p == "implement",
        )
        for p in ("test", "red", "implement", "green", "review")
    }
    for phase in ("red", "green"):
        template[phase] = {
            "actor": "test-runner",
            "execution": "tool",
            "command": [
                sys.executable,
                "-m",
                "software_factory.test_receipt",
                "--",
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "--junitxml={junit}",
            ],
            "output": f".factory-state/evidence/{phase}/result.json",
        }
    manifest["task_templates"] = (
        json.loads(args.task_templates.read_text()) if args.task_templates else {"python": template}
    )
    Workflow.validate(manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Created {args.output}. Local verification only; review commands before execution.")


if __name__ == "__main__":
    main()
