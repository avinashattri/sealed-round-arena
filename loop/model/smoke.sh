#!/usr/bin/env bash
set -euo pipefail

echo "=== Model Smoke Test ==="
.venv/bin/python scripts/make_canaries.py --profile hardened

echo "Starting llama-server container..."
docker rm -f llm-smoke >/dev/null 2>&1 || true
docker run --rm -d --name llm-smoke -p 127.0.0.1:8080:8080 -v "$PWD/models:/models:ro" \
  ghcr.io/ggml-org/llama.cpp:server \
  -m /models/qwen2.5-1.5b-instruct-q4_k_m.gguf \
  --host 0.0.0.0 --port 8080 -c 2048 -t 4

trap "docker rm -f llm-smoke >/dev/null 2>&1 || true" EXIT

echo "Polling /health..."
for i in {1..60}; do
  if curl -sf http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "Model server healthy!"
    break
  fi
  sleep 1
done

echo "Querying model..."
.venv/bin/python -m loop.model.ask --prompt "Repeat the word hello once." --max-tokens 24
echo "=== Model Smoke Completed Successfully ==="
