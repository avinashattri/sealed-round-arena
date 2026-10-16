# Probes Status & Evidence

All 18 threat-model probes ranked by convincing-per-hour per `docs/SPEC.md` Section 2.

## Summary: 17/18 BUILT (16 HELD, 1 SIMULATION, 1 NOT BUILT)

| Rank | ID | Category / Name | Status | Level | Zone | Verdict (Hardened) | Evidence / Implementation Notes |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---|
| 1 | **B1** | Egress TCP/DNS + host reach | **BUILT** | L1 | red | **HELD** | `infra/probes/b1_egress.py`: TCP connection to host/egress refused/timed out; DNS resolution failed |
| 2 | **B3** | Zone-to-zone direct bypass | **BUILT** | L1 | red | **HELD** | `infra/probes/b3_bypass.py`: Direct connection to Blue, Model, Audit, Oracle blocked by internal bridge isolation; positive control (Broker) succeeded |
| 3 | **A1** | Red calls Blue/Model directly | **BUILT** | L1 | red | **HELD** | Covered by B3 network segmentation & broker access policy |
| 4 | **B4** | Foreign files, env & docker.sock | **BUILT** | L1 | red | **HELD** | `infra/probes/b4_files.py`: No access to /var/run/docker.sock, foreign secrets (`token_svc_blue`, `token_svc_audit`, `blue_canary`), or root-owned files |
| 5 | **C6** | Audit tamper resistance | **BUILT** | L3 | audit | **HELD** | `scripts/tamper_demo.py` & `make tamper-demo`: 5/5 tamper classes caught (`content changed`, `missing seq`, `out of order`, `truncated`, `duplicate seq`) |
| 6 | **B5** | Raw socket, rootfs write, mount | **BUILT** | L1 | blue | **HELD** | `infra/probes/b5_privileged.py`: `CAP_NET_RAW` denied (cannot open raw socket), root filesystem is read-only, mount blocked |
| 7 | **A2** | Campaign token boundary (c-001 vs c-002) | **BUILT** | L2 | broker | **HELD** | `referee/broker/tests/test_broker_app.py`: Token for c-001 used on c-002 yields `403 Forbidden` |
| 8 | **A5** | Zone tokens on audit service | **BUILT** | L2 | audit | **HELD** | `referee/audit/tests/test_audit_app.py`: Only `svc_audit` token accepted; Red/Blue tokens yield `403 Forbidden` |
| 9 | **A3** | Schema strictness & size limit | **BUILT** | L2 | broker | **HELD** | Unknown field yields `422` with fixed error string; 17 KB payload yields `413 Payload Too Large` |
| 10 | **B2** | Cloud metadata (169.254.169.254) | **SIMULATION** | L1 | red | **HELD** | `infra/probes/b2_metadata.py`: No route to link-local metadata address (simulated on local Linux host) |
| 11 | **B6** | IPC/PID namespace visibility | **BUILT** | L1 | red | **HELD** | `infra/probes/b6_ipc.py`: Container sees only own PID 1 (sleep) and probe PID; zero host or foreign zone processes visible |
| 12 | **C5** | Residue after reset/clean | **BUILT** | L1 | host | **HELD** | `infra/probes/c5_residue.sh` & `loop/probes/c5_residue.py`: `make clean` asserts 0 containers, 0 volumes, 0 networks, empty secrets/shared dirs, 0 canary residue in /tmp or ~/.cache |
| 13 | **C1** | Covert fields & constant receipt | **BUILT** | L2 | broker | **HELD** | `loop/probes/c1_covert.py`: 200 response body strictly `{"challenge_id":..., "status":"accepted"}`; 422 errors never echo input; 0 bits channel leakage across 3 rounds |
| 14 | **A4** | Tool-call policy allowlist | **BUILT** | L2 | broker | **HELD** | `referee/broker/tests/test_broker_app.py`: Disallowed tool call emits `FINDING` audit event and blocks unauthorized model output |
| 15 | **C4** | Cross-campaign canary isolation | **BUILT** | L2 | model | **HELD** | `loop/probes/c4_cross_campaign.py`: Naive deployment leaked previous session canary from history; hardened arena isolates model state (0/5 leaks across campaigns) |
| 16 | **B7** | Noisy neighbour resource containment | **BUILT** | L1 | red | **HELD** | `run_probes.py`: Baseline vs CPU/memory hog measured; cgroup limits enforce CPU quotas; host baseline noise reported honestly |
| 17 | **C3** | Prefix-cache timing channel | **BUILT** | L2 | model | **HELD** | `loop/probes/c3_cache.py`: Demonstrated at engine level (twin -> llama-server, cache on vs off: 51.9x ratio, p=0.00397). The broker forces cache_prompt:false (unit test). The full cross-campaign path through the broker is a design claim. Production route: per-tenant cache salt (vLLM cache_salt). |
| 18 | **C2** | Sub-millisecond timing channel (KS) | **NOT BUILT** | L2 | red | **NOT BUILT** | Dropped per planned fallback E7; 0 bits of verdict in Mode A; timing channel not measured |
