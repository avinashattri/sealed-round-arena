"""
P3.T2: verify.py tests.
Builds a clean 12-entry log + signed checkpoint with a throwaway SigningKey.
clean = PASS; each tamper fails with a specific reason string.
"""

from datetime import UTC, datetime
from typing import Any

import pytest
from nacl.signing import SigningKey

from contracts.canonical import GENESIS, entry_hash
from contracts.crypto.sign import sign_checkpoint, sign_entry_hash
from referee.verify.tamper import ALL as TAMPERS
from referee.verify.verify import verify_audit_log

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_log(n: int, sk: SigningKey) -> list[dict[str, Any]]:
    """Build a clean hash-chained, signed log of n entries."""
    entries: list[dict[str, Any]] = []
    prev_hash = GENESIS
    sk_bytes = sk.encode()

    for seq in range(1, n + 1):
        ts = datetime.now(UTC).isoformat()
        fields: dict[str, Any] = {
            "campaign_id": "c-001",
            "round_id": "r-001",
            "challenge_id": f"ch-{seq:04d}",
            "parent": None,
            "actor": "broker",
            "event": "seal",
            "content_hash": None,
            "sealed_ref": None,
            "defense_digest": None,
            "model_digest": None,
            "policy_version": None,
            "seq": seq,
            "ts": ts,
            "prev_hash": prev_hash,
        }
        h = entry_hash(prev_hash, fields)
        sig = sign_entry_hash(sk_bytes, h)
        entry = {**fields, "entry_hash": h, "sig": sig}
        entries.append(entry)
        prev_hash = h

    return entries


def _make_checkpoint(
    entries: list[dict[str, Any]], sk: SigningKey, round_id: str = "r-001"
) -> dict[str, Any]:
    count = len(entries)
    head_hash = entries[-1]["entry_hash"] if entries else GENESIS
    sk_bytes = sk.encode()
    sig = sign_checkpoint(sk_bytes, round_id, count, head_hash)
    return {"round_id": round_id, "count": count, "head_hash": head_hash, "sig": sig}


@pytest.fixture(scope="module")
def log_and_checkpoint():
    """Return (entries, checkpoint, pubkey_hex) for a clean 12-entry log."""
    sk = SigningKey.generate()
    entries = _make_log(12, sk)
    cp = _make_checkpoint(entries, sk)
    pubkey_hex = sk.verify_key.encode().hex()
    return entries, cp, pubkey_hex


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_clean_log_passes(log_and_checkpoint):
    entries, cp, pubkey_hex = log_and_checkpoint
    valid, reasons = verify_audit_log(entries, cp, pubkey_hex)
    assert valid, f"Clean log should PASS but got reasons: {reasons}"
    assert reasons == []


def test_flip_fails_content_changed(log_and_checkpoint):
    entries, _cp, pubkey_hex = log_and_checkpoint
    tampered = TAMPERS["flip"](entries)
    # rebuild checkpoint on tampered (so we only test content, not checkpoint sig)
    valid, reasons = verify_audit_log(tampered, None, pubkey_hex)
    assert not valid, "Flip tamper should FAIL"
    combined = " ".join(reasons)
    assert "content changed" in combined, f"Expected 'content changed' in: {reasons}"


def test_delete_fails_missing_seq(log_and_checkpoint):
    entries, _cp, pubkey_hex = log_and_checkpoint
    tampered = TAMPERS["delete"](entries)
    valid, reasons = verify_audit_log(tampered, None, pubkey_hex)
    assert not valid, "Delete tamper should FAIL"
    combined = " ".join(reasons)
    assert "missing seq" in combined, f"Expected 'missing seq' in: {reasons}"


def test_reorder_fails_out_of_order(log_and_checkpoint):
    entries, _cp, pubkey_hex = log_and_checkpoint
    tampered = TAMPERS["reorder"](entries)
    valid, reasons = verify_audit_log(tampered, None, pubkey_hex)
    assert not valid, "Reorder tamper should FAIL"
    combined = " ".join(reasons)
    assert "out of order" in combined, f"Expected 'out of order' in: {reasons}"


def test_truncate_fails_truncated(log_and_checkpoint):
    entries, cp, pubkey_hex = log_and_checkpoint
    tampered = TAMPERS["truncate"](entries)
    # Use the original checkpoint so count mismatch triggers
    valid, reasons = verify_audit_log(tampered, cp, pubkey_hex)
    assert not valid, "Truncate tamper should FAIL"
    combined = " ".join(reasons)
    assert "truncated" in combined, f"Expected 'truncated' in: {reasons}"


def test_replay_fails_duplicate_seq(log_and_checkpoint):
    entries, _cp, pubkey_hex = log_and_checkpoint
    tampered = TAMPERS["replay"](entries)
    valid, reasons = verify_audit_log(tampered, None, pubkey_hex)
    assert not valid, "Replay tamper should FAIL"
    combined = " ".join(reasons)
    assert "duplicate seq" in combined, f"Expected 'duplicate seq' in: {reasons}"


def test_five_tamper_reasons_are_distinct(log_and_checkpoint):
    """All 5 tamper failure messages must be different strings."""
    entries, cp, pubkey_hex = log_and_checkpoint
    first_reasons = {}
    for name, fn in TAMPERS.items():
        tampered = fn(entries)
        cp_arg = cp if name == "truncate" else None
        _, reasons = verify_audit_log(tampered, cp_arg, pubkey_hex)
        assert reasons, f"Tamper '{name}' produced no failure reasons"
        first_reasons[name] = reasons[0]

    reason_values = list(first_reasons.values())
    unique_reasons = set(reason_values)
    assert len(unique_reasons) == 5, (
        f"Expected 5 distinct failure reasons, got {len(unique_reasons)}: {first_reasons}"
    )
