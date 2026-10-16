# TOGAF-aligned architecture

Use a high-tier model with research capability, but treat citations, repository evidence, and tested prototypes as the authority. Record the exact model resolved by the host.

Create an architecture review package with:

1. Architecture vision: requirement IDs, stakeholders, business outcomes, scope, constraints, measurable quality attributes, and explicit exclusions.
2. Baseline and target: business, data, application, and technology views, including repository boundaries and AWS accounts/regions.
3. Gap analysis and transition architectures: current-to-target gaps, migration increments, coexistence, rollback, and decommissioning.
4. Cross-cutting concerns: security, privacy, resilience, observability, cost, operability, data governance, and regulatory constraints.
5. Decisions: alternatives, evidence, trade-offs, risks, assumptions, consequences, and Architecture Decision Records.
6. Requirements traceability: each design element and acceptance test maps to stable requirement IDs.
7. Governance: architecture council votes, dissent, human approval, approved document hash, and change-control triggers.

Version-two runs require separate `security-architecture` and
`architecture-challenge` documents before council review. Use high-tier
`factory-architecture-challenger` to challenge assumptions, failure modes and
unsupported claims; resolve objections in independently reviewed evidence. The
challenger is separate from the example five-member architecture council. For
frontend work, complete UX, UI review and human UI approval before council review.
See the [spec workflow](spec-driven-development.md).

For AWS data systems, explicitly cover IAM boundaries, encryption, network paths, region and recovery objectives. For PySpark and Iceberg, cover catalog choice, table format version, partition evolution, schema evolution, snapshot retention, compaction, concurrency, and recovery.

When a changed architecture is supplied, do not silently replace the approved version. Diff it against the approved hash, list benefits, costs, risks, reversibility, migration impact, and affected requirements, then send it back through council and human approval.
