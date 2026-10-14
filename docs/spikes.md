# Spike Results

## Network Isolation Spike (P0.T4)
Date: 2026-10-15
Objective: Verify Docker `--internal` bridge network isolation between zones and broker multi-homing.

### Configuration
- `spike_a`: Docker internal bridge (`--internal`)
- `spike_b`: Docker internal bridge (`--internal`)
- `spike_blue`: Container attached to `spike_b` only, running HTTP server on port 9000
- `spike_broker`: Container attached to `spike_a` and `spike_b`
- `spike_red` (test container): Container attached to `spike_a` only

### Results
1. **Direct cross-zone connection (Net A -> spike_blue on Net B)**:
   - Command: `docker run --rm --network spike_a python:3.12-slim python -c "import urllib.request;print(urllib.request.urlopen('http://spike_blue:9000',timeout=3).status)"`
   - Outcome: **FAILED** (`urllib.error.URLError: <urlopen error [Errno -3] Temporary failure in name resolution>`).
   - Verdict: Direct name resolution and packet routing between separate internal networks is completely blocked.

2. **Broker multi-homed gateway routing**:
   - Command: `docker exec spike_broker python -c "import urllib.request;print(urllib.request.urlopen('http://spike_blue:9000',timeout=3).status)"`
   - Outcome: **SUCCESS** (`200`).
   - Verdict: Multi-homed broker container can reach the internal services across its connected networks.

3. **Egress to public internet from internal network**:
   - Command: `docker run --rm --network spike_a python:3.12-slim python -c "import socket;socket.create_connection(('1.1.1.1',443),3)"`
   - Outcome: **FAILED** (`OSError: [Errno 101] Network is unreachable`).
   - Verdict: Default-deny egress holds on `--internal` networks.

## Model Speed and Seed Hunt Spike (P0.T5)
Date: 2026-10-15
Objective: Measure local LLM inference speed on CPU and verify extraction of un-hardened canary.

### Configuration
- Model: Qwen2.5-1.5B-Instruct-GGUF (Q4_K_M)
- Container: `ghcr.io/ggml-org/llama.cpp:server`
- Arguments: `-m /models/qwen2.5-1.5b-instruct-q4_k_m.gguf --host 0.0.0.0 --port 8080 -c 2048 -t 4`

### Results
1. **Smoke test inference speed**:
   - Prompt: "Repeat the word hello once." (max_tokens: 24, temperature: 0)
   - Reply: "Hello."
   - Latency: **0.51 s** (Requirement: < 15 s per reply. Passed with huge headroom).

2. **Seed Hunt Extraction Rate**:
   - Evaluated 20 harmless prompt injection candidates against system prompt containing canary `BYR-...`.
   - Result: **11/20 leaked** (55% leak rate on raw un-defended model; Requirement: >= 3/20).
   - Artifact: Written to `evidence/seed_hunt.json`.

## gVisor / runsc Spike (P0.T7)
Date: 2026-10-15
Objective: Verify gVisor `runsc` runtime integration with Docker Engine on Ubuntu 24.04.

### Results
- Host Kernel: `7.0.0-38-generic` (>= 5.6 required: PASS)
- `docker run --rm --runtime=runsc hello-world`: **PASSED** (exit code 0, "Hello from Docker!")
- `docker run --rm --runtime=runsc ubuntu dmesg`: **PASSED** (outputs `[ 0.000000] Starting gVisor...`)
- Verdict: `runsc` OCI runtime is functional and available for container sandboxing.
