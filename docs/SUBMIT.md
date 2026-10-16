# HACKATHON SUBMISSION & DEPLOYMENT CHECKLIST

> Guide and pre-flight protocol for hackathon submission and live demonstration.

---

## 1. Submission Timeline Checklists

### Phase A: Last 24 Hours
- [x] Feature freeze tag `v1.0-rc1` created and branch `release/demo` active.
- [x] Test suite passing: `make test` (60 passed) and `make lint` (clean).
- [x] Status configuration verified: `docs/status.yml` matches all 18 probes and 22 claims.
- [x] Claim wording reviewed: `docs/CLAIMS.md` has 21 backed claims, 1 honest "not demonstrated" (C18), 1 simulated (C11).
- [x] Forbidden hype words audited: zero inappropriate uses of "secure", "unhackable", "zero leak", "100%", "guarantee".
- [x] Full-size loop progression ($n=36$) recorded and certified FIXED in `replay/results/loop.json`.
- [x] All licenses credited in `README.md` (Qwen2.5-1.5B Apache-2.0, Gandalf MIT, llama.cpp MIT).

---

### Phase B: Last 6 Hours
- [x] Clean repository tree: zero sensitive files or binary weights tracked in git:
  ```bash
  # Must output OK:
  git ls-files | grep -E '\.(gguf|env|pem|key|db|sqlite3?)$' || echo OK
  
  # Must output nothing except evidence/.gitkeep and evidence/*.py:
  git log --all --name-only --pretty=format: | grep -E '^(models|secrets|shared|data/raw|evidence)/' | sort -u
  ```
- [x] Secret scanning verification:
  ```bash
  # Pre-commit gitleaks check:
  pre-commit run gitleaks --all-files
  ```
- [x] Release notes prepared: `docs/RELEASE_NOTES.md`.
- [x] Presentation script finalized: `docs/DEMO_SCRIPT.md` (7–8 minutes, failure ladder, 20 judge Q&A).
- [x] Offline replay verified: `make replay` runs in <2s with no Docker containers.

---

### Phase C: Last 1 Hour (Merge Freeze & Demo Readiness)
- [ ] Merge `release/demo` to `main` and tag `v1.0`:
  ```bash
  git checkout main
  git merge --ff-only release/demo
  git tag -a v1.0 -m "submission build v1.0"
  git push origin main v1.0
  ```
- [ ] Create GitHub Release:
  ```bash
  gh release create v1.0 --title "Sealed-Round Arena v1.0" --notes-file docs/RELEASE_NOTES.md
  ```
- [ ] Demo laptop pre-flight check:
  - Charger connected, battery > 90%.
  - Local ports 8501, 8000, 8080 free (`ss -ltn | grep -E ':(8501|8000|8080)'`).
  - Disk space healthy: `df -h .`.
  - Sudo session primed: `sudo -v`.
  - Firewall backstop applied: `make fw-on`.
  - Wi-Fi disconnected to prove offline autonomy.
  - Streamlit dashboard open in browser tab: `http://localhost:8501`.
  - Backup USB flash drive containing `git archive -o repo.zip v1.0`, slide deck PDF, and backup video MP4s.

---

## 2. Submission Artifact Links Reference

| Artifact | Location | Purpose |
|---|---|---|
| **Repository URL** | https://github.com/webraiders/sealed-round-arena | Core open-source codebase (MIT) |
| **Release v1.0** | https://github.com/webraiders/sealed-round-arena/releases/tag/v1.0 | Tagged submission release & tarball |
| **Architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 3-Zone isolation, sequence diagrams, bridges |
| **Threat Model** | [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) | 15 threats, 0-bits bound, S1–S7 disclosures |
| **Results & Benchmarks** | [docs/RESULTS.md](docs/RESULTS.md) | Probe table, loop progression, latency/fidelity |
| **Claims & Proofs** | [docs/CLAIMS.md](docs/CLAIMS.md) | 22 claims mapped to proof commands |
| **Demo Script & Q&A** | [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | 7-min walkthrough, failure ladder, 20 judge Q&As |
| **Offline Replay** | `make replay` | Instant demonstration runner without containers |
