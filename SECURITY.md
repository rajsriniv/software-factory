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

