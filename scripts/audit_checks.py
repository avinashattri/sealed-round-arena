#!/usr/bin/env python3
"""
scripts/audit_checks.py
Runs:
 1. Full audit log verification on real log (evidence/ or replay/)
 2. In-memory tamper tests across all 5 tamper classes
 3. Commit-reveal altered-attack check (ch-0003 commitment mismatch)
Exits 0 only if all checks pass.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from referee.verify.tamper import ALL as TAMPERS
from referee.verify.verify import verify_audit_log


def find_files():
    evidence_dir = REPO_ROOT / "evidence"
    replay_dir = REPO_ROOT / "replay"

    log_path = evidence_dir / "audit_export.jsonl"
    pubkey_path = evidence_dir / "audit_pubkey.hex"
    anchors_dir = evidence_dir / "anchors"

    if not log_path.exists() and (replay_dir / "audit_export.jsonl").exists():
        log_path = replay_dir / "audit_export.jsonl"
        pubkey_path = replay_dir / "audit_pubkey.hex"
        anchors_dir = replay_dir / "anchors"

    return log_path, pubkey_path, anchors_dir


def load_log(path: Path) -> list[dict]:
    entries = []
    if not path.exists():
        return entries
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_checkpoint(anchors_dir: Path) -> dict | None:
    if not anchors_dir.exists():
        return None
    anchors = sorted(anchors_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not anchors:
        return None
    return json.loads(anchors[0].read_text())


def run_checks(offline_only: bool = False) -> bool:
    log_path, pubkey_path, anchors_dir = find_files()

    if not log_path.exists():
        print(f"Error: Audit log not found at {log_path}", file=sys.stderr)
        return False

    entries = load_log(log_path)
    pubkey_hex = pubkey_path.read_text().strip() if pubkey_path.exists() else None
    checkpoint = load_checkpoint(anchors_dir)

    print(f"[AUDIT CHECK 1/3] Verifying real log ({len(entries)} entries)...")
    valid, reasons = verify_audit_log(entries, checkpoint, pubkey_hex)
    if not valid:
        print(f"FAIL: verify_audit_log failed: {reasons}", file=sys.stderr)
        return False
    print(f"  PASS: {len(entries)} entries verified with pubkey and anchor checkpoint.")

    print("[AUDIT CHECK 2/3] Verifying 5 tamper classes on in-memory copies...")
    tamper_caught = 0
    for name, fn in TAMPERS.items():
        tampered = fn(entries)
        cp_arg = checkpoint if name == "truncate" else None
        t_valid, t_reasons = verify_audit_log(tampered, cp_arg, pubkey_hex)
        if t_valid:
            print(f"  {name:14s}: UNEXPECTED PASS (should be caught)", file=sys.stderr)
        else:
            first_err = t_reasons[0] if t_reasons else "rejected"
            print(f"  {name:14s}: CAUGHT ({first_err})")
            tamper_caught += 1

    if tamper_caught != 5:
        print(f"FAIL: only {tamper_caught}/5 tampers caught", file=sys.stderr)
        return False
    print("  PASS: 5/5 tamper classes successfully caught.")

    print("[AUDIT CHECK 3/3] Commit-reveal altered-attack check...")
    if offline_only:
        print("  SKIPPED in offline replay mode.")
        return True

    cmd = ["make", "-C", str(REPO_ROOT), "reveal-demo"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode == 0 and "OK: the altered attack was caught" in res.stdout:
        print("  PASS: Altered attack at reveal caught with COMMITMENT MISMATCH.")
        return True
    else:
        print(f"FAIL: reveal-demo failed:\n{res.stdout}\n{res.stderr}", file=sys.stderr)
        return False


def main():
    offline = "--offline" in sys.argv
    success = run_checks(offline_only=offline)
    if not success:
        sys.exit(1)
    print("ALL AUDIT CHECKS PASSED ✓")


if __name__ == "__main__":
    main()
