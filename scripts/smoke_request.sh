#!/usr/bin/env bash
set -euo pipefail

echo "=== Smoke Request Test ==="

# 1. State transitions via broker admin
echo "Transitioning broker state to EXECUTING..."
docker compose --project-directory . -f infra/compose/hardened.yml exec -T broker \
  python -m referee.broker.admin move COMMITTED >/dev/null

docker compose --project-directory . -f infra/compose/hardened.yml exec -T broker \
  python -m referee.broker.admin move SEALED >/dev/null

docker compose --project-directory . -f infra/compose/hardened.yml exec -T broker \
  python -m referee.broker.admin move EXECUTING >/dev/null

TOKEN_RED="$(cat secrets/token_red.txt 2>/dev/null || cat /run/secrets/token_red 2>/dev/null || echo '')"

# 2. Submit from Red container
echo "Sending submit request from Red container..."
SUBMIT_PAYLOAD='{"campaign_id":"c-001","round_id":"r-001","challenge_id":"ch-0001","payload":"Hello from Red zone"}'

RESP=$(docker compose --project-directory . -f infra/compose/hardened.yml exec -T red \
  python -c "
import urllib.request, json
req = urllib.request.Request(
    'http://broker:8000/submit',
    data=b'$SUBMIT_PAYLOAD',
    headers={'Authorization': 'Bearer $TOKEN_RED', 'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req, timeout=5)
print(resp.read().decode())
")

echo "Response from broker: $RESP"
if echo "$RESP" | grep -q '"status":"accepted"'; then
  echo "SMOKE REQUEST OK"
else
  echo "SMOKE REQUEST FAILED: unexpected response"
  exit 1
fi
