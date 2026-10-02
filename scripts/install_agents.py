#!/usr/bin/env python3
"""Install the factory skill and host-native role definitions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = {
    "code-mapper": "Map repository structure, calls, data flows and change blast radius; read references/platform-specialists.md. Cite files and revisions; do not invent edges.",
    "devops": "Build secure CI/CD and IaC; read references/platform-specialists.md. Deploy only exact human-approved artifacts and plans with rollback evidence.",
    "network": "Design and provision least-exposure networks, NLB and API Gateway; read references/platform-specialists.md. Verify topology and preserve human approvals.",
    "observability": "Instrument services and build metrics, logs, traces and actionable monitoring; read references/platform-specialists.md. Protect sensitive data and verify signals end to end.",
    "tdd-guide": "Design requirement-based failing tests and guide red-green-refactor; read references/tdd-sdet.md. Never approve implementation.",
    "sdet": "Write and run complete requirement-traceable E2E suites; read references/tdd-sdet.md. Report gaps and never approve your own tests.",
    "prompt-refiner": "Refine intake into traceable requirements; read references/prompt-refiner.md. Preserve intent, expose assumptions, ask consequential questions and never invent facts.",
    "company-brain": "Retrieve persistent company context with citations; read references/company-brain.md. Never invent company facts or grant tools.",
    "product": "Turn requests into measurable, traceable requirements.",
    "architect": "Research and design TOGAF-aligned architecture; do not implement.",
    "security": "Act as security reviewer for code smells, dependencies, blast radius, IAM, network and supply chain; read references/platform-specialists.md.",
    "planner": "Act as implementation planner: decompose approved architecture into bounded dependency-aware tasks with tests, ownership, allowed paths and rollback; read references/platform-specialists.md.",
    "java": "Implement assigned Java backend tasks and tests only.",
    "python": "Implement assigned Python or PySpark backend tasks and tests only.",
    "react": "Implement assigned React frontend tasks and component tests only.",
    "quality": "Run independent contract, integration, accessibility, and E2E verification.",
    "reviewer": "Independently review final artifacts against requirements and evidence.",
    "release": "Assemble provenance and deploy an explicitly approved immutable artifact.",
}
LOW = {"java", "python", "react"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", choices=("claude", "codex", "copilot"), required=True)
    parser.add_argument("--high-model", required=True)
    parser.add_argument("--low-model", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    model_names = {args.high_model.lower(), args.low_model.lower()}
    if args.high_model == args.low_model or model_names & {"auto", "inherit"}:
        parser.error("Use distinct explicit high and low model IDs")
    destination = args.destination.expanduser().resolve()
    files: dict[Path, str] = {}
    for source in (ROOT / "skills/software-factory").rglob("*"):
        if source.is_file():
            relative = source.relative_to(ROOT / "skills/software-factory")
            files[destination / "skills/software-factory" / relative] = source.read_text()
    for role, purpose in ROLES.items():
        model = args.low_model if role in LOW else args.high_model
        name = f"factory-{role}"
        instruction = (
            f"{purpose} Use the software-factory skill and structured messages. "
            "Preserve requirement and artifact hashes. Provide evidence, declare uncertainty, "
            "and never approve your own work. Never bypass hard gates or human approvals."
        )
        if args.host == "codex":
            body = (
                f"name = {json.dumps(name)}\n"
                f"description = {json.dumps(purpose)}\n"
                f"model = {json.dumps(model)}\n"
                f"developer_instructions = {json.dumps(instruction)}\n"
            )
            suffix = ".toml"
        else:
            body = f"---\nname: {name}\ndescription: {purpose}\nmodel: {json.dumps(model)}\n"
            if args.host == "copilot":
                body += "modelPolicy: required\n"
            body += f"---\n\n{instruction}\n"
            suffix = ".md" if args.host == "claude" else ".agent.md"
        files[destination / "agents" / f"{name}{suffix}"] = body
    conflicts = [
        str(path)
        for path, content in files.items()
        if path.exists() and path.read_text() != content
    ]
    if conflicts and not args.replace:
        parser.error("Existing files differ; inspect before --replace: " + ", ".join(conflicts))
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    print(f"Installed software-factory skill and {len(ROLES)} agents in {destination}")


if __name__ == "__main__":
    main()
