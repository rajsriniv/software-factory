# TDD and SDET

Use high-tier `factory-tdd-guide` and `factory-sdet` agents on all three hosts. Keep bounded implementation on the existing lower-tier Java/Python/React agents. Only start from a human-approved refined brief and approved architecture.

## Assembly line

1. During planning, have SDET build a requirement-to-E2E scenario matrix and define test data, environments, dependencies and expected outcomes. Use the approved architecture to choose test boundaries; do not change product requirements to simplify tests.
2. Before each behavior change, have the TDD guide define meaningful unit and integration tests with the implementer. Run a test and capture a failure caused by the missing behavior (RED), implement the smallest correct change (GREEN), then refactor with tests passing. Save commands, logs, requirement IDs and tested Git revisions. Compile errors, missing dependencies and skipped tests are not valid RED evidence. Never fabricate execution results. For documentation-only changes record an independently reviewed applicability rationale rather than inventing a test.
3. Have SDET author the complete E2E suite for the approved in-scope requirements and run it against the integrated service in an isolated test environment. Capture deployment/artifact revision, fixtures, commands and reports. If a required dependency or environment is unavailable, report BLOCKED; test files alone do not prove success.
4. Have the separate quality agent reproduce the relevant tests and validate scenario coverage, meaningful assertions, skipped tests and flakiness. Have reviewer assess requirements and evidence. SDET and implementers cannot approve their own work. Preserve human release approval.

## Complete E2E scope

“Complete” means every approved requirement has mapped E2E scenarios or an explicit, independently reviewed reason for another verification method. It does not mean every conceivable input is covered or that defects are impossible.

Cover applicable happy paths, invalid input, boundary values, authentication and authorization, tenant isolation, persistence, retries, idempotency, duplicate messages, dependency failures and recovery. Include frontend-to-backend journeys with Playwright when a UI exists. Assert user-visible outcomes, API responses and durable data effects rather than merely HTTP 200 or screenshot existence. Use deterministic data, stable locators, bounded waits, independent fixtures and cleanup. Do not use sleeps to conceal races or retries to silently turn failures green.

For Python/PySpark/Iceberg services, include applicable ingest-to-output journeys: real configured source fixtures through transformation to persisted tables and consumption, YAML validation, deduplication, schema evolution, late data, reconciliation and failure recovery. For AWS, test in a designated nonproduction account/environment with scoped credentials. Confirm catalog/engine compatibility from project sources. Mocks belong in unit/integration tests; clearly identify stubbed E2E dependencies and gaps to real end-to-end validation.

Do not run destructive or charge-generating AWS operations without existing task authorization. Never touch production or customer data to obtain E2E evidence. Store sanitized reports, traces and screenshots; keep secrets out of fixtures and artifacts.

## Handoffs and gates

Use ledger message kinds `test-plan`, `tdd-evidence`, `e2e-suite` and `e2e-results`, correlated with the task ID. Attach requirement IDs, test/scenario IDs, test code and application revisions, environment, executed commands, reports and unresolved gaps.

The controller's default release prerequisites now include `tdd` and `e2e-coverage` alongside `unit`, `integration` and `e2e`. Record `tdd` only after independently reviewed RED/GREEN/refactor evidence (or reviewed applicability rationale). Record `e2e-coverage` only after quality review confirms every requirement has a scenario or an approved alternative and no blocking gaps. Record `e2e` only after applicable tests actually run and pass. Never count skipped or quarantined blocking scenarios as passing.

These stages are agent workflow steps within planning, implementation and verification, not new controller enum stages. The controller checks reported gate results; it does not automatically execute tests, authenticate their authors or independently validate logs. Use the host/CI to produce trustworthy evidence. Existing states with custom `required_gates` need to include the new gates explicitly.
