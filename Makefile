.RECIPEPREFIX := >
SHELL := /bin/bash
.DEFAULT_GOAL := help

-include make/*.mk

.PHONY: help
help: ## Show help summary
> @echo "Sealed Round Arena - Makefile"
> @grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: setup
setup: assets images-build pin check-env ## Set up assets, build images, pin locks, check environment
> @echo "Setup complete! Ready to run 'make demo FAST=1' or 'make replay'."

.PHONY: test
test: ## Run full test suite
> .venv/bin/pytest tests referee contracts loop/oracle -q

.PHONY: lint
lint: ## Run linter checks
> .venv/bin/ruff check .
> .venv/bin/ruff format --check .
