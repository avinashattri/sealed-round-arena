#!/usr/bin/env python3
"""
scripts/check_env.py
Verifies runtime environment: Docker, Python, model weights, datasets, image locks.
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def check_env() -> bool:
    print("Checking environment...")
    ok = True

    print(f"  Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} ✓")

    # Check docker
    if not shutil.which("docker"):
        print("FAIL: docker binary not found in PATH", file=sys.stderr)
        ok = False
    else:
        res = subprocess.run(
            ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
        )
        if res.returncode != 0:
            print("FAIL: Docker daemon is not responding", file=sys.stderr)
            ok = False
        else:
            print("  Docker daemon responsive ✓")

    # Check model weights
    model_path = REPO_ROOT / "models" / "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    if not model_path.exists() or model_path.stat().st_size < 100_000_000:
        print(f"FAIL: Model weights missing at {model_path}", file=sys.stderr)
        ok = False
    else:
        print(f"  Model weights present ({model_path.stat().st_size / (1024 * 1024):.1f} MB) ✓")

    # Check datasets
    f1_path = REPO_ROOT / "loop" / "data" / "attacks" / "F1.json"
    benign_path = REPO_ROOT / "loop" / "data" / "benign.jsonl"
    if not f1_path.exists():
        print(f"FAIL: Attack dataset {f1_path} not found", file=sys.stderr)
        ok = False
    else:
        print("  Attack dataset F1.json ✓")

    if not benign_path.exists():
        print(f"FAIL: Benign dataset {benign_path} not found", file=sys.stderr)
        ok = False
    else:
        print("  Benign dataset benign.jsonl ✓")

    # Check locks
    img_lock = REPO_ROOT / "locks" / "images.lock.json"
    if not img_lock.exists():
        print(f"FAIL: Image lock missing at {img_lock}", file=sys.stderr)
        ok = False
    else:
        print("  Image locks present ✓")

    if ok:
        print("PASS: Environment check succeeded ✓")
    return ok


if __name__ == "__main__":
    if not check_env():
        sys.exit(1)
