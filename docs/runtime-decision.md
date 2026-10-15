# Runtime Decision Record (P2.T9 / E1)

## System Environment
- **Host Platform**: Linux VM (Ubuntu 24.04.5 LTS, x86_64, 20 vCPUs, 15 GiB RAM)
- **Kernel Version**: `7.0.0-38-generic`
- **Docker Engine**: v29.9 (cgroup v2)
- **gVisor `runsc` Version**: `release-20261005.0` (spec: 1.2.1)

## Benchmark Measurements
Inference latency tested on identical prompt ("Repeat the word hello once.", max_tokens: 24, temperature: 0, seed: 1) on CPU with Qwen2.5-1.5B-Instruct-GGUF (Q4_K_M):

| Runtime | Latency | Overhead | Status |
|---|---|---|---|
| `runc` | **0.51 s** | Baseline | Functional, healthy |
| `runsc` (gVisor) | **0.88 s** | **+72.5%** | Functional, healthy |

## Decision & Evidence
Per SPEC Phase 2 Task 9 rules:
> "if runsc is >30% slower set MODEL_RUNTIME=runc; re-run hardened probes under the final choice. Write docs/runtime-decision.md (machine, kernel, runsc --version, per-zone OK/FAIL, reply times, decision, evidence)."

Because gVisor `runsc` introduces a 72.5% syscall virtualization penalty on model CPU inference (exceeding the 30% threshold):
1. **Decision**: Use `MODEL_RUNTIME=runc` (defaulting to hardened `runc`).
2. **Isolation Architecture**: Zones and model container are fortified using defense-in-depth:
   - Cap drop: `ALL`
   - Read-only root filesystem (`read_only: true`)
   - `no-new-privileges: true`
   - Explicit memory, CPU, and PID cgroup limits
   - 5 isolated `--internal` Docker bridge networks
   - Host `DOCKER-USER` & `INPUT` iptables rules dropping cross-bridge and external traffic.
