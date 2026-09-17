.PHONY: install lint typecheck test validate
install:
	python -m pip install -e '.[dev]'
lint:
	ruff check .
typecheck:
	mypy src
test:
	pytest
validate: lint typecheck test
	software-factory validate-config config/factory.example.yaml

