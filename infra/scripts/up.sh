#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-naive}"

if [ "${KEEP_SECRETS:-0}" != "1" ]; then
    .venv/bin/python scripts/make_canaries.py --profile "$PROFILE"
fi

if [ "$PROFILE" = "hardened" ]; then
    BOOT_ID="$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || true)"
    FW_BOOT_ID="$(cat evidence/.fw_boot_id 2>/dev/null || true)"
    if [ "$FW_BOOT_ID" != "$BOOT_ID" ]; then
        echo "NEED YOU: run \`make fw-on\` in my Ubuntu terminal. Reply done."
        exit 3
    fi
fi

COMPOSE_FILE="infra/compose/${PROFILE}.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "Compose file not found: $COMPOSE_FILE"
    exit 1
fi

echo "Starting compose project sra-${PROFILE}..."
docker compose --project-directory . -f "$COMPOSE_FILE" up -d --wait --wait-timeout 180

# Poll model health
echo "Polling model health..."
for i in {1..60}; do
    if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1 || [ "$(docker inspect --format '{{.State.Health.Status}}' sra-hardened-model 2>/dev/null)" = "healthy" ] || [ "$(docker inspect --format '{{.State.Health.Status}}' sra-hardened-stubmodel 2>/dev/null)" = "healthy" ]; then
        echo "Model is healthy."
        break
    fi
    sleep 1
done

docker compose --project-directory . -f "$COMPOSE_FILE" ps
