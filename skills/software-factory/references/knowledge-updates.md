# Project knowledge handoff

At human-approved architecture and independently verified project milestones, have Company Brain prepare durable knowledge proposals: approved ADRs, service contracts, code maps, configuration standards, runbooks and verified observability/security decisions. Use actual artifacts and cite repository revisions and evidence. Summaries require independent review for correctness, unsupported assumptions and sensitive information. Do not promote raw task conversations, secrets, customer data or speculative conclusions. Project work may automatically prepare proposals; publication always waits for explicit human approval.

The current host workflow invokes these commands; no background project scanner or autonomous orchestrator is installed. Refine the proposal if human review requests changes; every changed proposal requires fresh review and approval.

## Proposal contract and workflow

Save a proposal JSON with exactly these fields:

```json
{
  "company": "my-company",
  "source": "projects/example/architecture",
  "content": "The approved architecture document or reviewed summary.",
  "owner": "platform-team",
  "expires": "2027-01-01T00:00:00+00:00",
  "roles": ["company-brain", "architect", "planner", "reviewer"],
  "task_id": "PROJECT-1",
  "repository_revision": "EXACT-COMMIT-ID",
  "author": "company-brain",
  "evidence": ["approved-architecture.md#ACTUAL-SHA256"]
}
```

Replace placeholders with real approved evidence. The proposal ID hashes the document, company/source, role scope, expiry, provenance and source's current base revision. Proposals are kept separate from retrievable knowledge. `inspect` returns the complete proposed and previous content for human comparison. Use the same source ID to evolve a document.

```sh
software-factory brain-updates propose --database /secure/company/brain.db --input proposal.json
software-factory brain-updates inspect --database /secure/company/brain.db --proposal PROPOSAL-ID
software-factory brain-updates review --database /secure/company/brain.db --proposal PROPOSAL-ID \
  --actor reviewer --evidence 'review-receipt#HASH' --pass-review
software-factory brain-updates approve --database /secure/company/brain.db --proposal PROPOSAL-ID \
  --actor human-owner --evidence 'human-approval-reference'
software-factory brain-updates publish --database /secure/company/brain.db --proposal PROPOSAL-ID
```

The human runs `approve` in an interactive terminal, reviews the displayed package and types `APPROVE PROPOSAL-ID` exactly. It refuses noninteractive stdin; agents must never supply this confirmation on the human's behalf. Omit `--pass-review` to record a failed review. Use `reject --actor human-owner --evidence 'reason'` to reject an unpublished proposal. Failed reviews are terminal for that proposal; create a revised proposal for another review.

`publish` is the post-approval automation: it atomically imports the exact approved document and updates publication state, then rebuilds the company's vector index using the configured/default model. Set `--model` to the existing index model if different. Install `.[brain]` and provision the approved cached model first. Source changes since proposal creation block publication. Expired proposals require a new proposal/approval. All imports preserve source history.

If model/dependency or indexing fails after import, state is `index-pending`; rerun `publish` after correcting the environment. Retry refreshes the index without a second knowledge revision. Lexical retrieval can see the approved imported document immediately; vector retrieval rejects incomplete/latest-source indexes until rebuilt. Already published proposals are idempotent. The vector transaction protects the prior index against partial rebuild.

## Human-visible audit and boundaries

```sh
software-factory brain-updates events --database /secure/company/brain.db --task-id PROJECT-1
```

The dedicated `factory-knowledge` event stream records proposal contents, review, explicit approval, rejection, import and indexing outcome, in the same SQLite database. It is read with `brain-updates events`, separately from the agent-message ledger. Announce proposal IDs and milestone handoffs through `factory-collaboration`; post human review requests to `factory-approvals`. Avoid copying secrets into either stream.

The API trusts the local caller and reviewer identity; terminal confirmation prevents accidental noninteractive approval but is not identity authentication or protection against an agent with terminal/database access. Use host permissions to deny approval commands and direct database writes to worker agents. `brain-ingest` remains a privileged manual onboarding bypass: worker agents must not use it for project promotion. Restrict it accordingly. Stored evidence references are independently checked by reviewers; code does not verify signatures, secret absence, or artifact claims. No production correction or deployment is authorized by knowledge approval.
