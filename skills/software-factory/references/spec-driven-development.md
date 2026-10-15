# Spec-driven development contract (version 0.2)

Start new initiatives with schema_version 2. Treat version-one manifests and
FactoryState as legacy compatibility, not production authorization.

## Prepare a concrete specification

Read the user's spec and consult Company Brain. Identify unknowns rather than
inventing acceptance criteria. Store a reviewed JSON spec in the project:

```json
{"requirements":[{"id":"R1","acceptance":["An observable outcome","An error or negative case"]}]}
```

Use `config/spec.example.json` for shape only. Each acceptance string has a stable
criterion key within this spec version: `R1::AC1`, `R1::AC2`. Editing, reordering,
adding or removing criteria creates a new spec hash and requires new approvals.
Do not call a requirement complete because one of its criteria passed.

## Create and check the execution contract

Use `scripts/init_spec_workflow.py` from the factory checkout after installing its
Python package. Supply the project checkout, spec, real verification commands,
client and exact model IDs. The initializer creates a verification-only manifest
and does not overwrite existing files. It fingerprints existing files under
`tests/` as baseline regressions. Inspect that list and add framework-specific
fixtures, Java/React test directories and runner configuration when relevant.

`--task-templates` accepts a reviewed mapping for Java, React or other project
workers. The default is Python with JUnit-producing pytest. Require deterministic
TDD commands and configure framework-appropriate JUnit output for other stacks.
Never reuse the placeholder checks as successful validations.

Run `workflow doctor`, inspect any missing executables/adapters, and resolve them
before running `workflow next`. Doctor does not authenticate native clients or
validate provider model availability. Log in using each client's supported flow.
Do not claim a live client was tested because its agent file was generated.

Add `.factory-state/`, test caches and build outputs to the project's ignore file;
never ignore source, specifications or tests. Keep the workflow database and
manifest outside the project checkout. The controller snapshots tracked and
nonignored source and hashes accepted evidence separately.

## Execute the approved stages

The controller requires Company Brain context (or an explicit knowledge gap),
refinement and human intake approval, alternatives, architecture, independent
security design and challenge, a council decision, and human architecture approval.
Existing systems add discovery. Frontend projects add UX, independent UI review
and human UI approval. Record applicability explicitly in the manifest.

The planner produces tasks after architecture approval. Each task declares:

- `id`, `template`, `requirements`, and prior `depends_on` IDs;
- `test_files` and nonoverlapping implementation `write_files` (exact paths);
- observable `acceptance` criteria for the chunk.

The planner selects operator-owned templates; it cannot introduce executables.
The controller validates the graph and waits at **plan-approval** before tests or
implementation. Templates use explicit high-tier models for design/test/review and
lower-tier implementers. Native adapters receive the current task and references
to previous outputs through `FACTORY_CONTEXT`.

SDET test design must supply `test_map`, mapping every criterion key to expected
JUnit test IDs. Each task then runs test writing → real red → implementation →
real green → independent review. Previously accepted tests and baseline regressions
remain protected. Refactor inside the implementation step, then rerun green.

E2E is a tool step, not an LLM assertion. `software_factory.acceptance_runner`
executes the configured command, reads fresh JUnit and checks the SDET mapping.
Final verification must cover every criterion and execute each mandatory gate.
Negative/error-path criteria belong in the approved spec, not an optional prose
recommendation. For high-risk components, configure mutation testing within the
unit gate and retain mutation results as evidence; the factory does not bundle
mutation engines or promise that passing assertions prove completeness.

The knowledge-proposal stage prepares a hashed draft for the existing independent
review/human approval publication flow. It does not silently publish generated
claims to Company Brain. `knowledge_gap: true` permits transparent initial work,
not an assertion that missing organizational requirements are satisfied.

## Repair without losing the audit

Failed checks never advance. `workflow repair` requires an interactive human
request and is available only after a recorded task green/review failure. It
retains the approved spec, architecture, plan and red evidence; invalidates that
task's implementation and later active results; and returns to implementation.
The complete history remains visible in `workflow events`. Retry and repair
budgets default to three; failed output files are archived before retry.

Changed specs, architecture, test contracts, manifests, protected-test mutations,
timeouts or uncertain deployment side effects require investigation and a new run.
There is no automatic production correction. Arbitrary cross-run approval reuse
is deliberately not implemented. Report the invalidated scope rather than
claiming a fresh approval was inherited.

## Report only the assurance actually established

Local mode is useful for spec-driven development on a user's computer. Its
identities and approvals are locally trusted. Same-user software can bypass file
permissions; do not present local mode as an adversarial security boundary.

Production uses isolated mode: a privileged POSIX controller, separate non-root
worker identities, protected keys/state, pinned trusted adapters, signed runtime
and council receipts, and an approved account/region/environment/IaC plan.
The stock native adapter cannot manufacture signed telemetry. A trusted provider
or execution broker must supply it; otherwise isolated agent steps stop.

Deploy the approved artifact without rebuilding. A different principal must
observe its digest and health in the approved environment before completion.
Signed usage receipts provide token/cost accounting and budget stops. Missing
telemetry must be reported as unknown, never as zero cost or a verified model.

Always state: spec hash, covered criteria, artifact hash, assurance level,
unresolved limitations, and whether the result is local verification or an
independently verified deployment. No workflow can prove semantic completeness;
independent review and the user's acceptance remain essential.
