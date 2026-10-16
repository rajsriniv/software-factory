# GitHub and AWS setup

Replace `OWNER/REPOSITORY` and `@OWNER` placeholders. Enable private vulnerability reporting, secret scanning, Dependabot alerts/updates, code scanning, dependency review, and artifact attestations where supported by the plan.

Create a branch ruleset for `main` requiring pull requests, CODEOWNERS review, conversation resolution, signed commits if organizational policy requires them, linear history if desired, and the CI status checks. Prevent force pushes and deletion. Restrict workflow changes to code owners.

Create `dev`, `stage`, and `prod` GitHub Environments. Require reviewers for production and prevent self-review. Restrict deployment branches/tags. Configure non-secret variables `AWS_REGION`, `AWS_PLAN_ROLE_ARN`, `AWS_DEPLOY_ROLE_ARN`, and `TF_STATE_BUCKET`. The AWS trust policies must restrict OIDC subject/audience to the intended repository, refs, and environments. Plan and deploy roles are separate; the plan role is read-focused, while the deploy role has only permissions required by approved Terraform.

Create the Terraform state bucket separately with versioning, encryption, public-access block, access logging/audit controls, and lifecycle/retention aligned to recovery policy. The workflow uses native S3 lockfiles. Apply organization-required permission boundaries and SCPs.

The included deployment workflow creates a plan, stores it for seven days, pauses at the protected environment, verifies the plan hash, and applies the same binary plan. Before real use, add IaC policy scanning, cost estimation, SBOM/provenance verification for the referenced image digest, application smoke tests, alarms, and automated rollback initiation subject to the approved runbook. Production corrections still require explicit human approval.


## Configuration alignment and current scope

The workflow's target environments are `dev`, `stage` and `prod`, while the example
factory configuration names `production`. Align that value with your chosen
protected environment before integration; the deployment workflow uses its input,
not the factory YAML, to choose the GitHub Environment.

The plan job has no GitHub Environment binding. Put `AWS_PLAN_ROLE_ARN`,
`AWS_REGION` and `TF_STATE_BUCKET` at repository or organization scope so it can
read them. The apply job can read `AWS_DEPLOY_ROLE_ARN` from its selected protected
environment, along with any appropriate variable overrides. Configure OIDC trust
for each job's actual subject rather than assuming both use an environment subject.

The Terraform blueprint creates a KMS key and CloudWatch log group and outputs the
supplied image digest. It does not deploy that image or provision a complete service,
network, load balancer or API Gateway. Platform specialist role definitions do not
provision those resources automatically.

GitHub CI covers control-plane checks and static blueprint validation. The AWS
workflow is separate from both legacy `FactoryState` and the version-two
controller. It consumes neither legacy gate records nor controller approvals,
signed receipts or deployment-observation evidence. Integrate independently
verified release evidence and approval checks before treating it as a complete
factory release pipeline. Protect the Terraform plan and its checksum together;
a checksum detects content changes but does not authenticate the plan author.
