# Contributing

Use a focused branch and pull request. Explain the problem, architecture impact, behavior change, tests, security implications, and rollback. Add an ADR for consequential design choices. Preserve backwards compatibility or document an approved migration.

Before opening a pull request:

```bash
python -m ruff check .
python -m mypy src
python -m pytest
software-factory validate-config config/factory.example.yaml
```

Do not weaken gates to merge a change. Generated evidence must come from executed tools and reference the exact commit. Changes to governance, release policy, decision math, message schemas, or production permissions require CODEOWNERS review.


## Keeping behavior and documentation aligned

When adding a role, keep the installer, example configuration, tier validation,
role tests and README role inventory consistent. Put detailed workflow guidance in
`skills/software-factory/references/` and link it from the README. Workflow guidance
must distinguish instructions from checks actually enforced by the controller.

When changing CLI arguments, update the [local operations guide](docs/operations/local-workflows.md)
and check examples against command help. Update the Unreleased changelog for
user-visible changes. Gate changes must update applicable legacy pipeline and execution-controller
tests, plus architecture and governance gate inventories. Keep the legacy
13-record inventory separate from version-two execution steps and its nine final
verification adapters. Company Brain and improvement-store changes need
coverage for scope, expiry/approval boundaries and invalid inputs as applicable.

The CI control-plane job runs lint, type checks, tests and configuration validation.
The blueprint job checks manifests and container-base declarations; it does not
build the Java/React/Python applications or execute their E2E suites. Passing this
CI workflow alone is not evidence that all factory release gates passed.

For execution changes, update both the spec workflow and runtime contract, the
initializer/examples, local operations and the README. Check approval ordering,
assurance boundaries, criterion-to-JUnit coverage and repair behavior against the
controller. Keep role/profile YAML schema versions separate from execution
manifest versions. Documentation-only changes require link, example and factual
consistency checks; do not invent application test evidence for prose edits.

Use installed distribution metadata (`importlib.metadata.version` with package
name `sdlc-software-factory`) for the package version. The project metadata is
0.2.0; the legacy module `__version__` constant remains 0.1.0. Keep that discrepancy
visible until a separately reviewed code correction aligns it.
