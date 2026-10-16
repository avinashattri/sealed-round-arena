#!/usr/bin/env python3
"""
scripts/build_ui_data.py
Compiles live or replay evidence into web/data.js for the standalone web application.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

THREATS_DATA = [
    {
        "rank": 1,
        "threat": "Cross-zone leakage",
        "status": "Demonstrated",
        "vector": "Probes B1, B3, B4, B5, B6",
        "mitigation": "Host iptables firewall backstop + 3 non-routed Docker bridges",
        "fail_cond": "Bridge routing or IP forwarding enabled across bridges",
    },
    {
        "rank": 2,
        "threat": "Container / kernel escape",
        "status": "Reduced",
        "vector": "CAP_NET_RAW dropped, read-only rootfs, non-root user",
        "mitigation": "Hardened runc profile with minimal privileges",
        "fail_cond": "Zero-day Linux kernel privilege escalation",
    },
    {
        "rank": 3,
        "threat": "CPU side channels",
        "status": "Not demonstrated",
        "vector": "Host baseline noise caveat, cgroup limits",
        "mitigation": "cgroup CPU share limits",
        "fail_cond": "Spectre/Meltdown L1/L2 cache cross-hyperthread leaks",
    },
    {
        "rank": 4,
        "threat": "Shared GPU memory",
        "status": "Not applicable",
        "vector": "CPU-only llama-server inference",
        "mitigation": "No GPU device nodes mapped into containers",
        "fail_cond": "GPU driver memory leaks (not used)",
    },
    {
        "rank": 5,
        "threat": "Prefix-cache timing",
        "status": "Demonstrated",
        "vector": "51.9x ratio measured on raw engine (probe C3)",
        "mitigation": "Broker strictly forces cache_prompt: false",
        "fail_cond": "Inference server re-enables global prompt caching",
    },
    {
        "rank": 6,
        "threat": "Verdict / response channel",
        "status": "Demonstrated",
        "vector": "0 bits covert channel measured across 3 rounds (probe C1)",
        "mitigation": 'Constant receipts {"status":"accepted"}, static error payloads',
        "fail_cond": "Gateway echoes user input or returns informative error stack traces",
    },
    {
        "rank": 7,
        "threat": "Timing channel",
        "status": "Not measured",
        "vector": "Probe C2 dropped per fallback E7",
        "mitigation": "0 bits verdict channel in Mode A",
        "fail_cond": "Attacker measures sub-millisecond network roundtrips",
    },
    {
        "rank": 8,
        "threat": "Audit tampering",
        "status": "Demonstrated",
        "vector": "5/5 synthetic tamper vectors caught (probe C6)",
        "mitigation": "Ed25519 hash chain over canonical RFC 8785 JSON + SQLite triggers",
        "fail_cond": "Audit signing seed compromised on host",
    },
    {
        "rank": 9,
        "threat": "Broker / Audit compromise",
        "status": "Out of scope",
        "vector": "Central referee components assumed trusted",
        "mitigation": "Policy enforced strictly at broker boundary",
        "fail_cond": "Host root compromise or arbitrary code execution in broker",
    },
    {
        "rank": 10,
        "threat": "Malicious operator / Cloud",
        "status": "Out of scope",
        "vector": "Standard single-tenant evaluation model",
        "mitigation": "SealedBox cryptographic payload sealing",
        "fail_cond": "Host administrator reads physical memory",
    },
    {
        "rank": 11,
        "threat": "Canary Oracle misdetection",
        "status": "Demonstrated",
        "vector": "Canary pattern matcher across 6 encodings",
        "mitigation": "Exact plain, spaced, reversed, b64, hex, rot13 detection",
        "fail_cond": "Model outputs semantic leak without canary tokens",
    },
    {
        "rank": 12,
        "threat": "Blue defense overfitting",
        "status": "Demonstrated",
        "vector": "Family F1 seed + 2 held-out variants + 120 benign prompts",
        "mitigation": "Scripted progression v1-v3 evaluated on pooled variants",
        "fail_cond": "Attacker employs completely novel attack taxonomies",
    },
    {
        "rank": 13,
        "threat": "Software supply chain",
        "status": "Demonstrated",
        "vector": "Image digest locking in locks/images.lock.json",
        "mitigation": "Pinning verification at container launch",
        "fail_cond": "Upstream Docker base image backdoor",
    },
    {
        "rank": 14,
        "threat": "Resource exhaustion / DoS",
        "status": "Demonstrated",
        "vector": "cgroup quotas (CPU shares, memory caps)",
        "mitigation": "Resource throttling per container zone",
        "fail_cond": "Memory exhaustion triggering kernel OOM killer",
    },
    {
        "rank": 15,
        "threat": "Human operator visibility (S1)",
        "status": "Procedural",
        "vector": "SealedBox payload encryption + procedural blindness",
        "mitigation": "Curve25519 sealed payload archives",
        "fail_cond": "Operator inspects raw packets before reveal",
    },
]


def build_bundle() -> Path:
    # Prefer evidence/ if report.json exists, otherwise replay/
    data_dir = REPO_ROOT / "evidence"
    if not (data_dir / "report.json").exists():
        data_dir = REPO_ROOT / "replay"

    report = json.loads((data_dir / "report.json").read_text(encoding="utf-8"))

    rounds_data = {}
    for r in ["r-001", "r-002", "r-003"]:
        rf = data_dir / "results" / r / "results.json"
        if not rf.exists():
            rf = REPO_ROOT / "replay" / "results" / r / "results.json"
        if rf.exists():
            rounds_data[r] = json.loads(rf.read_text(encoding="utf-8"))

    audit_sample = []
    log_file = data_dir / "audit_export.jsonl"
    if not log_file.exists():
        log_file = REPO_ROOT / "replay" / "audit_export.jsonl"

    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                line = line.strip()
                if line and (idx < 40 or (idx % 100 == 0 and idx < 1000)):
                    audit_sample.append(json.loads(line))

    pubkey_path = data_dir / "audit_pubkey.hex"
    if not pubkey_path.exists():
        pubkey_path = REPO_ROOT / "replay" / "audit_pubkey.hex"
    pubkey = pubkey_path.read_text(encoding="utf-8").strip() if pubkey_path.exists() else ""

    anchors = {}
    anchors_dir = data_dir / "anchors"
    if not anchors_dir.exists() or not list(anchors_dir.glob("*.json")):
        anchors_dir = REPO_ROOT / "replay" / "anchors"
    if anchors_dir.exists():
        for af in anchors_dir.glob("*.json"):
            anchors[af.stem] = json.loads(af.read_text(encoding="utf-8"))

    js_content = f"""// Auto-generated data bundle for Sealed-Round Arena UI
window.SRA_DATA = {{
    report: {json.dumps(report, indent=2)},
    rounds: {json.dumps(rounds_data, indent=2)},
    auditSample: {json.dumps(audit_sample, indent=2)},
    pubkey: {json.dumps(pubkey)},
    anchors: {json.dumps(anchors, indent=2)},
    threats: {json.dumps(THREATS_DATA, indent=2)}
}};
"""
    out_file = REPO_ROOT / "web" / "data.js"
    out_file.write_text(js_content, encoding="utf-8")
    return out_file


if __name__ == "__main__":
    out = build_bundle()
    print(f"Generated {out} successfully.")
