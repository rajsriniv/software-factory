# Controller and runtime contract

Read [spec-driven development](spec-driven-development.md) for the workflow.
Use `schema_version: 2` for new projects; version-one state is a legacy local
compatibility path, not production authorization.

## Controller commands

All commands take `--database /trusted/run.db`,
`--manifest /trusted/workflow.json` and `--repository /work/project`.

- `workflow doctor`: validate spec/state and detect missing executables/adapters.
- `workflow status`: current eligible phase, assurance, delivery mode and usage.
- `workflow next`: execute exactly one eligible phase; approvals cannot be skipped.
- `workflow approve`: display evidence and require the exact interactive phrase.
- `workflow repair`: interactively request bounded task repair after failed green/review.
- `workflow events`: full audit, including superseded attempts and repair requests.

The `factory-handoffs` event channel records command outcomes, source snapshots,
content hashes, actor, duration and available signed usage. It is readable JSON,
not a hosted chat UI. Protect logs; they can contain project information.

No failed command advances. A durable in-flight marker prevents guessing whether
an interrupted command completed. Process groups are cleaned up on completion or
timeout. Timeouts, protected-input mutation and uncertain deployment require
investigation, not automatic replay. Escaped process namespaces and disk quotas
require host/container policy; the Python controller is not a sandbox.

## Evidence and tool contracts

Every successful step exits zero and returns JSON with nonempty `summary` and
`passed: true`; red exits 1 with expected assertion failures. Write the response
to `FACTORY_EVIDENCE_OUTPUT`. Use `FACTORY_CONTEXT` for the assigned spec, task,
prior accepted outputs and deployment scope. Do not include unrelated company
knowledge or whole repository contents in every agent prompt.

Reference a document/report as `{"path":"relative/path","sha256":"..."}`.
Referenced files must exist inside the checkout, match their hashes and remain
unchanged. Keep generated reports in Git-ignored paths. Source and tests must not
be ignored. The controller rejects symlink source inputs.

Additional required fields:

| Phase | Evidence |
|---|---|
| company-context | Hashed `sources` array or `knowledge_gap: true` |
| refine, architecture, security-architecture, architecture-challenge, discovery, UX/UI, test-design, knowledge-proposal | Hashed `document` |
| brainstorm | Array `alternatives` containing at least two distinct strings |
| architecture-review | Hashed architecture `document`, `decision` with configured eligible voters, options, votes and selected option |
| plan | `tasks` declarations using approved templates; no executable command injection |
| test-design | `test_map`: every `R1::AC1` criterion → planned JUnit test IDs |
| red/green | Hashed `test_report` plus actual failing/passing test IDs matching JUnit |
| reviews/security/verification | `blocking_findings: []` |
| reviews/E2E/security/verification | `input_sha256` equal to `FACTORY_INPUT_SHA256` |
| E2E/verification | `coverage`: every criterion → list of hashed JUnit references with `test_ids` |
| verification | All `gates` true; actual absolute `artifact_path` and `artifact_sha256` |
| deploy | Same `artifact_sha256` as independently verified artifact |
| deployment-verification | `observed_artifact_sha256`, exact `target`, `healthy: true`, hashed observation `document` |

A coverage reference is:

```json
{"path":".factory-state/evidence/e2e.xml","sha256":"REPORT_HASH","test_ids":["tests.test_api::test_error_path"]}
```

Verification commands are operator-owned adapters. Each must run actual tools
and write a fresh report to `FACTORY_GATE_REPORT`:

```json
{"input_sha256":"CURRENT_INPUT_HASH","checks":[{"id":"actual-check-name","passed":true}]}
```

Final verification requires nine gate adapters: `build`, `unit`, `integration`,
`dependencies`, `iac`, `provenance`, `rollback`, `network-security` and
`observability`. TDD, criterion-level E2E coverage and security are separately
enforced steps; the legacy `FactoryState` inventory of 13 booleans is not the
execution contract.

A successful exit without this report cannot pass. Adapters must derive checks
from real tool results, never synthesize success or silently skip unavailable
scanners. The example checks file names application-specific adapters on purpose;
`doctor` blocks their absence. The factory does not bundle every language scanner,
AWS test environment or mutation engine.

Use `software_factory.test_receipt` for TDD and
`software_factory.acceptance_runner` for E2E. They execute configured commands
and parse fresh JUnit rather than trusting an LLM's claimed test results. Test IDs
are `classname::name`; duplicate IDs, missing tests, execution errors, failed
coverage and skipped-only green runs do not satisfy evidence requirements.

## Production authority

`delivery: deploy` requires `assurance: isolated`. Provision a privileged POSIX
controller with SETUID/SETGID capability, a root-owned mode-0700 state directory
outside the checkout, and distinct non-root worker UIDs/GIDs. Configure:

```json
{
  "runtime": {
    "approval_key": "/trusted/approval.key",
    "telemetry_key": "/trusted/telemetry.key",
    "verification_actor": "trusted-check-runner",
    "principals": {"trusted-check-runner":{"uid":1001,"gid":1001}},
    "trusted_files": [{"path":"/opt/factory/adapters/check.py","sha256":"PINNED_HASH"}]
  }
}
```

Provision a principal for every actor. Keys contain at least 32 random bytes,
are controller-owned mode 0600, and remain outside the checkout. Trusted adapters
and artifact files, including their parent paths, must be root-owned and not
worker-writable. Pin executable binaries, adapter entry-point files and their dependencies in `trusted_files`.
Isolated mode rejects inline `-c` code and unpinned entry points. Use pinned scripts
for non-factory Python modules.
Provision worker access to only their required source/output paths and provider
credentials. The installer does not create privileged users, containers or IAM.
Do not grant workers sudo, approval keys, controller storage or shared production
credentials. The controller drops supplementary groups and does not forward its
credential environment. Use controlled credential brokers for worker access.

The CLI signs an approval only after interactive operator confirmation. The
receipt binds run identity, phase, history, manifest, source and deployment scope.
Key possession is the authentication boundary; a terminal prompt alone is not.
The administrator and trusted receipt broker are inside the trust boundary.

A trusted runtime broker must sign each agent's `runtime_receipt`, using the
telemetry key; ordinary agent output is not authoritative. Receipt `body` contains
run_id, attempt_id, phase, input_sha256, actor, resolved_model, input_tokens, output_tokens and
cost_microunits. `signature` is HMAC-SHA256 over canonical sorted compact JSON.
Each council ballot similarly needs a signed body with run_id, actor, phase,
input_sha256 and the exact `vote`. Missing/mismatched receipts stop isolated work.
The stock native adapter does not provide a trusted broker; deployment remains
blocked until one is integrated. Do not share the signing key with workers.

Optional `budget` caps `tokens` and `cost_microunits` before the next step based on
verified receipts. A running request can exceed the remaining budget: configure
per-request hard limits in the provider broker. Unverified local usage is unknown.

`deployment` binds account, region, environment and a hashed IaC `plan`. Rehash
that plan and artifact before deployment. The adapter must deploy the supplied
`FACTORY_APPROVED_ARTIFACT_PATH`/`FACTORY_APPROVED_ARTIFACT_SHA256` to
`FACTORY_DEPLOYMENT_TARGET`. A distinct deployment-verification principal must
query the actual environment and report its observed digest and health. Do not
rebuild, infer deployment success, or automatically correct production drift.
