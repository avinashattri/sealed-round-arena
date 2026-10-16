# SOLO LIVE DEMO SCRIPT & JUDGE Q&A GUIDE

> **Target Duration:** 7–8 minutes  
> **Format:** Live terminal walkthrough + dashboard presentation + offline fallback ladder  
> **Target Audience:** Hackathon judges, security researchers, ML platform engineers

---

## 1. Five-Minute Pre-Flight Checklist

Before presenting or recording:
- [ ] Docker Engine running (`docker info >/dev/null`)
- [ ] Virtual environment active (`source .venv/bin/activate`)
- [ ] Sudo credentials cached (`sudo -v`)
- [ ] Firewall backstop rules active (`make fw-on`)
- [ ] Wi-Fi turned OFF (all demo and replay commands run 100% locally/offline)
- [ ] Charger plugged in; laptop on maximum performance profile
- [ ] Notifications and popups disabled (Do Not Disturb enabled)
- [ ] Terminal font size set to **18–20 pt** with high-contrast color scheme
- [ ] Streamlit dashboard pre-launched in browser: `http://localhost:8501`
- [ ] Verified git commit is tagged: `git rev-parse --short HEAD` matches `v1.0` or `v1.0-rc1`
- [ ] Backup MP4 video clips ready in quick-access folder
- [ ] Printed failure ladder card placed next to keyboard

---

## 2. Failure Ladder & Switch Rule

> **Golden Switch Rule:** If any live command freezes or yields no output for **20 seconds**, or returns an unexpected error, **immediately** switch to the replay fallback command. Never debug live during the presentation.

| Moment | Primary Live Command | Fallback Command (Offline Replay) | Last Resort |
|---|---|---|---|
| **STAR-1: Leak Lab** | `make probes PROFILE=naive ONLY=B1,B3,B4` | `make replay SECTION=probes` | Play `clip_01_probes.mp4` |
| **Defense Loop** | `make replay SECTION=loop` | `cat docs/RESULTS.md` | Play `clip_02_loop.mp4` |
| **STAR-2: Tamper Demo** | `make verify && make tamper-demo` | `make replay SECTION=audit` | Play `clip_03_tamper.mp4` |
| **STAR-3: Reveal Demo** | `make reveal-demo` | `cat /tmp/reveal_demo.log` | Play `clip_04_reveal.mp4` |
| **Metrics & Dashboard** | Browser `http://localhost:8501` | `make replay SECTION=metrics` | Play `clip_05_dashboard.mp4` |

---

## 3. Minute-by-Minute Live Demo Script (7–8 Minutes)

### [0:00 – 0:40] The Problem & System Overview
- **Action:** Open terminal at repo root. Run `make help`.
- **Narration:**
  > "Evaluating LLMs and defenses during adversarial red-teaming faces a fundamental paradox: you cannot trust adversarial inputs, yet traditional evaluation setups run everything on shared bridges, leaking secrets across zones, distorting responses, and allowing retroactive tampering of attack submissions.
  > 
  > This is **Sealed-Round Arena (SRA)**: an isolated, tamper-evident evaluation platform that benchmarks LLM defenses across sealed rounds without covert channels, inter-zone bypass, or submission forgery."

---

### [0:40 – 2:10] STAR-1: The Leak Lab (Naive vs Hardened)
- **Action:** Run:
  ```bash
  make probes PROFILE=naive ONLY=B1,B3,B4
  ```
- **Observed:** Three bright red `LEAK` lines appear on screen.
  - `B1 LEAK`: Egress TCP connected directly to gateway
  - `B3 LEAK`: Bypassed broker; reached Blue service directly
  - `B4 LEAK`: Foreign zone canary found in environment variables
- **Narration:**
  > "Here is the baseline setup used in standard Docker benchmarks. Red can bypass the referee, talk directly to Blue and Model, exfiltrate data to the host, and read foreign zone canary tokens directly from shared environments."
- **Action:** Run:
  ```bash
  make probes PROFILE=hardened ONLY=B1,B3,B4
  ```
