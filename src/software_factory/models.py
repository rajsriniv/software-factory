from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Stage(StrEnum):
    INTAKE = "intake"
    ARCHITECTURE = "architecture"
    ARCHITECTURE_APPROVAL = "architecture_approval"
    PLANNING = "planning"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    RELEASE_APPROVAL = "release_approval"
    RELEASED = "released"
    BLOCKED = "blocked"


class Severity(StrEnum):
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    BLOCKER = "blocker"


@dataclass(frozen=True)
class Message:
    message_id: str
    correlation_id: str
    sender: str
    recipient: str
    kind: str
    payload: dict[str, Any]
    created_at: str
    channel: str = "factory-general"


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    role: str
    host: str
    model: str
    tier: str
    tools: tuple[str, ...]


@dataclass(frozen=True)
class Vote:
    agent_id: str
    option_id: str
    approve: bool
    rationale: str
    evidence: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()


@dataclass(frozen=True)
class Option:
    option_id: str
    summary: str
    # Scores are declared before voting and normalized to [-1, 1].
    utilities: dict[str, float]
    disqualifiers: tuple[str, ...] = ()


@dataclass
class Decision:
    decision_id: str
    question: str
    eligible_voters: tuple[str, ...]
    options: tuple[Option, ...]
    votes: list[Vote] = field(default_factory=list)
    outcome: str | None = None
    method: str | None = None
    status: str = "open"
    evidence: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    evidence: tuple[str, ...]
    findings: tuple[str, ...] = ()
