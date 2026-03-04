PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest
RUFF ?= $(PYTHON) -m ruff
BLACK ?= $(PYTHON) -m black
MYPY ?= $(PYTHON) -m mypy
SPHINX ?= $(PYTHON) -m sphinx
BUILD ?= $(PYTHON) -m build
TWINE ?= $(PYTHON) -m twine

.PHONY: help dev install-dev lint fmt fmt-check type test qa coverage \
	examples-smoke examples-test docs docs-build docs-check docs-linkcheck \
	release-check ci clean

help:
	@echo "Common targets:"
	@echo "  dev            Install project in editable mode with dev dependencies."
	@echo "  test           Run the default pytest suite."
	@echo "  qa             Run lint, formatting, typing, and tests."
	@echo "  docs           Build Sphinx documentation."
	@echo "  release-check  Build distributions and validate metadata."
	@echo "  clean          Remove generated artifacts."

dev:
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

install-dev: dev

lint:
	$(RUFF) check .

fmt:
	$(BLACK) .

fmt-check:
	$(BLACK) --check .

type:
	$(MYPY) src

test:
	PYTHONPATH=src $(PYTEST) -q

qa: lint fmt-check type test

coverage:
	mkdir -p artifacts/coverage
	PYTHONPATH=src $(PYTEST) --cov=tigl_mcp_server --cov-report=term --cov-report=json:artifacts/coverage/coverage.json -q
	$(PYTHON) scripts/check_coverage_thresholds.py --coverage-json artifacts/coverage/coverage.json

examples-smoke:
	PYTHONPATH=src $(PYTEST) -m examples_smoke -q

examples-test:
	PYTHONPATH=src $(PYTEST) -m "examples_smoke or examples_full" -q

docs-build:
	$(PYTHON) scripts/generate_example_docs.py
	PYTHONPATH=src $(SPHINX) -b html docs docs/_build/html -n -W --keep-going -E

docs-check:
	$(PYTHON) scripts/generate_example_docs.py --check
	$(PYTHON) scripts/check_docs_consistency.py

docs-linkcheck:
	$(PYTHON) scripts/generate_example_docs.py --check
	PYTHONPATH=src $(SPHINX) -b linkcheck docs docs/_build/linkcheck -W --keep-going -E

docs: docs-build

release-check:
	rm -rf dist build
	$(BUILD) --no-isolation
	$(TWINE) check dist/*

ci: qa coverage docs-check examples-smoke

clean:
	rm -rf .coverage .mypy_cache .pytest_cache .ruff_cache artifacts build dist docs/_build src/*.egg-info src/tigl_mcp.egg-info src/tigl_mcp_server.egg-info
	find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
	find . -type f \( -name "*.pyc" -o -name ".coverage.*" \) -exec rm -f {} + 2>/dev/null || true
