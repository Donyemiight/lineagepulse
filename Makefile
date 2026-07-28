PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: help install dev test smoke demo demo-pii lint fmt clean

help:
	@echo "LineagePulse — DataHub Agent Hackathon submission"
	@echo ""
	@echo "Targets:"
	@echo "  install    Install the package and dev deps into a venv"
	@echo "  dev        Install in editable mode"
	@echo "  test       Run unit tests"
	@echo "  smoke      Run the end-to-end smoke test (DRY_RUN)"
	@echo "  demo       Run the demo runbook (writes to examples/demo_output/)"
	@echo "  demo-pii   Run the PII/governance demo (writes to examples/demo_output_pii/)"
	@echo "  lint       Run ruff + black check"
	@echo "  fmt        Auto-format with black + ruff --fix"
	@echo "  clean      Remove build artifacts"

$(VENV)/bin/python:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip

install: $(VENV)/bin/python
	$(BIN)/pip install -r requirements.txt

dev: $(VENV)/bin/python
	$(BIN)/pip install -e ".[dev]"

test:
	$(BIN)/python -m pytest tests/ -v

smoke:
	$(BIN)/python scripts/smoke_test.py

demo:
	$(BIN)/python scripts/demo_runbook.py

demo-pii:
	$(BIN)/python scripts/demo_runbook_pii.py

lint:
	$(BIN)/python -m ruff check src scripts tests
	$(BIN)/python -m black --check src scripts tests

fmt:
	$(BIN)/python -m black src scripts tests
	$(BIN)/python -m ruff check --fix src scripts tests

clean:
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache
	rm -f examples/last_demo_run.json
	rm -f examples/smoke_test_output.json
	rm -rf examples/demo_output/incident.json examples/demo_output/report.json
	rm -rf examples/demo_output_pii/incident.json examples/demo_output_pii/report.json
