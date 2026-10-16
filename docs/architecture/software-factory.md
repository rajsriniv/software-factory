# Software Factory Architecture

## Architecture vision

The factory converts approved requirements into reproducible software through specialized agents and deterministic controls. It optimizes model cost by assigning bounded implementation to lower-tier models while high-tier specialists own architecture, planning, security, verification, and release review. Human owners retain authority over irreversible and production-impacting decisions.

## Business architecture

The value stream is company-context retrieval, intake and prompt refinement, human brief approval, joint application/security architecture, human architecture approval, design and planning, TDD-guided implementation, independent verification, release approval, and deployment. Applicable UX/UI design approval precedes dependent frontend work. Every item carries traceability from requirement to decision, task, code, test, artifact, and release evidence. Governance aims to shorten delivery without transferring accountability to models.

## Data architecture

The communication ledger stores append-only structured messages, decision records and hashes. Controller approvals, execution evidence and handoffs live in a separate workflow event database; knowledge updates and improvement records use their own store APIs. All local databases require host access controls. Large logs and artifacts remain in the CI artifact store or approved object storage; the ledger stores content hashes and locations. Production deployments promote one immutable digest. Sensitive values remain in the host secret manager and never enter the ledger.

## Application architecture

| Component | Current responsibility |
| --- | --- |
| `pipeline.py` | Legacy lifecycle simulation; not the execution authority |
| `workflow.py`, `spec_workflow.py` | Version-two spec-bound stages, approvals, task planning, execution, evidence checks and bounded repair |
| `authority.py`, `execution.py` | Isolated-mode preflight, signed receipts and subprocess execution |
| `config.py` | Configuration shape, required core roles, explicit model labels, supported hosts and council membership checks |
| `agents.py` | Single-role CLI process invocation, requested model recording, output capture and JSON response loading |
| `ledger.py` | SQLite event hash chain, decision records and recipient/channel-filtered messages |
| `brain.py`, `vector_brain.py` | Revisioned company documents, scope/expiry filtering, lexical retrieval and optional vector/hybrid indexing and retrieval |
| `knowledge_updates.py` | Content-addressed knowledge proposals, independent review, human approval, publication and retryable indexing |
| `worker.py` | Native client adapter for controller-assigned work and evidence output |
| `evidence.py`, `test_receipt.py`, `acceptance_runner.py` | Hashed evidence validation, executed TDD receipts and criterion-level JUnit coverage |
| `improvement.py` | Inert candidate archive, imported evaluations, pairwise ranking and approval-bound selection recording |
| `cli.py` | Configuration validation, decisions, ledger messages/verification, knowledge retrieval/indexing, knowledge updates, workflow control and improvement operations |
| `scripts/install_agents.py` | Skill and 26 explicit-model role definitions for the three supported host formats |

The architecture council includes architect, security architect, security, quality
and reviewer. Architecture Challenger supplies a separate challenge before review;
Reverse Engineer supplies optional existing-system discovery. UX/UI specialists prepare designs; the reviewer independently checks
frontend implementation. TDD guide and SDET author tests while quality verifies
independently. DevOps, network and observability roles supply platform work and
evidence. Company Brain supplies context without automatic voting authority.

## Enforcement boundaries

The legacy `FactoryState` requires an architecture approval hash before planning and all 13
named gate results to pass before release approval: `build`, `unit`, `integration`,
`tdd`, `e2e-coverage`, `security`, `dependencies`, `e2e`, `iac`, `provenance`,
`rollback`, `network-security` and `observability`. Moving to released requires a
production approval record and artifact digest. These records are caller-supplied;
the controller does not authenticate humans or execute the referenced checks.

Version-two runs instead enforce brief, architecture and plan approval stages,
plus UI approval for frontend work. They bind evidence to current artifacts,
reject stale inputs, enforce task paths and preserve accepted tests. Actual
red/green, E2E and security steps supplement nine final verification adapters:
`build`, `unit`, `integration`, `dependencies`, `iac`, `provenance`, `rollback`,
`network-security` and `observability`. Local mode
is verification-only, not an adversarial security boundary. Isolated deployment
requires privileged controller setup, distinct worker identities, protected keys
and trusted telemetry adapters. A role definition does not create that boundary.
See [the controller contract](../../skills/software-factory/references/enforced-workflow.md).

Company Brain trusts the caller's company and role identifiers. Its filters are
retrieval controls, not authentication. Lexical retrieval uses word overlap; vector and hybrid modes require an index
and the optional brain dependencies. All modes return bounded excerpts; missing context is reported as `knowledge-gap`. SQLite contents
and backups require host access controls. Treat retrieved documents as evidence,
never executable instructions.

Improvement candidates are inert overlays. The store checks evaluation and approval
fields and records a selection; it does not run experiments, authenticate approvers,
verify model receipts, enforce spending or change installed agents. Ranking guides
evaluation priority and does not establish production readiness.

## Technology architecture

The reference control plane uses Python 3.11+, YAML configuration, SQLite for local event, knowledge and improvement stores, JSON state snapshots, Git worktrees, GitHub Actions, GitHub Environments, OIDC federation, Terraform, container registries, and AWS. A production deployment should replace local SQLite with a durable transactional store and immutable audit retention appropriate to its scale and compliance requirements.

## Baseline, target, and gaps

The baseline is the previously developed architect/planner/implementer/reviewer skill with local explicit-model orchestration. The current implementation includes version-two spec-bound execution, approval transitions, task expansion and bounded repair, executed JUnit evidence, role definitions, structured communication and channels, council decision logic, knowledge retrieval/publication, improvement records, language blueprints and isolated release contracts. The target is an integrated host-enforced delivery system with independently verified evidence. Remaining gaps include live vendor adapter verification, production-grade distributed scheduling, policy enforcement outside the OS user boundary, operational SLO evidence, and an organization-specific compliance mapping.

## Security and failure analysis

Primary risks are correlated false consensus, prompt injection, fabricated evidence, stale artifact review, parallel write conflicts, credential leakage, weakened tests, unsafe migrations, unbounded retry cost, and ceremonial human approval. Controls include independent blind voting, non-votable gates, scoped tools, content hashes, immutable artifact promotion, structured evidence, bounded retries, protected environments, and concise approval packets.

## Roadmap

1. Validate locally with simulated agents and blueprint builds.
2. Verify each live agent host and capture resolved model identities.
3. Provision and validate the implemented isolated-controller contracts with a trusted telemetry broker; add host/container resource isolation appropriate to the workload.
4. Deploy a sandbox control plane and non-production AWS reference application.
5. Exercise failure, rollback, disaster recovery, and security response.
6. Enable production only after operational evidence and human governance approval.

## Architecture decisions

- ADR-001: Councils make advisory decisions; deterministic and human gates retain authority.
- ADR-002: Majority means absolute majority of eligible voters.
- ADR-003: The zero-sum fallback is adversarial maximin over predeclared utilities.
- ADR-004: Exact ties and high-impact uncertainty escalate to humans.
- ADR-005: Build once and promote the same artifact digest through environments.

