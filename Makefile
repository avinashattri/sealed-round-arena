.RECIPEPREFIX := >
SHELL := /bin/bash
.DEFAULT_GOAL := help

-include make/*.mk

.PHONY: help
help: ## Show help summary
> @echo "Sealed Round Arena - Makefile"
> @grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
