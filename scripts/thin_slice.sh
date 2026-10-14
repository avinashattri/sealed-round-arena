#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    docker rm -f slice_broker slice_blue slice_red >/dev/null 2>&1 || true
    docker network rm slice_a slice_b >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup

# 1. Build broker image
echo "Building broker image..."
docker build -q -f infra/docker/zone.Dockerfile \
  --build-arg COMPONENT=broker \
  --build-arg SRC=referee/broker \
  --build-arg PORT=8000 \
  -t sra/broker:dev . >/dev/null

# 2. Setup networks
docker network create --internal slice_a >/dev/null
docker network create --internal slice_b >/dev/null

# 3. Start services
docker run -d --name slice_blue --network slice_b python:3.12-slim python -m http.server 9000 >/dev/null
docker run -d --name slice_broker --network slice_a sra/broker:dev >/dev/null
docker network connect slice_b slice_broker >/dev/null

# Wait for broker health
for i in {1..30}; do
  if docker exec slice_broker python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

# 4. Probe from Red twin on net A: blue must NOT resolve
if docker run --rm --network slice_a python:3.12-slim python -c "import urllib.request; urllib.request.urlopen('http://slice_blue:9000', timeout=2)" >/dev/null 2>&1; then
  echo "FAIL: red was able to reach blue directly!"
  exit 1
else
  echo "red->blue: UNREACHABLE (expected)"
fi

# 5. Probe from Red twin on net A: broker must answer
if docker run --rm --network slice_a python:3.12-slim python -c "import urllib.request; assert urllib.request.urlopen('http://slice_broker:8000/health', timeout=2).status == 200" >/dev/null 2>&1; then
  echo "red->broker: OK"
else
  echo "FAIL: red cannot reach broker:8000/health"
  exit 1
fi

# 6. Audit & verify test
.venv/bin/python scripts/slice_audit.py

echo "SLICE OK"
