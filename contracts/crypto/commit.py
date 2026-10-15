"""
Commit-reveal scheme.
make_commitment(items) -> (nonce_hex, commitment_hex)
  items: list of strings (attack payloads). Commitment is:
  SHA256(nonce32 || canonical_json(sorted(items)))
check_commitment(items, nonce_hex, commitment_hex) -> bool
"""

import hashlib
import os

from contracts.canonical import canonical_json


def make_commitment(items: list[str]) -> tuple[str, str]:
    """Commit to a list of items. Returns (nonce_hex, commitment_hex)."""
    nonce = os.urandom(32)
    commitment = _compute(nonce, items)
    return nonce.hex(), commitment


def check_commitment(items: list[str], nonce_hex: str, commitment_hex: str) -> bool:
    """Verify commitment against revealed nonce and items."""
    try:
        nonce = bytes.fromhex(nonce_hex)
        expected = _compute(nonce, items)
        return expected == commitment_hex.lower()
    except (ValueError, TypeError):
        return False


def _compute(nonce: bytes, items: list[str]) -> str:
    body = canonical_json(sorted(items))
    return hashlib.sha256(nonce + body).hexdigest()
