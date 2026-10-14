# Hardening Specification

This document details the container and network micro-segmentation controls implemented in `infra/compose/hardened.yml` for Sealed Round Arena.

## 1. Container Defense-in-Depth (`x-zone` Anchor)

Every container zone (broker, audit, oracle, blue, red) implements strict least-privilege constraints:

| Control | Value | Rationale |
|---|---|---|
| User | `10001:10001` (`appuser`) | Eliminates root privileges within the container; prevents root filesystem changes. |
| Read-only Root FS | `read_only: true` | Protects binaries, configurations, and system directories from in-flight tampering or persistence. |
| Memory-backed `/tmp` | `tmpfs: ["/tmp:size=64M,noexec,nosuid,nodev"]` | Constrains temporary scratchpad to 64MB; disallows execution of payloads written to `/tmp`. |
| Linux Capabilities | `cap_drop: [ALL]` | Removes all kernel capabilities (e.g. `CAP_NET_RAW`, `CAP_SYS_ADMIN`, `CAP_CHOWN`, `CAP_DAC_OVERRIDE`). |
| No New Privileges | `security_opt: ["no-new-privileges:true"]` | Prevents privilege escalation through `setuid`/`setgid` binaries. |
| CPU Limit | `cpus: 1.0` (model: `3.0`) | Mitigates CPU exhaustion and denial-of-service across tenants. |
| Memory Limit | `mem_limit: 512m` (model: `3g`) | Hard cgroup memory threshold to prevent OOM attacks. |
| PIDs Limit | `pids_limit: 64` | Restricts fork-bombing or unbounded thread creation. |
| DNS Override | `dns: ["192.0.2.1"]` | Uses TEST-NET-1 unroutable blackhole IP to disable external recursive DNS resolution. |
| Log Rotation | `max-size: 10m, max-file: 3` | Protects host disk space from log flooding. |
| Exposed Ports | None | No host port publishing in hardened configuration. All communications are in-cluster. |

## 2. Probe Twins (`x-probe` Anchor)

Probe twins (`red_probe`, `blue_probe`, `model_probe`) evaluate isolation from the perspective of an attacker who has achieved container execution.
- They inherit all resource limits, DNS, and network settings from `x-zone`.
- They override `user: "0:0"` solely to test whether kernel capability dropping and root-filesystem locks prevent privileged actions (e.g., raw sockets, mounts) even when running as UID 0 inside the user namespace.

## 3. Network Micro-Segmentation

Five isolated Docker bridge networks configured with `--internal`:
1. `red_net` (`br-sra-red`): Broker <-> Red zone
2. `blue_net` (`br-sra-blue`): Broker <-> Blue filter zone
3. `model_net` (`br-sra-model`): Broker <-> Model inference engine
4. `audit_net` (`br-sra-audit`): Broker <-> Append-only Audit logger
5. `referee_net` (`br-sra-referee`): Broker <-> Oracle scoring judge

Cross-zone traffic is structurally impossible at Layer 2 and Layer 3: only the Broker container is multi-homed across all five networks.
