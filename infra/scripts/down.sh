#!/usr/bin/env bash
set -euo pipefail

PROFILE="${1:-naive}"
COMPOSE_FILE="infra/compose/${PROFILE}.yml"

if [ -f "$COMPOSE_FILE" ]; then
    docker compose --project-directory . -f "$COMPOSE_FILE" down -v --remove-orphans
fi
