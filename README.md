# Sealed-Round Arena (SRA)

An isolated, tamper-evident evaluation platform that benchmarks LLM red-teaming defenses across sealed rounds without covert channels or leakage.

<!-- GIF: record in P7 -->
> *[Demonstration Recording: replay mode execution and audit verification]*

---

## Key Highlights

- **16/18 Threat-Model Probes Held:** Validated against 18 ranked attack vectors spanning egress, inter-zone bypass, filesystem leakage, IPC visibility, covert response fields, and cache timing (16 held, 1 simulated, 1 unmeasured).
- **Certified Defense Progression ($n=36$):** Evaluated on attack family F1; transitions from 100% breach baseline (Round 1) to partially fixed (Round 2, 66.7%) to certified **`FIXED`** (Round 3, 0.0% breach, Wilson 95% CI $[0.00, 0.0964] \le 0.10$, 0.0% FPR).
- **Cryptographic Audit Trail (5,218+ entries verified):** Ed25519-signed SHA-256 hash chain with SQLite triggers, catching 5/5 synthetic tamper classes and catching altered payloads at reveal.

---

## Quickstart

### Prerequisites & Host Machine
- **Tested Environment:** Linux VM (Ubuntu 24.04 LTS, 4 CPU cores, 16 GB RAM).
- **Dependencies:** Docker Engine 24+, Python 3.10+, `git`, `curl`, `make`.

```bash
# 1. Clone repository
git clone https://github.com/webraiders/sealed-round-arena.git
cd sealed-round-arena

# 2. Setup virtual environment, download model weights and assets
make setup

# 3. Run automated demo (<4 min on 4 cores)
make demo FAST=1

# 4. Instant offline replay and audit verification (<2s)
make replay
```

---

## Results at a Glance

### 1. Threat-Model Probes (Leak Lab)

| Rank | ID | Probe Vector | Level | Zone | Naive | Hardened | Status |
|:---:|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | **B1** | Egress TCP/DNS + host reach | L1 | red | **LEAK** | **HELD** | Demonstrated |
| 2 | **B3** | Zone-to-zone direct bypass | L1 | red | **LEAK** | **HELD** | Demonstrated |
| 3 | **A1** | Direct Red-to-Blue/Model call | L1 | red | **LEAK** | **HELD** | Demonstrated |
| 4 | **B4** | Foreign files, env & docker.sock | L1 | red | **LEAK** | **HELD** | Demonstrated |
| 5 | **C6** | Audit tamper resistance (5 classes) | L3 | audit | **LEAK** | **HELD** | Demonstrated |
| 6 | **B5** | Raw socket, rootfs write, mount | L1 | blue | **LEAK** | **HELD** | Demonstrated |
| 7 | **A2** | Campaign token boundary (c-001 vs c-002) | L2 | broker | **LEAK** | **HELD** | Demonstrated |
| 8 | **A5** | Zone tokens on audit service | L2 | audit | **LEAK** | **HELD** | Demonstrated |
| 9 | **A3** | Schema strictness & size limit | L2 | broker | **LEAK** | **HELD** | Demonstrated |
| 10 | **B2** | Cloud metadata (169.254.169.254) | L1 | red | HELD | **HELD** | Simulated |
| 11 | **B6** | IPC/PID namespace visibility | L1 | red | HELD | **HELD** | Demonstrated |
| 12 | **C5** | Residue after reset/clean | L1 | host | **LEAK** | **HELD** | Demonstrated |
| 13 | **C1** | Covert fields & constant receipt | L2 | broker | **LEAK** | **HELD** | Demonstrated |
| 14 | **A4** | Tool-call policy allowlist | L2 | broker | **LEAK** | **HELD** | Demonstrated |
| 15 | **C4** | Cross-campaign canary isolation | L2 | model | **LEAK** | **HELD** | Demonstrated |
| 16 | **B7** | Noisy neighbour resource containment | L1 | red | **LEAK** | **HELD** | Demonstrated |
| 17 | **C3** | Prefix-cache timing channel | L2 | model | **LEAK** | **HELD** | Demonstrated |
| 18 | **C2** | Sub-millisecond timing channel (KS) | L2 | red | NOT BUILT | NOT BUILT | NOT BUILT |

*Full evidence details and probe descriptions are documented in [docs/PROBES.md](docs/PROBES.md).*

### 2. Multi-Round Defense Progression (Family F1, $n=36$)

| Round | Defense Layer | Seed ASR | Variants ASR | Pooled ASR | 95% Wilson CI | False Positive Rate | Certified State |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **1** | v1 (Input override) | 12/12 | 24/24 | **36/36** | $[0.9036, 1.0000]$ | 0.0% | **`(baseline)`** |
| **2** | v2 (Paraphrase filter) | 0/12 | 24/24 | **24/36** | $[0.5033, 0.7979]$ | 0.0% | **`PARTIALLY FIXED`** |
| **3** | v3 (Normalized scanner + redaction) | 0/12 | 0/24 | **0/36** | $[0.0000, 0.0964]$ | 0.0% | **`FIXED`** |

### 3. Performance & Fidelity Overhead

