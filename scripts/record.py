#!/usr/bin/env python3
"""
scripts/record.py
Copies validated evidence subset into replay/, generates meta.json,
and validates that the recorded bundle verifies offline.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def record():
    evidence_dir = REPO_ROOT / "evidence"
    replay_dir = REPO_ROOT / "replay"
    docs_dir = REPO_ROOT / "docs"

    if not evidence_dir.exists():
        print("Error: evidence directory does not exist.", file=sys.stderr)
        sys.exit(1)

    replay_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy results/
    src_results = evidence_dir / "results"
    dst_results = replay_dir / "results"
    if src_results.exists():
        if dst_results.exists():
            shutil.rmtree(dst_results)
        shutil.copytree(src_results, dst_results)
        print(f"Copied {src_results} -> {dst_results}")

    # 2. Copy audit files
    for fname in ["audit_export.jsonl", "audit_pubkey.hex", "report.json"]:
        src = evidence_dir / fname
        if src.exists():
            shutil.copy2(src, replay_dir / fname)
            print(f"Copied {src} -> {replay_dir / fname}")

    # 3. Copy anchors/
    src_anchors = evidence_dir / "anchors"
    dst_anchors = replay_dir / "anchors"
    if src_anchors.exists():
        if dst_anchors.exists():
            shutil.rmtree(dst_anchors)
        shutil.copytree(src_anchors, dst_anchors)
        print(f"Copied {src_anchors} -> {dst_anchors}")

    # 4. Copy status.yml
    src_status = docs_dir / "status.yml"
    if src_status.exists():
        shutil.copy2(src_status, replay_dir / "status.yml")
        print(f"Copied {src_status} -> {replay_dir / 'status.yml'}")

    # 5. Generate meta.json
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
        ).strip()
    except (subprocess.SubprocessError, OSError):
        commit = "unknown"

    meta = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "machine": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "commit": commit,
        "runtime": os.environ.get("MODEL_RUNTIME", "runc"),
        "size": "full",
    }
    (replay_dir / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote {replay_dir / 'meta.json'}")

    # 6. Verify replay log offline
    res = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "audit_checks.py"), "--offline"],
        check=False,
    )
    if res.returncode != 0:
        print("FAIL: Replay verification failed!", file=sys.stderr)
        sys.exit(1)
    print("SUCCESS: Recorded bundle verified offline ✓")


if __name__ == "__main__":
    record()
