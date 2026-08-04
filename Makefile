.PHONY: install test compile shell hygiene build check quality audit

install:
	python -m pip install -e ".[test]"

test:
	pytest --cov --cov-report=term-missing

compile:
	python -m compileall -q src tests __init__.py

shell:
	bash -n scripts/install.sh scripts/install-dual.sh scripts/uninstall.sh scripts/live-smoke-test.sh

build:
	python -m build

check: compile shell hygiene test build

hygiene:
	python scripts/check-release-tree.py

quality:
	ruff check src tests
	ruff format --check src tests
	mypy src

audit:
	pip-audit
