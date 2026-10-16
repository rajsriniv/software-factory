---
name: software-factory
description: Run a governed multi-agent SDLC assembly line for Java, Python or Rust backends, React web frontends, Rust GTK4 or Iced desktop apps, E2E automation, and AWS delivery. Use for architecture-to-release workflows needing agent councils, evidence-backed decisions, independent implementation/review, human approval, and deterministic quality gates.
---

# Software Factory

Start with [spec-driven development](references/spec-driven-development.md). Use version-two manifests for new work. Bind the approved specification and each acceptance criterion to executable evidence. Run `workflow doctor` before execution, and report local verification separately from an independently verified release.

Use the [enforced workflow controller](references/enforced-workflow.md) for every execution and handoff. Read that reference before starting work. Stop if a trusted controller has not been configured; never fall back to prose-only handoffs or the legacy FactoryState simulation. Only report completion from `workflow status` showing `complete`.

Use this repository's controller, configuration, governance, and blueprints. Treat agents as specialized workers and critics, not sources of truth. Bind every handoff to requirement IDs, repository revision, artifact hashes, acceptance criteria, evidence, assumptions, and unresolved questions.

Before intake and each stage, consult Company Brain using [company context](references/company-brain.md). Bind its source revisions to the task and refresh before approval.

Run [prompt refinement](references/prompt-refiner.md) at intake and whenever the requirement changes. Present every refined brief for mandatory human review. Wait for explicit approval tied to its revision and saved artifact hash before handing it to product or architecture. Any edit invalidates that approval; present the revised brief again. Do not treat inferred requirements as approved.

Follow intake/refinement -> human refined-brief approval -> architecture/security design and independent challenge -> applicable UX/UI review and human UI approval -> architecture council -> human architecture approval -> planning -> human plan approval -> SDET test design -> TDD implementation -> SDET E2E execution -> independent verification -> human release approval -> AWS release and independent deployment verification when isolated deployment is configured. Local verification mode stops before release. Use high-tier explicit models for product analysis, architecture, planning, security, quality, review, and release; use lower-tier explicit models for bounded Java, Python, React, and Rust tasks. Verify actual model resolution rather than relying on agent claims.

For architecture work, read [TOGAF-aligned architecture](references/architecture.md). For governance and decision rules, read [factory governance](references/governance.md). For stack-specific work, read only the relevant reference: [Java](references/java.md), [Python and PySpark](references/python.md), [React and E2E](references/react-e2e.md), [Rust](references/rust.md), [Rust GTK4 and Iced desktop UI](references/rust-desktop.md) (read with Rust), or [AWS](references/aws.md).

Agent councils require independent evidence-backed votes. Objective failures and safety findings cannot be outvoted. Use absolute majority; if none exists, use the controller's predeclared maximin fallback. Escalate ties, missing evidence, destructive changes, security exceptions, architecture revisions, and production deployment to a human.

Never let an implementer approve its own change. Never autonomously deploy or correct production. Report RELEASED only when the controller verifies all required evidence and the exact immutable artifact digest has human approval.

For implementation and E2E work, follow [TDD and SDET](references/tdd-sdet.md). Require red-green-refactor evidence and requirement-to-E2E coverage before release review. Keep SDET test authorship separate from quality verification.

Use [platform specialists and collaboration channels](references/platform-specialists.md) for code mapping, security review, implementation planning, DevOps, networking and observability. Keep security first: require independent review of IAM, network exposure and deployment blast radius; verify observability before release. Use explicit ledger channels for all specialist handoffs.

During architecture, have `factory-architecture-challenger` independently challenge assumptions, failure modes and unsupported claims before council review. Have the architect and high-tier security architect jointly produce [secure architecture](references/security-architecture.md). Require independent security review and resolution of blocking threats before human architecture approval.

For user-facing products, involve high-tier UX and UI specialists before frontend implementation. Follow [UX, UI and independent frontend review](references/ux-ui.md); obtain human approval of the design, then have reviewer assess UI code and rendered behavior independently.

For explicitly requested prompt/workflow optimization, follow the isolated [improvement loop](references/improvement.md). Never apply candidates to live agents automatically; judge rankings guide evaluation effort and cannot replace mandatory verification or human approval.

At approved architecture and verified project milestones, have Company Brain prepare [reviewable knowledge updates](references/knowledge-updates.md) from durable artifacts. Obtain independent review and exact human approval before invoking publication and vector reindexing. Never promote task discussion or unapproved assumptions automatically.

For existing or undocumented systems, use the high-tier [Reverse Engineer](references/reverse-engineering.md) alongside Code Mapper before proposing changes. Independently review reconstructed behavior and baseline architecture; preserve human approval for new scope and Company Brain publication.
