import pytest

from software_factory.models import GateResult, Stage
from software_factory.pipeline import FactoryState, TransitionError


def test_architecture_and_release_require_human_approval() -> None:
    state = FactoryState("i1", required_gates=("tests",))
    state.transition(Stage.ARCHITECTURE, "controller", "requirements ready")
    state.transition(Stage.ARCHITECTURE_APPROVAL, "architect", "revision presented")
    with pytest.raises(TransitionError):
        state.transition(Stage.PLANNING, "planner", "too early")
    state.approve_architecture("sha256:architecture", "human", "approval.md")
    state.transition(Stage.PLANNING, "human", "approved")
    state.transition(Stage.IMPLEMENTATION, "planner", "plan accepted")
    state.transition(Stage.VERIFICATION, "controller", "work integrated")
    state.record_gate(GateResult("tests", True, ("junit.xml",)))
    state.transition(Stage.RELEASE_APPROVAL, "controller", "gates passed")
    with pytest.raises(TransitionError):
        state.transition(Stage.RELEASED, "release", "too early")
    state.approve_release("sha256:image", "human", "deployment-approval.md")
    state.transition(Stage.RELEASED, "release", "approved immutable artifact")


def test_failed_gate_blocks_release_approval() -> None:
    state = FactoryState("i2", stage=Stage.VERIFICATION, required_gates=("security",))
    state.record_gate(GateResult("security", False, ("scan.sarif",), ("critical finding",)))
    with pytest.raises(TransitionError, match="failed"):
        state.transition(Stage.RELEASE_APPROVAL, "controller", "attempt")


def test_default_release_requires_tdd_and_e2e_coverage() -> None:
    state = FactoryState("tdd", stage=Stage.VERIFICATION)
    for name in state.required_gates:
        if name not in {"tdd", "e2e-coverage"}:
            state.record_gate(GateResult(name, True, ("report",)))
    with pytest.raises(TransitionError, match="missing"):
        state.transition(Stage.RELEASE_APPROVAL, "quality", "attempt")
    state.record_gate(GateResult("tdd", True, ("red-green-refactor.log",)))
    state.record_gate(GateResult("e2e-coverage", False, ("coverage.json",)))
    with pytest.raises(TransitionError, match="failed"):
        state.transition(Stage.RELEASE_APPROVAL, "quality", "attempt")
    state.record_gate(GateResult("e2e-coverage", True, ("coverage.json",)))
    state.transition(Stage.RELEASE_APPROVAL, "quality", "coverage verified")
