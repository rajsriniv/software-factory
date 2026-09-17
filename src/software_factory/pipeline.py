from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .models import GateResult, Stage


class TransitionError(ValueError):
    pass


TRANSITIONS: dict[Stage, set[Stage]] = {
    Stage.INTAKE: {Stage.ARCHITECTURE, Stage.BLOCKED},
    Stage.ARCHITECTURE: {Stage.ARCHITECTURE_APPROVAL, Stage.BLOCKED},
    Stage.ARCHITECTURE_APPROVAL: {Stage.PLANNING, Stage.ARCHITECTURE, Stage.BLOCKED},
    Stage.PLANNING: {Stage.IMPLEMENTATION, Stage.ARCHITECTURE, Stage.BLOCKED},
    Stage.IMPLEMENTATION: {Stage.VERIFICATION, Stage.BLOCKED},
    Stage.VERIFICATION: {Stage.IMPLEMENTATION, Stage.RELEASE_APPROVAL, Stage.BLOCKED},
    Stage.RELEASE_APPROVAL: {Stage.RELEASED, Stage.IMPLEMENTATION, Stage.BLOCKED},
    Stage.RELEASED: set(),
    Stage.BLOCKED: {Stage.INTAKE, Stage.ARCHITECTURE, Stage.PLANNING, Stage.IMPLEMENTATION},
}


@dataclass
class FactoryState:
    initiative_id: str
    stage: Stage = Stage.INTAKE
    approved_architecture_hash: str | None = None
    approved_artifact_digest: str | None = None
    approvals: dict[str, dict[str, str]] = field(default_factory=dict)
    gates: dict[str, GateResult] = field(default_factory=dict)
    history: list[dict[str, str]] = field(default_factory=list)
    required_gates: tuple[str, ...] = (
        "build", "unit", "integration", "security", "dependencies",
        "e2e", "iac", "provenance", "rollback",
    )

    def transition(self, target: Stage, actor: str, reason: str) -> None:
        if target not in TRANSITIONS[self.stage]:
            raise TransitionError(f"Invalid transition: {self.stage} -> {target}")
        if target is Stage.PLANNING and not self.approved_architecture_hash:
            raise TransitionError("Exact architecture revision requires human approval")
        if target is Stage.RELEASE_APPROVAL:
            missing = sorted(set(self.required_gates) - set(self.gates))
            if missing:
                raise TransitionError(f"Verification gates missing: {missing}")
            failed = [name for name in self.required_gates if not self.gates[name].passed]
            if failed:
                raise TransitionError(f"Verification gates failed: {failed}")
        if target is Stage.RELEASED:
            if "production-release" not in self.approvals:
                raise TransitionError("Production release needs explicit human approval")
            if not self.approved_artifact_digest:
                raise TransitionError("Release artifact digest is missing")
        self.history.append({"from": self.stage, "to": target, "actor": actor, "reason": reason})
        self.stage = target

    def approve_architecture(self, revision_hash: str, actor: str, evidence: str) -> None:
        if self.stage is not Stage.ARCHITECTURE_APPROVAL:
            raise TransitionError("Architecture can only be approved at its approval gate")
        self.approved_architecture_hash = revision_hash
        self.approvals["architecture"] = {"actor": actor, "hash": revision_hash, "evidence": evidence}

    def approve_release(self, artifact_digest: str, actor: str, evidence: str) -> None:
        if self.stage is not Stage.RELEASE_APPROVAL:
            raise TransitionError("Release can only be approved at its approval gate")
        self.approved_artifact_digest = artifact_digest
        self.approvals["production-release"] = {
            "actor": actor, "digest": artifact_digest, "evidence": evidence
        }

    def record_gate(self, result: GateResult) -> None:
        self.gates[result.gate] = result


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, state: FactoryState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(state), indent=2, default=str) + "\n")
        temporary.replace(self.path)
