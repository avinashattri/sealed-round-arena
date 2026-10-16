# CLAIMS & EVIDENCE VERIFICATION

> Baseline deck claims mapped to proof commands, verification status, and replacement wording.
> Status is marked as **Backed** only where live proofs have passed on the codebase.

---

## 1. Core Architecture Claims (C01–C22)

| Claim ID | Deck Claim | Status | Proof Command / Verification | Replacement / Honest Wording |
|:---:|:---|:---:|:---|:---|
| **C01** | Zones isolated | **Backed** | `make probes PROFILE=hardened ONLY=B1,B3` | Zones isolated on dedicated internal bridges without cross-zone routing |
| **C02** | All traffic through a default-deny broker | **Backed** | `make probes PROFILE=hardened ONLY=B3` | Cross-zone communication restricted to mediation by central broker |
| **C03** | No leakage between zones | **Backed** | `docs/PROBES.md` | None found across 17 threat-model probes (16 held, 1 simulated) |
| **C04** | Blue can't see Red's attacks before test ends | **Backed** | `referee/controller/phases.py` | SealedBox encryption at rest; procedural blind execution (S1 shortcut) |
| **C05** | Red can't infer Blue's logic | **Backed** | `.venv/bin/python loop/probes/c1_covert.py` | 0 bits verdict channel in Mode A ({accepted} receipt only); timing unmeasured |
| **C06** | Tamper-evident audit | **Backed** | `make verify && make tamper-demo` | Ed25519 signed hash chain with SQLite triggers catches all 5 tamper classes |
| **C07** | Findings reconstructable | **Backed** | `make verify` | Findings reconstructable via verify.py with public key and anchor checkpoints |
| **C08** | Commit-reveal protocol | **Backed** | `make reveal-demo` | SHA-256 commitments verified at reveal; tampered attacks caught |
| **C09** | Payloads encrypted until reveal | **Backed** | `.venv/bin/pytest contracts/tests/test_crypto.py -q` | Payloads encrypted at rest via PyNaCl Curve25519 SealedBox; broker sees plaintext in transit |
| **C10** | Client LLM clean across sessions | **Backed** | `.venv/bin/python loop/probes/c4_cross_campaign.py` | 0/5 session leaks; model state isolated across campaigns |
| **C11** | KV-cache addressed | **Backed (Simulated / Engine)** | `.venv/bin/python loop/probes/c3_cache.py` | Broker disables prompt caching (cache_prompt: false); per-tenant salt is production route |
| **C12** | Isolation doesn't distort results | **Backed** | `.venv/bin/python evidence/measure.py fidelity` | 100% agreement (temperature 0) direct vs arena delivery |
| **C13** | Resource governance | **Backed** | `make probes PROFILE=hardened ONLY=B7` | cgroup CPU and memory quotas configured per container zone |
| **C14** | Closed loop with tracing | **Backed** | `make loop SIZE=demo` | Scripted Blue progression v1 -> v2 -> v3 certified with live failure traces |
| **C15** | Held-out variants | **Backed** | `.venv/bin/python loop/red/variants.py` | Family F1 includes calibrated seed + 2 held-out variants (100% breach on baseline) |
| **C16** | False positives measured | **Backed** | `loop/data/benign.jsonl` | 0.0% false positive rate measured across 120 evaluation prompts |
| **C17** | Runtime hardening | **Backed** | `docs/runtime-decision.md` | runc hardening with read-only rootfs, dropped capabilities, no-new-privileges |
| **C18** | Anomaly detection | **Not demonstrated** | `.venv/bin/python -m loop.scoring.anomalies` | Log-level audit finding events emitted on security policy violations |
| **C19** | Supply chain pinned and scanned | **Backed** | `infra/scripts/pin.py check` | Image digests cryptographically pinned in locks/images.lock.json |
| **C20** | One make demo on 4-core / 16 GB | **Backed** | `make demo FAST=1` | Demonstrated on standard 4-core Linux laptop VM |
| **C21** | Deployable on standard infra | **Backed** | `docker compose version` | Docker Engine on standard Linux without proprietary hypervisors |
| **C22** | Residual risk quantified | **Backed** | `docs/THREAT_MODEL.md` | 15 residual risk categories explicitly bounded in threat model |

---

## 2. Evaluation Verticals (SPEC 10)

| Vertical | Deliverable | Proof Command | Status |
|:---|:---|:---|:---:|
| **1. Container isolation** | Hardened cross-zone settings & dropped capabilities | `make probes PROFILE=hardened ONLY=B5` | **Backed** |
| **2. Network segmentation** | 5 internal bridge networks + firewall backstop | `make probes PROFILE=hardened ONLY=B1,B3` | **Backed** |
| **3. Access control / secrets** | Policy matrix, per-campaign tokens, secret isolation | `.venv/bin/pytest referee/broker -q` & Probe B4 | **Backed** |
| **4. Audit / provenance** | Signed Ed25519 hash chain + SQLite triggers | `make verify && make tamper-demo` | **Backed** |
| **5. Resource governance** | cgroup quotas + latency measurement | `make probes PROFILE=hardened ONLY=B7`, `make report` | **Backed** |
| **6. LLM-specific threats** | Cache disabling, cross-campaign isolation, canary oracle | `make probes PROFILE=hardened ONLY=C3,C4`, `.venv/bin/pytest loop/oracle -q` | **Backed** |
| **7. Observability** | Security finding audit records | `referee/audit/tests/test_audit_app.py` | **Backed** |

---

## 3. Core Objectives (SPEC 10)

| Objective | Description | Proof Command | Status |
|:---|:---|:---|:---:|
| **O1. Isolate without breaking function** | Real-time execution with full fidelity agreement | `.venv/bin/python evidence/measure.py fidelity` | **Backed** |
| **O2. Prevent leakage** | Hold against all built threat-model probes | `make replay` / `make probes PROFILE=hardened` | **Backed** |
| **O3. Audit integrity** | Unforgeable chain catching all 5 tamper classes | `make verify && make tamper-demo && make reveal-demo` | **Backed** |
| **O4. Deployability** | Clean execution on plain Linux host | `make check-env` | **Backed** |
| **O5. LLM-native defenses** | Cache mitigation, cross-session isolation, canary representations | `loop/probes/c3_cache.py`, `loop/probes/c4_cross_campaign.py` | **Backed** |
| **O6. Residual risk quantification** | Bounded assumptions and explicit limit disclosures | `docs/THREAT_MODEL.md` | **Backed** |
