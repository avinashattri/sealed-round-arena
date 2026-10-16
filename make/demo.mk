.PHONY: reveal-demo
reveal-demo: ## Mini round with tampered attack ch-0003 to assert commitment mismatch is caught at reveal
> @rm -f /tmp/reveal_demo.log
> @.venv/bin/python -m referee.controller run --campaign c-001 --round r-001 --attacks loop/data/attacks/F1.json --defense 1 --size mini --stub-model --stand-in-red --tamper-attack ch-0003 >/tmp/reveal_demo.log 2>&1 || true
> @if grep -q "COMMITMENT MISMATCH" /tmp/reveal_demo.log; then \
> 	echo "OK: the altered attack was caught"; \
> else \
> 	cat /tmp/reveal_demo.log; \
> 	echo "FAIL: COMMITMENT MISMATCH not caught"; exit 1; \
> fi

.PHONY: record
record: ## Copy validated evidence into replay/ and create meta.json
> @.venv/bin/python scripts/record.py

.PHONY: replay
replay: ## Re-render recorded demo offline without containers
> @.venv/bin/python scripts/demo.py --replay $(if $(SECTION),--section $(SECTION),)

.PHONY: demo
demo: ## Run live demonstration (FAST=1 skips metrics)
> @.venv/bin/python scripts/demo.py $(if $(SECTION),--section $(SECTION),) $(if $(FAST),--fast,)

.PHONY: dashboard
dashboard: ## Start Streamlit dashboard on port 8501
> @.venv/bin/streamlit run dashboard/app.py --server.address 0.0.0.0 --server.headless true --server.port 8501

.PHONY: ui-build
ui-build: ## Rebuild web/data.js bundle from current evidence or replay
> @.venv/bin/python scripts/build_ui_data.py

.PHONY: ui
ui: ui-build ## Start modern web console HTTP server on port 8080
> @echo "Starting Sealed-Round Arena Web Console on http://localhost:8080 ..."
> @python3 -m http.server 8080 --directory web
