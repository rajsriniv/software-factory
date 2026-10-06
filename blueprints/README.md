# Blueprints

These are intentionally small starting points. The Java and Python services expose a minimal API, the React template includes Playwright, and Terraform demonstrates immutable artifact input and encrypted logs. Container builds require `--build-arg BASE_IMAGE=<registry/image@sha256:digest>`; no mutable default is provided. Generate and commit lockfiles in product repositories; Dependabot/Renovate should manage upgrades. Add workload-specific networking, compute, IAM, scaling, observability, data stores, budgets, alarms, deployment strategy, and rollback.

The Terraform sample does not deploy a compute service. Selecting ECS, EKS, Lambda, Glue, or another AWS runtime is an architecture decision based on workload requirements, not a factory default.
