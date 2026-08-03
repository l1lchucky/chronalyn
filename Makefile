.PHONY: install test compile shell build check quality audit

install:
	python -m pip install -e ".[test]"

test:
	pytest --cov --cov-report=term-missing

compile:
	python -m compileall -q src tests __init__.py

shell:
	bash -n scripts/install.sh scripts/uninstall.sh scripts/live-smoke-test.sh

build:
	python -m build

check: compile shell test build

quality:
	ruff check .
	ruff format --check .
	mypy

audit:
	pip-audit
