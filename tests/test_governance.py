import pytest

from software_factory.governance import DecisionError, decide
from software_factory.models import Decision, Option, Vote

OPTIONS = (
    Option("a", "A", {"security": 0.7, "cost": -0.2, "delivery": 0.4}),
    Option("b", "B", {"security": 0.2, "cost": 0.6, "delivery": 0.7}),
)


def vote(agent: str, option: str, approve: bool = True) -> Vote:
    return Vote(agent, option, approve, "evidence-backed rationale", ("report.json",))


def test_absolute_majority_wins() -> None:
    decision = Decision("d1", "choose", ("x", "y", "z"), OPTIONS, [vote("x", "a"), vote("y", "a"), vote("z", "b")])
    assert decide(decision, True).outcome == "a"
    assert decision.method == "absolute-majority"


def test_maximin_fallback_selects_best_worst_case() -> None:
    decision = Decision("d2", "choose", ("x", "y", "z"), OPTIONS, [vote("x", "a"), vote("y", "b"), vote("z", "a", False)])
    assert decide(decision, True).outcome == "b"
    assert decision.method == "zero-sum-maximin"


def test_gate_failure_cannot_be_outvoted() -> None:
    decision = Decision("d3", "choose", ("x", "y", "z"), OPTIONS, [vote("x", "a"), vote("y", "a"), vote("z", "a")])
    assert decide(decision, False).status == "blocked"
    assert decision.outcome is None


def test_duplicate_vote_is_rejected() -> None:
    decision = Decision("d4", "choose", ("x", "y", "z"), OPTIONS, [vote("x", "a"), vote("x", "a")])
    with pytest.raises(DecisionError, match="Duplicate"):
        decide(decision, True)


def test_zero_sum_tie_requires_human() -> None:
    options = (Option("a", "A", {"risk": 0.2}), Option("b", "B", {"risk": 0.2}))
    decision = Decision("d5", "choose", ("x", "y", "z"), options, [vote("x", "a"), vote("y", "b")])
    assert decide(decision, True).status == "human-review"

