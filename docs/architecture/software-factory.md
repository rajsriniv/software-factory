# Software Factory Architecture

## Architecture vision

The factory converts approved requirements into reproducible software through specialized agents and deterministic controls. It optimizes model cost by assigning bounded implementation to lower-tier models while high-tier specialists own architecture, planning, security, verification, and release review. Human owners retain authority over irreversible and production-impacting decisions.

## Business architecture

The value stream is intake, architecture, approval, planning, implementation, verification, release approval, and AWS deployment. Every item carries traceability from requirement to decision, task, code, test, artifact, and release evidence. Governance aims to shorten delivery without transferring accountability to models.

## Data architecture

The communication ledger stores immutable events, structured messages, votes, approvals, hashes, and evidence references. Large logs and artifacts remain in the CI artifact store or approved object storage; the ledger stores content hashes and locations. Production deployments promote one immutable digest. Sensitive values remain in the host secret manager and never enter the ledger.

## Application architecture

- Controller: deterministic lifecycle and gates.
- Agent host adapters: Codex, Claude Code, and Copilot integrations with explicit models.
- Councils: independent architecture, implementation, and release reviewers.
- Worker pools: Java, Python, React, E2E, and infrastructure tasks isolated by worktree/container.
- Evidence service: test, scan, provenance, SBOM, plan, deployment, and rollback evidence.
- Human approval UI: binds identity and approval to artifact hashes.

## Technology architecture

The reference control plane uses Python 3.11+, YAML configuration, SQLite for local append-only event storage, Git worktrees, GitHub Actions, GitHub Environments, OIDC federation, Terraform, container registries, and AWS. A production deployment should replace local SQLite with a durable transactional store and immutable audit retention appropriate to its scale and compliance requirements.

## Baseline, target, and gaps

The baseline is the previously developed architect/planner/implementer/reviewer skill with local explicit-model orchestration. The target adds an agent registry, structured communication, councils, deterministic voting, multiple language profiles, E2E, GitHub governance, and AWS release gates. Remaining gaps include live vendor adapter verification, production-grade distributed scheduling, policy enforcement outside the OS user boundary, operational SLO evidence, and an organization-specific compliance mapping.

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

