.PHONY: assets
assets: ## Fetch and verify model and dataset assets
> .venv/bin/python scripts/fetch_assets.py

.PHONY: model-smoke
model-smoke: ## Run model smoke test
> bash loop/model/smoke.sh

.PHONY: loop
loop: ## Run 3-round defense progression loop (SIZE=demo|full)
> @.venv/bin/python -m loop.scoring.run --family F1 --size $(or $(SIZE),demo)

.PHONY: report
report: ## Regenerate docs/RESULTS.md and evidence/report.json
> @.venv/bin/python evidence/report_gen.py
