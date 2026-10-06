# Governance

## Decision authority

Councils advise on options whose trade-offs are reversible and measurable. The controller owns state transitions. Humans approve the exact architecture revision, requirement changes, destructive or irreversible migrations, IAM/network trust changes, policy exceptions, and production deployment.

The following are not subject to majority vote: compilation/test failures; blocker or major security findings; data-loss risk; legal/compliance failures; missing requirement coverage; missing provenance; a changed artifact after approval; and absent human approval.

## Voting protocol

1. The decision owner publishes a question, eligible voters, options, evaluation dimensions, normalized utilities, evidence deadline, and conflicts of interest.
2. Agents review independently. They do not see other votes until voting closes.
3. Each eligible agent submits one approve/reject vote with rationale and evidence. Abstention or insufficient evidence counts toward neither option.
4. An option wins only with more than half of all eligible voters.
5. Without a majority, disqualified options are removed and the controller applies zero-sum maximin: for each option, a red-team adversary selects its worst credible utility dimension; the controller selects the option with the greatest worst-case payoff.
6. Exact ties, missing matrices, incomparable options, and high-impact decisions go to a human.

Utilities are agreed before votes and cover requirement fit, correctness, security, reversibility, operability, cost, maintainability, and delivery. They must not be altered after seeing a losing vote. The ledger records every input and outcome.

## Independence

Proposer, implementer, and final reviewer are separate runs. Nominally different agents using identical model, prompt, and evidence are not treated as independent without an explicit waiver. Councils should mix specialist prompts and, where practical, different capable models. Reviewers receive requirements and artifacts directly rather than an implementer's persuasive summary.

## Change management

Material architecture or requirement changes invalidate affected plans and approvals. Rollback and correction proposals follow the same approval path as forward changes. No agent may autonomously change production data or deploy a correction.

