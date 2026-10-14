#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Firewall Negative Test ==="
echo "1. Applying firewall rules..."
bash infra/firewall/apply.sh

echo "2. Starting hardened stack with leaky override (red_net internal:false)..."
.venv/bin/python scripts/make_canaries.py --profile hardened
docker compose --project-directory . \
  -f infra/compose/hardened.yml \
  -f infra/compose/override-leaky.yml \
  up -d broker red

echo "3. Running B1 probe from red_probe with firewall ON (Expect HELD)..."
.venv/bin/python run_probes.py --profile hardened --only B1

echo "4. Removing firewall rules..."
bash infra/firewall/remove.sh

echo "5. Running B1 probe from red_probe with firewall OFF (Expect LEAK)..."
.venv/bin/python run_probes.py --profile hardened --only B1

echo "6. Restoring firewall rules and cleaning up override..."
bash infra/firewall/apply.sh
docker compose --project-directory . -f infra/compose/hardened.yml down -v --remove-orphans
echo "=== Firewall Negative Test Passed ==="
