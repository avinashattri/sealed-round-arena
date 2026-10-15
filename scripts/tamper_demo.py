#!/usr/bin/env python3
"""
STAND-IN demo: apply all 5 tampers to an in-memory copy of the real audit log
and print each failure reason. Never writes to or modifies the real log.
"""

import json
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from referee.verify.tamper import ALL as TAMPERS
from referee.verify.verify import verify_audit_log

LOG_PATH = Path("evidence/audit_export.jsonl")
PUBKEY_PATH = Path("evidence/audit_pubkey.hex")
ANCHORS_DIR = Path("evidence/anchors")


def load_log(path: Path) -> list[dict]:
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_checkpoint(anchors_dir: Path) -> dict | None:
    if not anchors_dir.exists():
        return None
    anchors = sorted(anchors_dir.glob("*.json"), reverse=True)
    if not anchors:
        return None
    return json.loads(anchors[0].read_text())


def main():
    if not LOG_PATH.exists():
        print(
            f"STAND-IN: {LOG_PATH} not found. Run a round first to generate evidence.",
            file=sys.stderr,
        )
        sys.exit(1)

    entries = load_log(LOG_PATH)
    pubkey_hex = PUBKEY_PATH.read_text().strip() if PUBKEY_PATH.exists() else None
    checkpoint = load_checkpoint(ANCHORS_DIR)

    print(f"Tamper demo on {len(entries)}-entry log (in-memory only, real log untouched)")
    print("-" * 60)

    all_pass = True
    for name, fn in TAMPERS.items():
        tampered = fn(entries)  # in-memory copy; real log untouched
        cp_arg = checkpoint if name == "truncate" else None
        valid, reasons = verify_audit_log(tampered, cp_arg, pubkey_hex)
        if valid:
            print(f"  {name:12s}: UNEXPECTED PASS (should have failed)")
            all_pass = False
        else:
            first_reason = reasons[0]
            print(f"  {name:12s}: FAIL — {first_reason}")

    print("-" * 60)
    if all_pass:
        print("tamper-demo: all 5 tampers detected ✓")
    else:
        print("tamper-demo: WARNING — some tampers not caught", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