- **Observed:** Three bright green `HELD` lines appear.
- **Action:** Transition to full probe table:
  ```bash
  make replay SECTION=probes
  ```
- **Narration:**
  > "Under our hardened architecture with non-routed internal bridges and a default-deny broker, those same vectors are blocked. Across 18 ranked threat probes—covering network bypass, filesystem isolation, IPC namespace visibility, response covert channels, and prefix cache timing—16 are HELD, 1 is simulated, and 1 timing probe was dropped per our honest fallback specification."

---

### [2:10 – 3:30] The Closed-Loop Defense Progression (n=36)
- **Action:** Run:
  ```bash
  make replay SECTION=loop
  ```
- **Observed:** Clean rich table displaying Rounds 1, 2, and 3.
- **Narration:**
  > "Next, the evaluation loop. We evaluate attack family F1 using pre-calibrated seeds and held-out variants across 36 trials per round against a live 1.5-billion-parameter instruction model.
  > 
  > In Round 1 with basic defense v1, attackers achieved a 100% breach rate—establishing our empirical baseline.
  > In Round 2 with paraphrase filtering, breach rate dropped to 66.7%, reaching a PARTIALLY FIXED state.
  > In Round 3 with normalized token decoding and output redaction, breaches dropped to 0%, certified at FIXED with a Wilson 95% confidence interval upper bound under 0.10, and a 0.0% false positive rate on 120 benign prompts."

---

### [3:30 – 4:40] STAR-2: Cryptographic Audit & Tamper Resistance
- **Action:** Run:
  ```bash
  make verify
  ```
- **Observed:** `PASS: 5218 entries, chain, signatures and checkpoint verified`
- **Narration:**
  > "Every interaction in the arena is hashed canonically and signed with an Ed25519 hash chain backed by SQLite update-and-delete triggers. Here, verify.py validates 5,218 live entries against our signed round anchor checkpoint."
- **Action:** Run:
  ```bash
  make tamper-demo
  ```
- **Observed:** Five distinct failures caught on in-memory copies:
  - `flip -> FAIL (content changed)`
  - `delete -> FAIL (missing seq)`
  - `reorder -> FAIL (missing seq)`
  - `truncate -> FAIL (truncated: expected 5218)`
  - `replay -> FAIL (duplicate seq)`
- **Narration:**
  > "To prove tamper resistance, tamper-demo applies 5 distinct classes of corruption to in-memory copies of the log. As you can see, every single manipulation is caught with an exact failure reason."

---

### [4:40 – 5:40] STAR-3: Commit-Reveal Protocol
- **Action:** Run:
  ```bash
  make reveal-demo
  ```
- **Observed:** `COMMITMENT MISMATCH: ['ch-0003']` $\to$ `OK: the altered attack was caught`
- **Narration:**
  > "What stops a Red team from changing their prompt after seeing the results? Our commit-reveal protocol. Attacks are committed in Phase 1 via SHA-256 hashes and sealed with Curve25519 SealedBoxes. In this test, an attacker subtly altered attack challenge ch-0003 at reveal. The referee caught the commitment mismatch instantly and rejected the round."

---

### [5:40 – 6:50] Benchmarks, Overhead & Dashboard Tour
- **Action:** Switch to browser at `http://localhost:8501`.
- **Narration:**
  > "Let's inspect our Streamlit dashboard, which runs entirely from recorded or live evidence without ever calling Docker or modifying the audit log.
  > 
  > Under Benchmarks: Direct model inference median latency is 616 ms. Through the arena broker, latency is 1,455 ms—an overhead of 839 ms for full cryptographic sealing, audit logging, dual-pass Blue filtering, and canary scanning. Crucially, generation fidelity is 100.0%: zero token perturbation.
  > 
  > Under the Trace Explorer: Judges can inspect any challenge across rounds, examining the raw input, gateway decision, model output, and oracle verdict."

---

