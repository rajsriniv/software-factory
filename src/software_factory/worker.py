"""Native client worker adapter. It emits evidence and never advances the controller."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from uuid import uuid4

from .agents import run_agent
from .models import AgentSpec


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", choices=("claude", "codex", "copilot"), required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tier", choices=("high", "low"), required=True)
    args = parser.parse_args()
    required = (
        "FACTORY_PHASE",
        "FACTORY_INPUT_SHA256",
        "FACTORY_EVIDENCE_OUTPUT",
        "FACTORY_CONTEXT",
    )
    if any(not os.environ.get(k) for k in required):
        parser.error("Worker must be launched by the workflow controller")
    if args.model != os.environ.get("FACTORY_EXPECTED_MODEL"):
        parser.error("Worker model differs from the manifest")
    output = Path(os.environ["FACTORY_EVIDENCE_OUTPUT"])
    context = Path(os.environ["FACTORY_CONTEXT"]).read_text()
    instruction = (
        "Use the software-factory skill. Read references/spec-driven-development.md and "
        "references/enforced-workflow.md. Execute only the assigned phase. "
        "Never approve a gate, edit controller state, or deploy without the supplied approved scope. "
        "Do not fabricate tests, tool results, model identity, runtime receipts, or source citations. "
        "Return phase-specific JSON evidence; incomplete work must return passed=false. "
        f"Current phase: {os.environ['FACTORY_PHASE']}. "
        f"Bind input_sha256 to {os.environ['FACTORY_INPUT_SHA256']}. "
        f"Controller packet: {context}"
    )
    spec = AgentSpec(args.role, args.role, args.host, args.model, args.tier, ())
    result = run_agent(spec, [], instruction, Path.cwd(), Path(".factory-state/runs") / uuid4().hex)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result.response, indent=2) + "\n")


if __name__ == "__main__":
    main()
