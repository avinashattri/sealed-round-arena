.RECIPEPREFIX := >
SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help
help: ## Show help summary
> @echo "Sealed Round Arena - Makefile"
