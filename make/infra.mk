.PHONY: slice
slice: ## Run thin slice test (networks, gateway, audit verify)
> bash scripts/thin_slice.sh

.PHONY: images-build
images-build: ## Build docker images (stub, probe, broker)
> docker build -f infra/docker/stub.Dockerfile -t sra/stub:dev .
> docker build -f infra/docker/probe.Dockerfile -t sra/probe:dev .
> docker build -f infra/docker/zone.Dockerfile --build-arg COMPONENT=broker --build-arg SRC=referee/broker --build-arg PORT=8000 -t sra/broker:dev .
> docker build -f infra/docker/zone.Dockerfile --build-arg COMPONENT=audit --build-arg SRC=referee/audit --build-arg PORT=7000 -t sra/audit:dev .

.PHONY: naive
naive: ## Start naive compose environment
> bash infra/scripts/up.sh naive

.PHONY: naive-down
naive-down: ## Stop naive compose environment
> bash infra/scripts/down.sh naive

.PHONY: probes
probes: ## Run probes (PROFILE=naive|hardened, ONLY=B1,B3,B4)
> .venv/bin/python run_probes.py --profile $(or $(PROFILE),naive) $(if $(ONLY),--only $(ONLY),)

.PHONY: clean
clean: ## Tear down all containers, volumes, and repo-local secrets/shared dirs
> @docker compose --project-directory . -f infra/compose/naive.yml --profile "*" down -v --remove-orphans >/dev/null 2>&1 || true
> @docker compose --project-directory . -f infra/compose/hardened.yml --profile "*" down -v --remove-orphans >/dev/null 2>&1 || true
> @for net in $$(docker network ls --filter name=sra- -q); do docker network rm $$net >/dev/null 2>&1 || true; done
> @rm -rf secrets shared
> @echo "Clean complete: stopped containers, removed volumes, removed secrets/ and shared/."

.PHONY: hardened
hardened: ## Start hardened compose environment
> bash infra/scripts/up.sh hardened

.PHONY: hardened-down
hardened-down: ## Stop hardened compose environment
> bash infra/scripts/down.sh hardened

.PHONY: fw-on
fw-on: ## Apply firewall backstop rules (sudo)
> bash infra/firewall/apply.sh

.PHONY: fw-off
fw-off: ## Remove firewall backstop rules (sudo)
> bash infra/firewall/remove.sh

.PHONY: pin
pin: ## Write image digests to locks/images.lock.json
> .venv/bin/python infra/scripts/pin.py write

.PHONY: check-env
check-env: ## Verify Docker, Python, model weights, datasets, image locks
> .venv/bin/python scripts/check_env.py
