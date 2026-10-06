# Local factory operations

Run commands from the repository root after installing the Python package as shown
in the [README](../../README.md). The CLI records and retrieves local data; it does
not run the entire agent workflow automatically.

## Configuration and role definitions

```sh
software-factory validate-config config/factory.example.yaml
software-factory --help
```

Replace `high-model-id` and `low-model-id` with explicit models available in your
host. Validation accepts nonempty placeholder labels; it does not check model
availability. The installer defines 23 roles, with Java, Python and React assigned
the lower tier and the remaining roles assigned the higher tier. Its `--host`,
`--high-model`, `--low-model` and `--destination` arguments are required:

```sh
python scripts/install_agents.py --help
```

The installer copies the skill and role files beneath the supplied destination.
Different existing contents stop installation unless `--replace` is supplied;
review those changes before replacement. Generation alone does not verify live
host compatibility, provision tools or run agents.

The Java blueprint uses Maven (`pom.xml`), while the example profile specifies
`./gradlew build`. Set the profile to your actual project build command before use;
for the supplied blueprint that is `mvn test` or `mvn package` in its directory.

## Messages and channels

```sh
software-factory send --ledger .factory-state/ledger.db \
  --channel factory-design --sender ux --recipient reviewer \
  --kind design-review --correlation demo-task \
  --payload '{"requirement_ids":["REQ-001"],"status":"ready-for-review"}'
software-factory inbox --ledger .factory-state/ledger.db \
  --recipient reviewer --channel factory-design --after 0
software-factory verify-ledger .factory-state/ledger.db
```

The example sends a local ledger message; it does not contact or launch an agent.
`send` defaults to `factory-general`. Omitting `inbox --channel` includes all
channels for that recipient, including broadcasts to `*`; `--after` is an event sequence cursor. Channels organize
messages and are not access-control boundaries. Hash-chain verification detects
chain inconsistency, not authenticated authorship or externally anchored history.

## Company Brain

Use [Company Brain onboarding](../../skills/software-factory/references/company-brain.md)
for `brain-ingest` and `brain-query` examples. Imports require company, source,
file, owner, a future timezone-aware expiry and explicit permitted role IDs.
Repeated imports preserve source revisions. Queries use the latest revision of
each source and exclude expired or role-ineligible sources; they do not fall back
to an older revision. Word overlap determines matches.

`--max-chars` defaults to 6000 and allows 1–20000 characters of excerpt content.
The result includes source revisions, hashes, owners, expiry and truncation flags.
A `knowledge-gap` response means no eligible lexical match, not proof that the
company has no relevant knowledge. Provision approved documents and access controls
separately; never import credentials.

## Prompt/workflow improvement

```sh
software-factory improvement --help
```

The supported actions are `propose`, `evaluate`, `compare`, `rank`, `inspect`,
`assessment` and `select`. Every action requires `--database`; actions other than
`propose` and `compare` also require `--candidate`. Supply operation JSON using
`--input` when proposing, evaluating, comparing or selecting. Follow the complete
[payload and evidence contract](../../skills/software-factory/references/improvement.md).

The sequence is proposal, actual external evaluation, evidence import, optional
pairwise comparison/ranking, benchmark and independent review, assessment hash,
then exact human-approved selection. Selection never changes live agents. The
host and evaluation harness enforce identity, spending and actual execution.

## Storage and verification

Use a controlled location for ledger, knowledge and improvement databases, state
snapshots and evidence. `.factory-state` is the example state-directory setting;
CLI database paths are supplied explicitly and are not loaded from that setting.
Restrict local access and back up retained evidence. Avoid committing sensitive
company documents, databases, logs or credentials.

Run the checks listed in [Contributing](../../CONTRIBUTING.md). Tests cover local
logic; live host integration, application E2E runs and AWS deployment require
separate evidence. See [GitHub and AWS setup](github-setup.md) for deployment scope
and configuration alignment.
