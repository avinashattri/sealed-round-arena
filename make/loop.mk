.PHONY: assets
assets: ## Fetch and verify model and dataset assets
> .venv/bin/python scripts/fetch_assets.py

.PHONY: model-smoke
model-smoke: ## Run model smoke test
> bash loop/model/smoke.sh
