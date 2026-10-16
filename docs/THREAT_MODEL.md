# THREAT MODEL & SECURITY ASSURANCES

> System: Sealed-Round Arena (SRA)
> Target Architecture: 3-Zone Isolated Evaluation Framework (Red, Blue, Model) mediated by Default-Deny Broker and Cryptographic Audit Log.

---

## 1. Threat Matrix

| Threat | Status | Evidence | When it fails | Next step |
|:---|:---:|:---|:---|:---|
| **1. Cross-zone leakage** | **Demonstrated** | Probes B1, B3, B4, B5, B6; [docs/PROBES.md](file:///home/webraiders/sealed-round-arena/docs/PROBES.md); [docs/RESULTS.md](file:///home/webraiders/sealed-round-arena/docs/RESULTS.md) | Docker daemon bridge misconfiguration or IP forwarding enabled across bridges | Enforce host firewall rules (`infra/firewall/apply.sh`) and eBPF egress filtering |
| **2. Container / kernel escape** | **Reduced (not tested)** | [docs/runtime-decision.md](file:///home/webraiders/sealed-round-arena/docs/runtime-decision.md); `runc` with dropped capabilities (`CAP_NET_RAW`), read-only root filesystem, `no-new-privileges` | Zero-day kernel vulnerability or privileged container breakout | Deploy on hardware-isolated microVMs (Firecracker / Kata Containers) |
| **3. CPU side channels** | **Not demonstrated** | Host baseline variance caveat documented; cgroup CPU limits enforced | Spectre/Meltdown or L1/L2 cache contention across sibling hyperthreads | Hardware core pinning (`taskset`), hyperthreading disabled, `isolcpus` |
| **4. Shared GPU memory** | **Not applicable** | Model runs purely on CPU via `llama-server`; no GPU device nodes shared or mapped | GPU driver memory leaks or tensor core context leakage | Multi-Instance GPU (MIG) with hardware-enforced memory isolation |
| **5. Prefix-cache timing** | **Demonstrated (engine level)** | `loop/probes/c3_cache.py`: 51.9x ratio measured on raw engine; broker strictly forces `cache_prompt: false` | Inference server re-enables global prompt caching | Cryptographic tenant-keyed prompt cache salting (`vLLM cache_salt`) |
| **6. Verdict / response channel** | **Demonstrated (0 bits)** | `loop/probes/c1_covert.py`: 200 responses return constant `{"challenge_id":..., "status":"accepted"}`; 422 errors return fixed `{"error":"bad request"}` | Gateway echoes user input or returns informative error stack traces | Automated response fuzzing and differential verification |
| **7. Timing channel** | **Not measured** | Probe C2 dropped per planned fallback E7; response timing unpadded | Attacker measures sub-millisecond network roundtrips on low-jitter local network | Jittered response delay bucketing (constant-time response padding) |
| **8. Audit tampering** | **Demonstrated** | `referee/verify/verify.py` and `scripts/tamper_demo.py` catching 5/5 synthetic tamper vectors | Audit signing key seed compromised on host | Hardware Security Module (HSM) or cloud KMS signing |
| **9. Broker / Audit / Controller compromise** | **Out of scope** | Central referee components assumed trusted; all policy enforced at broker boundaries | Host root compromise or arbitrary code execution in broker | Confidential Computing (AMD SEV-SNP / Intel SGX) for referee zone |
| **10. Malicious operator / Cloud provider** | **Out of scope** | Standard single-tenant evaluation model | Host administrator reads physical memory or container storage | Remote attestation and verifiable confidential virtual machines |
| **11. Canary Oracle misdetection** | **Demonstrated (Canary-only)** | `loop/oracle/matcher.py`: regex pattern matching across plain, spaced, reversed, base64, hex, and rot13 | Model outputs paraphrased semantic leak without verbatim canary token | Ensemble harm classifier (HarmBench / Llama-Guard) alongside canaries |
| **12. Blue defense overfitting** | **Demonstrated** | `loop/red/variants.py`: calibrated seed + 2 held-out variants; 120-item benign prompt validation (0.0% FPR) | Attackers employ completely novel jailbreak taxonomies | Continuous automated red-teaming (AutoDAN / PAIR) in loop progression |
| **13. Software supply chain** | **Demonstrated** | `infra/scripts/pin.py`, `locks/images.lock.json`, image digest verification at launch | Upstream maintainer compromise or unpinned pip dependencies | Cosign cryptographic signatures + SLSA Level 3 build provenance |
| **14. Resource exhaustion / DoS** | **Demonstrated** | cgroup resource limits in `infra/compose/hardened.yml` (CPU shares, memory caps) | Memory exhaustion triggering host kernel OOM killer | Hard memory reservations with systemd slice isolation |
| **15. Human operator visibility (S1)** | **Procedural** | Cryptographic commit-reveal (`contracts/crypto/commit.py`) and SealedBox payload encryption | Operator inspects raw traffic or payload archives during execution | Multi-party cryptographic threshold decryption (m-of-n escrow) |

---

## 2. Verdict-Channel Information Bound

In Mode A (blind evaluation):
- **Response Alphabet:** Red receives exclusively `{"challenge_id": "<id>", "status": "accepted"}` for accepted submissions.
- **Error Responses:** Schema or size violations return a fixed, static payload `{"error": "bad request"}` without echoing any input fields or detailing validation failure paths.
- **Information Leakage:**
  $$\text{Leakage} = \log_2(1) = 0 \text{ bits per query}$$
- **Mode B (Adaptive Evaluation Bound):**
  If Red is provided with pass/fail evaluation outcomes in real-time, leakage is bounded by:
  $$\text{Leakage} \le Q \times \log_2(|\Sigma|)$$
  where $Q$ is the number of queries and $|\Sigma| = 2$ ({pass, fail}), giving at most $Q$ bits of feedback. In Sealed-Round Arena Mode A, all verdicts are withheld until round reveal, strictly preserving $0$ bits of feedback during execution.

---

## 3. Solo Shortcuts & Disclosures (S1–S7)

Per project design specifications, the following solo development shortcuts are explicitly cataloged:

- **S1 (Single Operator):** A single developer operates Red, Blue, and Referee roles. Blindness is maintained procedurally and enforced via Curve25519 SealedBox cryptography.
- **S2 (Scripted Defenses):** Blue defense layers (v1, v2, v3) are packaged as immutable Docker images rather than an interactive live defense submission API.
- **S3 (Token Authentication):** Per-campaign and per-service bearer tokens are used instead of a full mutual TLS (mTLS) public key infrastructure.
- **S4 (Local Checkpoint Anchors):** Audit checkpoints are signed and anchored to local filesystem artifacts (`evidence/anchors/*.json`) rather than an external public ledger (e.g. RFC 3161 TSA or Rekor).
- **S5 (Canary-Only Oracle):** Evaluation is strictly canary-token leak detection across 6 encoding representations, without a full semantic harm judge.
- **S6 (Simulated Probes):** Probe B2 (cloud metadata) and C3 (prefix cache cross-campaign broker integration) are executed as simulations or engine-level tests.
- **S7 (Single-Host Deployment):** All zones execute on a single Linux host via Docker Engine internal bridge networks rather than a distributed Kubernetes cluster.
