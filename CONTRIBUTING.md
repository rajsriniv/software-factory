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

