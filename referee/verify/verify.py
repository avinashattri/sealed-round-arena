import argparse
import json
import sys
from pathlib import Path
from typing import Any

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

from contracts.canonical import GENESIS, canonical_json, entry_hash


def verify_audit_log(
    entries: list[dict[str, Any]],
    checkpoint: dict[str, Any] | None = None,
    pubkey_hex: str | None = None,
) -> tuple[bool, list[str]]:
    """
    Verify audit log entries and checkpoint.
    Returns (is_valid, list_of_reasons).
    Possible reasons:
      - 'duplicate seq'
      - 'missing seq'
      - 'out of order'
      - 'broken chain'
      - 'content changed'
      - 'bad signature'
      - 'truncated'
    """
    reasons = []

    verify_key = None
    if pubkey_hex:
        try:
            verify_key = VerifyKey(bytes.fromhex(pubkey_hex))
        except (ValueError, TypeError) as e:
            reasons.append(f"bad signature: invalid verify key ({e})")

    # Checkpoint pre-check for truncation
    if checkpoint is not None:
        cp_count = checkpoint.get("count", 0)
        if len(entries) < cp_count:
            reasons.append(f"truncated: expected {cp_count} entries, found {len(entries)}")

    seen_seqs = set()
    prev_seq = 0
    prev_hash = GENESIS

    for _idx, entry in enumerate(entries):
        seq = entry.get("seq")
        if seq is None:
            reasons.append("out of order: missing seq field")
            continue

        # Sequence checks
        if seq in seen_seqs:
            reasons.append(f"duplicate seq: {seq} encountered more than once")
        elif seq < prev_seq:
            reasons.append(f"out of order: seq {seq} after {prev_seq}")
        elif seq > prev_seq + 1:
            reasons.append(f"missing seq: expected {prev_seq + 1}, got {seq}")

        seen_seqs.add(seq)
        prev_seq = seq

        # Chain check
        entry_prev_hash = entry.get("prev_hash")
        if entry_prev_hash != prev_hash:
            reasons.append(f"broken chain at seq {seq}: prev_hash {entry_prev_hash} != {prev_hash}")

        # Content hash recomputation
        claimed_entry_hash = entry.get("entry_hash")
        fields_to_hash = {k: v for k, v in entry.items() if k not in ("entry_hash", "sig")}
        recomputed_hash = entry_hash(entry_prev_hash or GENESIS, fields_to_hash)
        if claimed_entry_hash != recomputed_hash:
            reasons.append(
                f"content changed at seq {seq}: {claimed_entry_hash} != {recomputed_hash}"
            )

        # Signature verification
        sig_hex = entry.get("sig")
        if verify_key and sig_hex and claimed_entry_hash:
            try:
                verify_key.verify(bytes.fromhex(claimed_entry_hash), bytes.fromhex(sig_hex))
            except (BadSignatureError, ValueError) as e:
                reasons.append(f"bad signature at seq {seq}: {e}")

        prev_hash = claimed_entry_hash

    # Checkpoint verification
    if checkpoint is not None:
        cp_head = checkpoint.get("head_hash")
        cp_sig = checkpoint.get("sig")
        cp_round = checkpoint.get("round_id")
        cp_count = checkpoint.get("count", 0)

        # Check head hash
        if (
            len(entries) > 0
            and len(entries) == cp_count
            and entries[-1].get("entry_hash") != cp_head
        ):
            reasons.append(
                f"broken chain: checkpoint head_hash {cp_head} != last entry {entries[-1].get('entry_hash')}"
            )

        # Verify checkpoint signature
        if verify_key and cp_sig:
            cp_payload = canonical_json(
                {
                    "round_id": cp_round,
                    "count": cp_count,
                    "head_hash": cp_head,
                }
            )
            try:
                verify_key.verify(cp_payload, bytes.fromhex(cp_sig))
            except (BadSignatureError, ValueError) as e:
                reasons.append(f"bad signature on checkpoint: {e}")

    is_valid = len(reasons) == 0
    return is_valid, reasons


def main():
    parser = argparse.ArgumentParser(description="Verify audit log integrity")
    parser.add_argument(
        "log", nargs="?", default=None, help="Path to audit log JSONL file (positional)"
    )
    parser.add_argument(
        "--log",
        dest="log_flag",
        default=None,
        help="Path to audit log JSONL file (flag, deprecated)",
    )
    parser.add_argument("--checkpoint", default=None, help="Path to checkpoint JSON file")
    parser.add_argument("--pubkey", default=None, help="Path to Ed25519 public key hex file")
    args = parser.parse_args()

    log_path = Path(args.log or args.log_flag)
    if not log_path.exists():
        sys.exit(f"Log file not found: {log_path}")

    entries = []
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    checkpoint = None
    if args.checkpoint:
        cp_path = Path(args.checkpoint)
        if cp_path.exists():
            checkpoint = json.loads(cp_path.read_text(encoding="utf-8"))

    pubkey_hex = None
    if args.pubkey:
        pk_path = Path(args.pubkey)
        if pk_path.exists():
            pubkey_hex = pk_path.read_text().strip()

    valid, reasons = verify_audit_log(entries, checkpoint, pubkey_hex)
    if valid:
        print(f"PASS: {len(entries)} entries, chain, signatures and checkpoint verified")
        sys.exit(0)
    else:
        print("FAIL:")
        for r in reasons:
            print(f"  - {r}")
        sys.exit(1)


if __name__ == "__main__":
    main()