### [6:50 – 7:30] Conclusion & Honest Boundary
- **Narration:**
  > "To conclude: Sealed-Round Arena provides empirical isolation, closed-loop defense verification, and cryptographic auditability on standard developer hardware.
  > 
  > We make no hype claims: we do not claim the system is 'unhackable' or eliminates all side channels. We state clearly that the defense held against these 16 cataloged probes. Thank you, and I welcome your questions."

---

## 4. The 20 Likely Judge Questions & Concrete Honest Answers

### 1. Is this system completely secure?
> **Answer:** "No system is completely secure, and we explicitly avoid hype words like 'unhackable' or 'zero leak'. Our security claims are bounded strictly to the 18 threat-model probes we cataloged: we demonstrated that the hardened configuration held against all 16 built probes, labeled 1 as simulation, and disclosed 1 dropped probe."

### 2. Why is default Docker insufficient for competitive evaluation?
> **Answer:** "Default Docker bridges allow inter-container IP routing, container-to-host connectivity, and environment variable inspection. In our naive probe demonstration, an untrusted Red container directly reached Blue's internal port, exfiltrated data through the host bridge, and read foreign zone canary secrets."

### 3. Did you use gVisor (runsc)? Why or why not?
> **Answer:** "We evaluated gVisor `runsc` during Phase 2. While network and IPC isolation held, CPU inference latency for `llama-server` increased by +72.5% (from 0.51s to 0.88s), exceeding our pre-registered 30% performance threshold. Per our decision rule in `docs/runtime-decision.md`, we deployed standard `runc` hardened with read-only root filesystems, dropped capabilities (`CAP_NET_RAW`), and `no-new-privileges`."

### 4. What prevents an attacker from breaking out of the container (kernel escape)?
> **Answer:** "Container escape is categorized in our Threat Model under 'Reduced, not tested'. We reduce escape surface by running all services as non-root users (`uid 1000`), enforcing `read_only: true` on root filesystems, dropping all unnecessary capabilities, and forbidding privilege escalation. Complete kernel breakout prevention requires microVMs like Firecracker or Kata Containers, which we document as our next architectural evolution."

### 5. Does the mediation layer distort model output fidelity?
> **Answer:** "No. We tested 10 evaluation prompts direct vs through the arena at temperature 0. Agreement was 100.0% (Wilson 95% CI [0.7225, 1.0000]). The broker acts as an HTTP proxy without modifying prompt tokens or generation parameters."

### 6. How do you address CPU cache side channels (Spectre/Meltdown)?
> **Answer:** "On a shared multi-core host, microarchitectural cache timing channels exist across hyperthreads. We enforce cgroup CPU quotas (2.0 cores per zone), but we honestly disclose in `docs/THREAT_MODEL.md` that CPU side channels are not demonstrated or prevented without dedicated core pinning (`taskset`) and disabled simultaneous multithreading."

### 7. How does the arena handle KV-cache timing channels?
> **Answer:** "In shared inference engines, pre-warmed prompt caches allow an attacker to measure response latency and infer whether another user prompted the same prefix. In probe C3, we demonstrated this timing gap on raw llama-server (51.9x latency gap, $p < 0.01$). The broker mitigates this by forcing `cache_prompt: false` on every inference call. For production multi-tenant engines, tenant-keyed cache salts (e.g., `vLLM cache_salt`) are the required route."

### 8. What happens if the broker itself is compromised?
> **Answer:** "The broker is inside our Trusted Computing Base (TCB). If an attacker achieves arbitrary code execution inside the broker, they compromise mediation. However, the broker has no network access to external egress, has a read-only filesystem, and cannot alter existing audit entries due to SQLite trigger hardening on the audit service."

### 9. How do you know the Canary Oracle doesn't produce false negatives?
> **Answer:** "Our Canary Oracle scans for exact 16-hex canary strings across 6 distinct representations: plain text, space-separated, reversed, base64, hexadecimal, and rot13. However, if a model paraphrases secret meaning without emitting the verbatim canary token, a regex matcher will miss it. We disclose this solo shortcut (S5) and specify that full semantic harm evaluation requires an ensemble harm classifier."

