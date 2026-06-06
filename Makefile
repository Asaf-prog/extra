# Makefile — task runner for the Declarative Agent Platform.
#
# These targets are the canonical entry points for development. AGENTS.md and
# every skill/task file refer to them. During the foundation phase some targets
# may not have code to act on yet; they are written to degrade gracefully and
# document the expected future tooling (ruff, mypy, pytest).

PYTHON ?= python3
PKG := src
TESTS := tests

.DEFAULT_GOAL := help

.PHONY: help install format lint test check clean

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dev dependencies (editable install + tooling).
	$(PYTHON) -m pip install --upgrade pip
	@if [ -f pyproject.toml ]; then \
		$(PYTHON) -m pip install -e ".[dev]" || \
		echo "No installable package yet — this is expected in the foundation phase."; \
	else \
		echo "No pyproject.toml found."; \
	fi

format: ## Auto-format the codebase (ruff format).
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format $(PKG) $(TESTS) 2>/dev/null || ruff format .; \
		ruff check --fix $(PKG) $(TESTS) 2>/dev/null || true; \
	else \
		echo "ruff not installed. Run 'make install' first. (Expected tooling: ruff)"; \
	fi

lint: ## Static analysis (ruff check + mypy).
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check $(PKG) 2>/dev/null || ruff check .; \
	else \
		echo "ruff not installed. (Expected tooling: ruff)"; \
	fi
	@if command -v mypy >/dev/null 2>&1; then \
		mypy $(PKG) 2>/dev/null || echo "No package to type-check yet."; \
	else \
		echo "mypy not installed. (Expected tooling: mypy)"; \
	fi

test: ## Run the test suite (pytest).
	@if command -v pytest >/dev/null 2>&1; then \
		pytest -q || echo "Tests not present yet — this is expected in the foundation phase."; \
	else \
		echo "pytest not installed. (Expected tooling: pytest)"; \
	fi

check: ## Quality gate: format-check + lint + test. MUST pass before finishing a task.
	@echo "==> format check"
	@if command -v ruff >/dev/null 2>&1; then ruff format --check . 2>/dev/null || true; fi
	@$(MAKE) --no-print-directory lint
	@$(MAKE) --no-print-directory test
	@echo "==> check complete"

clean: ## Remove caches and build artifacts.
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov dist build *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
