#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path

# Full candidate list of arena images
CANDIDATE_IMAGES = [
    "sra/stub:dev",
    "sra/broker:dev",
    "sra/audit:dev",
    "sra/probe:dev",
    "ghcr.io/ggml-org/llama.cpp:server",
    "sra/oracle:dev",
    "sra/red:dev",
    "sra/blue:v1",
    "sra/blue:v2",
    "sra/blue:v3",
]

LOCK_FILE = Path("locks/images.lock.json")


def get_image_digest(image_name: str) -> str | None:
    """Get RepoDigests[0] if available, else .Id. Returns None if inspect fails."""
    res = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{json .}}", image_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        return None
    try:
        data = json.loads(res.stdout)
        repo_digests = data.get("RepoDigests", [])
        if (
            repo_digests
            and isinstance(repo_digests, list)
            and len(repo_digests) > 0
            and repo_digests[0]
        ):
            return repo_digests[0]
        return data.get("Id")
    except (json.JSONDecodeError, KeyError):
        return None


def write_pins():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    locked = {}
    for img in CANDIDATE_IMAGES:
        digest = get_image_digest(img)
        if digest:
            locked[img] = digest
    LOCK_FILE.write_text(json.dumps(locked, indent=2) + "\n")
    print(f"Wrote {len(locked)} image pins to {LOCK_FILE}")


def check_pins():
    if not LOCK_FILE.exists():
        print(f"Lock file not found: {LOCK_FILE}", file=sys.stderr)
        sys.exit(1)

    locked = json.loads(LOCK_FILE.read_text())
    for img, expected in locked.items():
        actual = get_image_digest(img)
        if actual is None:
            print(f"IMAGE MISMATCH: {img} not found", file=sys.stderr)
            sys.exit(1)
        if actual != expected:
            print(f"IMAGE MISMATCH: {img} expected {expected}, got {actual}", file=sys.stderr)
            sys.exit(1)
    print(f"PASS: all {len(locked)} pinned images verified")


def main():
    parser = argparse.ArgumentParser(description="Image pinning utility")
    parser.add_argument("action", choices=["write", "check"], help="Pinning action: write or check")
    args = parser.parse_args()

    if args.action == "write":
        write_pins()
    elif args.action == "check":
        check_pins()


if __name__ == "__main__":
    main()
