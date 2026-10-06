from __future__ import annotations

from collections import Counter

from .models import Decision


class DecisionError(ValueError):
    pass


def _validate(decision: Decision) -> None:
    voters = set(decision.eligible_voters)
    if len(voters) < 3 or len(voters) % 2 == 0:
        raise DecisionError("A decision council must contain an odd number of at least three voters")
    if len({option.option_id for option in decision.options}) != len(decision.options):
        raise DecisionError("Option IDs must be unique")
    seen: set[str] = set()
    for vote in decision.votes:
        if vote.agent_id not in voters:
            raise DecisionError(f"Ineligible voter: {vote.agent_id}")
        if vote.agent_id in seen:
            raise DecisionError(f"Duplicate vote: {vote.agent_id}")
        if vote.option_id not in {option.option_id for option in decision.options}:
            raise DecisionError(f"Unknown option: {vote.option_id}")
        if not vote.rationale or not vote.evidence:
            raise DecisionError("Every vote needs rationale and evidence")
        seen.add(vote.agent_id)


def decide(decision: Decision, mandatory_gates_passed: bool) -> Decision:
    """Resolve an advisory council decision.

    Majority requires more than half of all eligible voters, not just responses.
    When no majority exists, use an adversarial maximin rule: each utility
    dimension represents a stakeholder or failure scenario; select the option
    with the best worst-case payoff. This is the zero-sum fallback: the
    proposer maximizes utility while a red-team adversary chooses the most
    damaging credible dimension. An exact tie is escalated to a human.
    """
    _validate(decision)
    if not mandatory_gates_passed:
        decision.status = "blocked"
        decision.method = "policy-veto"
        return decision

    approved = [vote.option_id for vote in decision.votes if vote.approve]
    counts = Counter(approved)
    threshold = len(decision.eligible_voters) // 2 + 1
    winners = [option_id for option_id, count in counts.items() if count >= threshold]
    if len(winners) == 1:
        decision.outcome = winners[0]
        decision.method = "absolute-majority"
        decision.status = "decided"
        return decision
    if len(winners) > 1:
        raise DecisionError("Contradictory majority; inspect voting inputs")

    candidates = [option for option in decision.options if not option.disqualifiers]
    if not candidates:
        decision.status = "blocked"
        decision.method = "all-options-disqualified"
        return decision
    for option in candidates:
        if not option.utilities:
            raise DecisionError(f"Option {option.option_id} has no utility matrix")
        if any(score < -1 or score > 1 for score in option.utilities.values()):
            raise DecisionError("Utilities must be normalized to [-1, 1]")

    worst_case = {option.option_id: min(option.utilities.values()) for option in candidates}
    best = max(worst_case.values())
    winners = sorted(option_id for option_id, score in worst_case.items() if score == best)
    if len(winners) != 1:
        decision.status = "human-review"
        decision.method = "maximin-tie"
        return decision
    decision.outcome = winners[0]
    decision.method = "zero-sum-maximin"
    decision.status = "decided"
    return decision


def safety_gates(findings: list[dict[str, str]], checks: list[dict[str, object]]) -> bool:
    material = {"blocker", "major"}
    return not any(f.get("severity", "").lower() in material for f in findings) and all(
        bool(check.get("passed")) for check in checks
    )

