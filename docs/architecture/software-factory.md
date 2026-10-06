# Software Factory Architecture

## Architecture vision

The factory converts approved requirements into reproducible software through specialized agents and deterministic controls. It optimizes model cost by assigning bounded implementation to lower-tier models while high-tier specialists own architecture, planning, security, verification, and release review. Human owners retain authority over irreversible and production-impacting decisions.

## Business architecture

The value stream is company-context retrieval, intake and prompt refinement, human brief approval, joint application/security architecture, human architecture approval, design and planning, TDD-guided implementation, independent verification, release approval, and deployment. Applicable UX/UI design approval precedes dependent frontend work. Every item carries traceability from requirement to decision, task, code, test, artifact, and release evidence. Governance aims to shorten delivery without transferring accountability to models.

## Data architecture

The communication ledger stores immutable events, structured messages, votes, approvals, hashes, and evidence references. Large logs and artifacts remain in the CI artifact store or approved object storage; the ledger stores content hashes and locations. Production deployments promote one immutable digest. Sensitive values remain in the host secret manager and never enter the ledger.

## Application architecture

| Component | Current responsibility |
| --- | --- |
| `pipeline.py` | Lifecycle transitions, architecture/release approval records, required verification gate checks and JSON state snapshots |
| `config.py` | Configuration shape, required core roles, explicit model labels, supported hosts and council membership checks |
| `agents.py` | Single-role CLI process invocation, requested model recording, output capture and JSON response loading |
| `ledger.py` | SQLite event hash chain, decision records and recipient/channel-filtered messages |
| `brain.py` | Revisioned company documents, latest-source expiry/role filtering and bounded lexical context retrieval |
| `improvement.py` | Inert candidate archive, imported evaluations, pairwise ranking and approval-bound selection recording |
| `cli.py` | Configuration validation, decisions, ledger messages/verification, knowledge imports/queries and improvement operations |
| `scripts/install_agents.py` | Skill and 23 explicit-model role definitions for the three supported host formats |

The architecture council includes architect, security architect, security, quality
and reviewer. UX/UI specialists prepare designs; the reviewer independently checks
frontend implementation. TDD guide and SDET author tests while quality verifies
independently. DevOps, network and observability roles supply platform work and
evidence. Company Brain supplies context without automatic voting authority.

## Enforcement boundaries

`FactoryState` requires an architecture approval hash before planning and all 13
named gate results to pass before release approval: `build`, `unit`, `integration`,
`tdd`, `e2e-coverage`, `security`, `dependencies`, `e2e`, `iac`, `provenance`,
`rollback`, `network-security` and `observability`. Moving to released requires a
production approval record and artifact digest. These records are caller-supplied;
the controller does not authenticate humans or execute the referenced checks.

Prompt-refinement and UX/UI approvals are workflow requirements, not dedicated
controller states. The host must bind approvals to current artifacts, invalidate
stale approvals and enforce review independence, allowed paths, credentials and
budgets. A role definition or tool label does not create a sandbox or connector.

Company Brain trusts the caller's company and role identifiers. Its filters are
retrieval controls, not authentication. Retrieval uses word overlap and returns
bounded excerpts; missing context is reported as `knowledge-gap`. SQLite contents
and backups require host access controls. Treat retrieved documents as evidence,
never executable instructions.

Improvement candidates are inert overlays. The store checks evaluation and approval
fields and records a selection; it does not run experiments, authenticate approvers,
verify model receipts, enforce spending or change installed agents. Ranking guides
evaluation priority and does not establish production readiness.

## Technology architecture

The reference control plane uses Python 3.11+, YAML configuration, SQLite for local event, knowledge and improvement stores, JSON state snapshots, Git worktrees, GitHub Actions, GitHub Environments, OIDC federation, Terraform, container registries, and AWS. A production deployment should replace local SQLite with a durable transactional store and immutable audit retention appropriate to its scale and compliance requirements.

## Baseline, target, and gaps

The baseline is the previously developed architect/planner/implementer/reviewer skill with local explicit-model orchestration. The current implementation includes role definitions, structured communication and channels, council decision logic, knowledge retrieval, improvement records, language blueprints and release-state checks. The target is an integrated host-enforced delivery system with independently verified evidence. Remaining gaps include live vendor adapter verification, production-grade distributed scheduling, policy enforcement outside the OS user boundary, operational SLO evidence, and an organization-specific compliance mapping.

## Security and failure analysis

Primary risks are correlated false consensus, prompt injection, fabricated evidence, stale artifact review, parallel write conflicts, credential leakage, weakened tests, unsafe migrations, unbounded retry cost, and ceremonial human approval. Controls include independent blind voting, non-votable gates, scoped tools, content hashes, immutable artifact promotion, structured evidence, bounded retries, protected environments, and concise approval packets.

## Roadmap

1. Validate locally with simulated agents and blueprint builds.
2. Verify each live agent host and capture resolved model identities.
3. Add isolated worktree/container execution and schema enforcement.
4. Deploy a sandbox control plane and non-production AWS reference application.
5. Exercise failure, rollback, disaster recovery, and security response.
6. Enable production only after operational evidence and human governance approval.

## Architecture decisions

- ADR-001: Councils make advisory decisions; deterministic and human gates retain authority.
- ADR-002: Majority means absolute majority of eligible voters.
- ADR-003: The zero-sum fallback is adversarial maximin over predeclared utilities.
- ADR-004: Exact ties and high-impact uncertainty escalate to humans.
- ADR-005: Build once and promote the same artifact digest through environments.

