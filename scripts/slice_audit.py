#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nacl.signing import SigningKey

from contracts.canonical import GENESIS, canonical_json, entry_hash


def main():
    sk = SigningKey.generate()
    vk = sk.verify_key

    pubkey_path = Path("/tmp/slice_pubkey.hex")
    log_path = Path("/tmp/slice_audit.jsonl")
    cp_path = Path("/tmp/slice_checkpoint.json")

    pubkey_path.write_text(vk.encode().hex())

    events = [
        ("broker", "campaign_created", {"policy_version": 1}),
        ("red", "commit", {"content_hash": "a" * 64}),
        ("broker", "seal", {"sealed_ref": "box-001"}),
    ]

    entries = []
    prev_hash = GENESIS

    for seq, (actor, event, extra) in enumerate(events):
        fields = {
            "campaign_id": "c-001",
            "round_id": "r-001",
            "seq": seq,
            "ts": f"2026-10-15T00:00:0{seq}Z",
            "actor": actor,
            "event": event,
            "prev_hash": prev_hash,
            **extra,
        }
        e_hash = entry_hash(prev_hash, fields)
        sig = sk.sign(bytes.fromhex(e_hash)).signature.hex()
        entry = {**fields, "entry_hash": e_hash, "sig": sig}
        entries.append(entry)
        prev_hash = e_hash

    with open(log_path, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(e) + "\n" for e in entries)

    head_hash = entries[-1]["entry_hash"]
    cp_data = {
        "round_id": "r-001",
        "count": len(entries),
        "head_hash": head_hash,
    }
    cp_sig = sk.sign(canonical_json(cp_data)).signature.hex()
    checkpoint = {**cp_data, "sig": cp_sig}
    cp_path.write_text(json.dumps(checkpoint, indent=2))

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT}:{REPO_ROOT}/referee:{REPO_ROOT}/loop"

    cmd = [
        sys.executable,
        "-m",
        "referee.verify.verify",
        "--log",
        str(log_path),
        "--checkpoint",
        str(cp_path),
        "--pubkey",
        str(pubkey_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, env=env, check=False)
    if res.returncode != 0:
        print("verify.py failed:\n", res.stderr or res.stdout)
        sys.exit(res.returncode)
    print(res.stdout.strip())


if __name__ == "__main__":
    main()
