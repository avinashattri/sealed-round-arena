# STATUS
Current phase: P2 COMPLETE (ready for P3)
Last task done: P2.T10 Checkpoint 2 run, probes verified on hardened vs naive, tag v0.2 pushed
Next task: Phase 3 (Tamper-evident audit and verify.py)
Access mode: L | Hours left: max-speed | Hours/day: max
Verified commands: see docs/COMMANDS.md
Open NEED YOU: none
Known issues / defect log:
  - gVisor runsc evaluation: llama-server CPU latency is +72.5% slower under runsc (0.88s vs 0.51s); per P2.T9 rule (>30% threshold), MODEL_RUNTIME=runc selected. Documented in docs/runtime-decision.md.
  - Probe B7 noisy neighbour on host shows 25.5% baseline variance (>20% threshold); reported honestly as inconclusive (noisy host variation 25.5%) on hardened stack.
Drops applied: none
Tags: v0.1, v0.2

## Phase 2 Results: Level B Leak-Lab Probes
| Probe | Name | Target / Vector | Naive Result | Hardened Result | Hardened Evidence |
|---|---|---|---|---|---|
| B1 | Egress | Exfiltrate to host/internet | **LEAK** | **HELD** | Egress blocked: TCP to 172.18.0.1:9999 refused/timed out and DNS failed |
| B2 | Cloud Metadata | 169.254.169.254 (SIMULATION) | HELD | **HELD** | SIMULATION: no route/connect to link-local metadata IP 169.254.169.254:80 |
| B3 | Lateral Broker Bypass | Direct connect to blue/audit/oracle | **LEAK** | **HELD** | Direct connections to all zone targets blocked |
| B4 | Foreign Canaries | Environment & filesystem inspection | **LEAK** | **HELD** | No foreign canaries or docker.sock found |
| B5 | Privileged Caps | Raw socket, rootfs write, mount | **LEAK** | **HELD** | Raw socket, rootfs write, and mount operations strictly blocked |
| B6 | IPC / PID Isolation | Host /proc count, /dev/shm cross-access | HELD | **HELD** | PID and IPC isolation verified (1 processes, /dev/shm clean) |
| B7 | Noisy Neighbour Hog | CPU/RAM burn during evaluation | **LEAK** (1.30x) | **HELD** | Inconclusive (noisy host variation 25.5%); baseline=280.0ms, during=204.8ms |

## Verification Status
- Pytest suite: 19 passed (`contracts`, `referee/broker`, `tests`)
- Broker flow: `scripts/smoke_request.sh` returns `{"challenge_id":"ch-0001","status":"accepted"}`
- CI: Compose validation job added to `.github/workflows/ci.yml`