### 10. Why is the Blue defense progression scripted rather than live submissions?
> **Answer:** "Per design shortcut S2, Blue defenses v1, v2, and v3 are packaged as immutable Docker images. This allowed us to rigorously calibrate and reproduce a 3-round benchmark showing transition from baseline (100% breach) to partially fixed (66.7%) to certified fixed (0.0%, $n=36$) with zero false positive rate on benign inputs."

### 11. What exactly does the commit-reveal protocol prove?
> **Answer:** "Commit-reveal ensures Red submits their attack payloads before the round begins. In Phase 1, Red commits SHA-256 hashes of all challenges. In Phase 5 (reveal), the controller verifies that the revealed plaintexts match the committed hashes. This cryptographically prevents Red from retroactively changing attack payloads after seeing which defenses Blue deployed."

### 12. How does the tamper-evident audit chain work?
> **Answer:** "Every event is serialized using canonical RFC 8785 JSON, hashed with SHA-256 including the previous entry's hash, and signed with the referee's Ed25519 private key. SQLite triggers reject any SQL `UPDATE` or `DELETE`. At round close, a signed anchor checkpoint `{round_id, count, head_hash, sig}` is recorded. Offline verification requires only the log, pubkey, and checkpoint."

### 13. What if the referee's audit signing key leaks?
> **Answer:** "If the private signing key leaks on the host, an attacker could forge new valid signatures. In our local VM setup (solo shortcut S4), keys are stored in `/run/secrets/`. In production, signing keys should reside inside a Hardware Security Module (HSM) or AWS KMS with restricted IAM policies."

### 14. Are human operators blind to the attacks during the round?
> **Answer:** "In our solo development mode (S1), a single engineer builds all components. Blindness during evaluation is enforced procedurally and through cryptography: attack payloads are sealed using PyNaCl Curve25519 `SealedBox` and only decrypted in-memory by the broker inside the closed container environment."

### 15. Why did you use bearer tokens instead of mutual TLS (mTLS)?
> **Answer:** "Solo shortcut S3: within an internal container bridge where containers cannot sniff or spoof MAC addresses, bearer tokens loaded from Docker secrets provide adequate service authentication with significantly lower development overhead than full PKI and certificate rotation."

### 16. Can this architecture support hosted APIs (OpenAI / Anthropic) or GPUs?
> **Answer:** "Yes. For hosted APIs, the Model zone container is replaced by an egress gateway that terminates a restricted TLS proxy to the external provider API. For GPUs, NVIDIA Container Toolkit (`--gpus all`) maps tensor cores into the Model container, though Multi-Instance GPU (MIG) slice isolation would be needed to prevent shared GPU memory side channels."

### 17. What automated anomaly detection is implemented?
> **Answer:** "The broker validates all request schemas via Pydantic (`extra='forbid'`) and enforces 16 KB size limits. Disallowed tool calls, unrecognized fields, and unauthorized campaign tokens generate `FINDING` audit events. Full real-time behavioral anomaly detection was dropped per our pre-registered scope."

### 18. Why use harmless canaries instead of real harmful jailbreak datasets?
> **Answer:** "Canaries provide ground truth: either the model leaked the 16-hex token or it did not. This avoids the noise, ambiguity, and human grading variance of harm benchmarks, ensuring our statistical Wilson confidence intervals measure pure defense containment without subjective grading error."

### 19. Can this run on Kubernetes?
> **Answer:** "Yes. The 3 zones map directly to Kubernetes NetworkPolicies (default-deny ingress/egress per namespace), the broker maps to an Ingress Controller/Service, secrets map to Kubernetes Secrets, and container hardening maps to SecurityContext (`readOnlyRootFilesystem: true`, `capabilities: {drop: ['ALL']}`)."

### 20. What was cut from the original scope?
> **Answer:** "We strictly followed our pre-registered drop list: Probe C2 (sub-millisecond KS timing channel) was dropped per fallback E7 because network jitter dominated on a laptop VM; external RFC 3161 timestamping was replaced by local filesystem anchors (S4); and Blue defenses were scripted as container images (S2) rather than an interactive submission web API."