| Metric | Direct Model | Arena Mediated Broker | Overhead Delta | Overhead Ratio |
|:---|:---:|:---:|:---:|:---:|
| **p50 Latency** | `615.77 ms` | `1455.00 ms` | `+839.23 ms` | `136.3%` |
| **p95 Latency** | `812.52 ms` | `1780.33 ms` | `+967.81 ms` | `119.1%` |
| **Generation Fidelity** | `100.0% agreement` | `100.0% agreement` | `0 token mismatch` | Wilson CI $[0.7225, 1.0000]$ |

---

## How It Works

1. **Strict 3-Zone Segmentation:** Red, Blue, and Model execute on non-routed internal Docker bridge networks (`red_net`, `blue_net`, `model_net`).
2. **Default-Deny Broker:** The broker is the single multi-homed gateway validating schemas, dropping unauthorized tool calls, and mediating all traffic.
3. **Commit-Reveal Sealing:** Attack payloads are sealed to disk using Curve25519 SealedBox; SHA-256 commitments are validated at round reveal to prevent retrofitted attacks.
4. **0-Bits Verdict Channel (Mode A):** Red receives exclusively constant receipts `{"status": "accepted"}` during execution; Blue defense decisions and Canary Oracle scores are withheld until reveal.
5. **Tamper-Evident Provenance:** All operations are recorded into an append-only Ed25519 hash chain, signed at round close, and verifiable offline.

*Read the comprehensive design in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).*

---

## Threat Model Summary

- **Protected:** Network egress bypass, cross-zone direct calls, unauthorized tool execution, foreign secret extraction, audit log modification, response covert channels (0 bits), and cross-campaign model state leakage.
- **Reduced:** Container/kernel escape (hardened with non-root user, dropped `CAP_NET_RAW`, read-only rootfs), prefix-cache timing (broker disables prompt caching), and CPU starvation (cgroup quotas).
- **Out of Scope / Unmeasured:** Malicious host hypervisor / cloud operator, hardware GPU memory leakage (system is CPU-only), and sub-millisecond network jitter timing channels (C2 dropped per fallback E7).

*Full threat matrix and bounded assumptions are detailed in [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).*

---

## Limits & Honesty Disclosures

> [!NOTE]
> - **No Hype:** We never claim this system is "secure", "unhackable", or guarantees "zero leakage". The system is evaluated and held strictly against the 18 cataloged threat probes.
> - **Simulated Probes:** Probe B2 (cloud metadata) and C3 (prefix cache timing gap) are evaluated at the engine / simulation level.
> - **Scripted Progression:** Blue defenses v1, v2, and v3 are deterministic, scripted rule layers evaluated against pre-calibrated F1 seed prompts and held-out variants.
> - **Solo Shortcut (S1):** A single developer operates Red, Blue, and Referee roles; blindness is enforced procedurally and through SealedBox cryptography.
> - **Container Runtime:** Hardened configurations run on standard Docker Engine `runc` with dropped capabilities; gVisor `runsc` was evaluated and deferred due to a +72.5% CPU latency degradation on llama-server (documented in [docs/runtime-decision.md](docs/runtime-decision.md)).

---

## Repository Map

```
sealed-round-arena/
├── contracts/             # Canonical serialization, message schemas, crypto (commit, seal)
├── dashboard/             # Interactive Streamlit dashboard (app.py)
├── docs/                  # Architecture, Results, Probes, Threat Model, Claims
├── evidence/              # Live execution evidence, results JSONs, audit log export, anchors
├── infra/
│   ├── compose/           # Naive and hardened Docker Compose environments
│   ├── docker/            # Dockerfiles for zone stubs, broker, audit, oracle, probe
│   ├── firewall/          # Host firewall backstop iptables rules
│   └── probes/            # Threat-model probe scripts (B1, B3, B4, B5, B6, C5)
├── loop/
│   ├── blue/              # Defenses v1, v2, v3
│   ├── data/              # Attack family F1, benign evaluation set (120 prompts)
│   ├── oracle/            # Canary leak matcher across 6 encodings
│   ├── probes/            # Model covert channel probes (C1, C3, C4)
│   └── scoring/           # Statistical analysis, Wilson CIs, loop runner
├── referee/
│   ├── audit/             # SQLite trigger-hardened audit store and service
│   ├── broker/            # Default-deny mediation gateway
│   ├── controller/        # 7-phase round lifecycle coordinator
│   └── verify/            # Offline cryptographic verifier and tamper tests
├── replay/                # Validated offline demonstration bundle and meta.json
├── scripts/               # Automation, demo.py, audit_checks.py, record.py, check_env.py
└── Makefile               # make check-env, naive, hardened, loop, verify, demo, replay, dashboard
```

---

## Credits & Licenses

- **Target Model:** [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) (Apache-2.0 License).
- **Inference Engine:** [llama.cpp](https://github.com/ggerganov/llama.cpp) (MIT License).
- **Evaluation Dataset:** Prompts adapted from [Gandalf](https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions) (MIT License).
- *Models and datasets are downloaded via scripts on setup and are not redistributed with this repository.*
- **Sealed-Round Arena:** Licensed under the [MIT License](LICENSE).
