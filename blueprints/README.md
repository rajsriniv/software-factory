# Blueprints

These are intentionally small starting points. The Java and Python services expose a minimal API, the React template includes Playwright, and Terraform demonstrates immutable artifact input and encrypted logs. Container builds require `--build-arg BASE_IMAGE=<registry/image@sha256:digest>`; no mutable default is provided. Generate and commit lockfiles in product repositories; Dependabot/Renovate should manage upgrades. Add workload-specific networking, compute, IAM, scaling, observability, data stores, budgets, alarms, deployment strategy, and rollback.

The Terraform sample does not deploy a compute service. Selecting ECS, EKS, Lambda, Glue, or another AWS runtime is an architecture decision based on workload requirements, not a factory default.

## Local build entry points

Run commands inside the corresponding blueprint directory after installing its
declared toolchain and dependencies:

| Blueprint | Build or verification entry point |
| --- | --- |
| Java | JDK 21 and Maven; `mvn test` or `mvn package` |
| Python | Python 3.11+; `python3 -m pip install -e '.[dev]'`, then `python3 -m pytest` |
| React | Install dependencies with npm; `npm run build` and `npm run test:e2e` (install Playwright browsers first) |
| AWS Terraform | Configure backend/variables; `terraform fmt -check`, `terraform init`, `terraform validate`, then review a real plan |

The Playwright configuration does not start a web server. Serve the built React
application at `http://127.0.0.1:4173` or set `BASE_URL` to the authorized test
environment before running E2E tests.

The example factory Java profile uses Gradle; override it for the Maven blueprint.
Rust service and GTK4/Iced desktop workflows have skill guidance and a role, but
no Rust blueprint is supplied. Repository CI validates blueprint manifests and
container-base declarations only; it does not run these application builds or E2E
suites. See [GitHub/AWS setup](../docs/operations/github-setup.md) for the standalone
Terraform workflow and its integration limits.
