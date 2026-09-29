---
name: software-factory
description: Run a governed multi-agent SDLC assembly line for Java or Python backends, React frontends, E2E automation, and AWS delivery. Use for architecture-to-release workflows needing agent councils, evidence-backed decisions, independent implementation/review, human approval, and deterministic quality gates.
---

# Software Factory

Use this repository's controller, configuration, governance, and blueprints. Treat agents as specialized workers and critics, not sources of truth. Bind every handoff to requirement IDs, repository revision, artifact hashes, acceptance criteria, evidence, assumptions, and unresolved questions.

Before intake and each stage, consult Company Brain using [company context](references/company-brain.md). Bind its source revisions to the task and refresh before approval.

Follow intake -> architecture council -> human architecture approval -> planning -> bounded implementation -> independent verification -> human release approval -> AWS release. Use high-tier explicit models for product analysis, architecture, planning, security, quality, review, and release; use lower-tier explicit models for bounded Java, Python, and React tasks. Verify actual model resolution rather than relying on agent claims.

For architecture work, read [TOGAF-aligned architecture](references/architecture.md). For governance and decision rules, read [factory governance](references/governance.md). For stack-specific work, read only the relevant reference: [Java](references/java.md), [Python and PySpark](references/python.md), [React and E2E](references/react-e2e.md), or [AWS](references/aws.md).

Agent councils require independent evidence-backed votes. Objective failures and safety findings cannot be outvoted. Use absolute majority; if none exists, use the controller's predeclared maximin fallback. Escalate ties, missing evidence, destructive changes, security exceptions, architecture revisions, and production deployment to a human.

Never let an implementer approve its own change. Never autonomously deploy or correct production. Report RELEASED only when the controller verifies all required evidence and the exact immutable artifact digest has human approval.
