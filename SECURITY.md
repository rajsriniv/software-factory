# Security policy

## Reporting

Do not disclose suspected vulnerabilities in a public issue. Use GitHub private vulnerability reporting or the repository owner's documented security contact. Include affected revision, reproduction steps, impact, and suggested containment. The maintainer should acknowledge a report within five business days and coordinate disclosure after a fix is available.

## Trust boundaries

- Repository content, agent messages, research pages, build logs, and generated artifacts are untrusted input.
- Agents receive least-privilege tools, scoped worktrees, time/token limits, and no production credentials.
- Production assumes a protected GitHub Environment, an AWS OIDC role restricted to repository/environment claims, and explicit human approval.
- Workflow permissions default to read-only. Third-party actions must be reviewed and pinned to immutable commit SHAs.
- Secrets must not appear in prompts, logs, fixtures, plans, Terraform state, or artifacts.
- Release evidence includes checks, provenance, SBOM, digest, approved Terraform plan, smoke tests, and rollback criteria.

Major security findings and changes to IAM, KMS, networking, encryption, data retention, or trust policies require a specialist review and human approval. Votes cannot waive these gates.


## Controller assurance

Version-two local runs execute checks and validate hashed evidence, but trust
local actor identities and filesystem ownership. Local mode supports verification
only. Production deployment requires isolated mode with a privileged POSIX
controller, protected state/keys, distinct worker principals, pinned adapters and
signed runtime/council receipts. A separate principal must observe the approved
artifact digest and health after deployment. The stock native adapter does not
provide a trusted telemetry broker; operators must integrate one.

Interactive approval prevents accidental noninteractive confirmation; operator
identity depends on host access and protected keys. Legacy `FactoryState`, ledger
messages, Company Brain role filters and improvement JSON approval fields are not
authentication boundaries. Protect source documents, vectors, audit databases and
backups. Knowledge publication requires independent review and human approval;
manual `brain-ingest` must remain restricted to authorized onboarding operators.
See the [runtime contract](skills/software-factory/references/enforced-workflow.md)
and [knowledge boundaries](skills/software-factory/references/knowledge-updates.md).

The standalone AWS Actions workflow does not consume controller approvals or
signed evidence. Environment protection and independently integrated evidence
checks are required before using it as a production release pipeline.
