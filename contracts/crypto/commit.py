import hashlib

from contracts.canonical import canonical_json


def make_commitment(nonce_bytes: bytes, challenge_id: str, payload: str) -> str:
    """Commitment = SHA256(nonce16 + canonical_json({challenge_id: payload}))."""
    if len(nonce_bytes) != 16:
        raise ValueError("Nonce must be exactly 16 bytes")
    body = canonical_json({challenge_id: payload})
    return hashlib.sha256(nonce_bytes + body).hexdigest()


def verify_commitment(
    commitment_hex: str, nonce_bytes: bytes, challenge_id: str, payload: str
) -> bool:
    """Verify an attack commitment against the revealed nonce, challenge_id, and payload."""
    try:
        expected = make_commitment(nonce_bytes, challenge_id, payload)
        return commitment_hex.lower() == expected.lower()
    except (ValueError, TypeError):
        return False
