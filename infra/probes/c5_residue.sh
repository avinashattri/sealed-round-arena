#!/bin/bash
set -euo pipefail

# infra/probes/c5_residue.sh: assert zero residue after reset/clean

# Canaries to check
MODEL_CANARY=$(cat secrets/model_canary.txt 2>/dev/null || echo "")
RED_CANARY=$(cat secrets/red_canary.txt 2>/dev/null || echo "")
BLUE_CANARY=$(cat secrets/blue_canary.txt 2>/dev/null || echo "")

FAILED_CHECKS=()

# 1. Check containers
CONTAINERS=$(docker ps -a --filter "name=sra-" --format '{{.Names}}' || true)
if [ -n "$CONTAINERS" ]; then
    FAILED_CHECKS+=("lingering containers: $(echo "$CONTAINERS" | tr '\n' ' ')")
fi

# 2. Check volumes
VOLUMES=$(docker volume ls --filter "name=sra-" --format '{{.Name}}' || true)
if [ -n "$VOLUMES" ]; then
    FAILED_CHECKS+=("lingering volumes: $(echo "$VOLUMES" | tr '\n' ' ')")
fi

# 3. Check networks
NETWORKS=$(docker network ls --filter "name=sra-" --filter "name=br-sra" --format '{{.Name}}' || true)
if [ -n "$NETWORKS" ]; then
    FAILED_CHECKS+=("lingering networks: $(echo "$NETWORKS" | tr '\n' ' ')")
fi

# 4. Check secrets and shared directories
if [ -d "secrets" ] && [ "$(ls -A secrets 2>/dev/null)" ]; then
    FAILED_CHECKS+=("secrets/ dir not empty")
fi
if [ -d "shared" ] && [ "$(ls -A shared 2>/dev/null)" ]; then
    FAILED_CHECKS+=("shared/ dir not empty")
fi

# 5. Check canary residue in /tmp and ~/.cache
for CANARY in "$MODEL_CANARY" "$RED_CANARY" "$BLUE_CANARY"; do
    if [ -n "$CANARY" ]; then
        if grep -rq "$CANARY" /tmp 2>/dev/null; then
            FAILED_CHECKS+=("canary found in /tmp")
            break
        fi
        if [ -d "$HOME/.cache" ] && grep -rq "$CANARY" "$HOME/.cache" 2>/dev/null; then
            FAILED_CHECKS+=("canary found in ~/.cache")
            break
        fi
    fi
done

if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo '{"probe": "C5", "verdict": "HELD", "evidence": "Zero residue: 0 containers, 0 volumes, 0 networks, empty secrets/shared, 0 canary matches in /tmp or ~/.cache"}'
    exit 0
else
    EVIDENCE=$(IFS='; '; echo "${FAILED_CHECKS[*]}")
    echo "{\"probe\": \"C5\", \"verdict\": \"LEAK\", \"evidence\": \"Residue detected: $EVIDENCE\"}"
    exit 1
fi
