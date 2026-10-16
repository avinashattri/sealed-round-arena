# Sealed-Round Arena v1.0 Release Notes

> **Version:** `v1.0`  
> **Release Target:** Hackathon Submission & Demonstration Release  
> **License:** MIT License  
> **Repository:** https://github.com/webraiders/sealed-round-arena

---

## 1. Executive Summary

**Sealed-Round Arena (SRA)** is an isolated, tamper-evident evaluation framework for benchmarking LLM defenses against adversarial red-teaming. It guarantees that untrusted attack payloads cannot leak across execution zones, that defenses cannot overfit to live submissions, and that round findings cannot be altered post-hoc.

---

## 2. Key Capabilities & Empirical Results

- **16/18 Threat-Model Probes Held:**
  - Validated against 18 ranked attack vectors across network egress, inter-zone bypass, foreign filesystem/secrets access, IPC namespace visibility, response covert channels, and KV-cache timing.
  - 16 held on hardened configuration, 1 simulated (B2 metadata), 1 unmeasured (C2 timing channel).
- **Certified Defense Progression ($n=36$):**
  - Evaluated on attack family F1 across 3 rounds against a live Qwen2.5-1.5B instruction model.
  - Round 1 (v1 baseline): 36/36 breaches (100.0% breach rate).
  - Round 2 (v2 paraphrase filter): 24/36 breaches (66.7% breach rate, PARTIALLY FIXED).
  - Round 3 (v3 normalization + output redaction): 0/36 breaches (0.0% breach rate, Wilson 95% CI $[0.0000, 0.0964] \le 0.10$, 0.0% false positive rate across 120 benign prompts, certified **FIXED**).
- **Tamper-Evident Provenance (5,218+ entries verified):**
  - Canonical RFC 8785 JSON events bound in an Ed25519-signed SHA-256 hash chain with SQLite triggers blocking SQL `UPDATE` and `DELETE`.
  - Offline verification via `referee.verify.verify` with published public keys and round anchor checkpoints.
  - Tamper tests catch 5/5 synthetic corruption classes (`content changed`, `missing seq`, `out of order`, `truncated`, `duplicate seq`).
  - Commit-reveal protocol catches retroactively altered payloads at reveal (`ch-0003` caught with `COMMITMENT MISMATCH`).
- **Performance & Zero Distortion:**
  - Direct model inference median latency: 615.8 ms.
  - Arena-mediated broker median latency: 1,455.0 ms (+839.2 ms overhead for dual-pass filtering, audit logging, and canary scanning).
  - Generation fidelity: **100.0% agreement** direct vs arena at temperature 0 (Wilson 95% CI $[0.7225, 1.0000]$).

---

## 3. Limits & Honesty Disclosures

- **Bounded Security Claims:** We never claim this system is "secure", "unhackable", or guarantees "zero leakage". Defenses are verified and held against the 18 cataloged threat probes.
- **Simulations:** Probe B2 (cloud metadata) and C3 (prefix-cache timing gap) are evaluated at the engine / simulation level.
- **Scripted Defenses:** Blue defenses v1, v2, and v3 are deterministic, scripted rule layers evaluated against pre-calibrated F1 seed prompts and held-out variants.
- **Solo Developer Shortcuts (S1–S7):** A single developer operates all roles; blindness is enforced procedurally and through SealedBox cryptography; token authentication is used instead of mTLS; local filesystem anchors are used instead of external public timestamp ledgers.
- **Container Runtime:** Hardened configurations run on standard Docker Engine `runc` with dropped Linux capabilities (`CAP_NET_RAW`) and read-only root filesystems; gVisor `runsc` was evaluated and deferred due to a +72.5% CPU latency degradation on llama-server.

---

## 4. Quickstart

```bash
# Clone and setup
git clone https://github.com/webraiders/sealed-round-arena.git
cd sealed-round-arena
make setup

# Run automated live demo (<4 min on 4 cores)
make demo FAST=1

# Instant offline replay and audit verification (<2s)
make replay

# Launch interactive dashboard
make dashboard
```
