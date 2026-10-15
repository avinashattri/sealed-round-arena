from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

from contracts.canonical import canonical_json


def sign_entry_hash(signing_key_bytes: bytes, entry_hash_hex: str) -> str:
    """Sign entry_hash using Ed25519 (PyNaCl) over raw bytes of hash."""
    sk = SigningKey(signing_key_bytes)
    sig = sk.sign(bytes.fromhex(entry_hash_hex)).signature
    return sig.hex()


def verify_entry_hash(verify_key_bytes: bytes, entry_hash_hex: str, sig_hex: str) -> bool:
    """Verify Ed25519 signature over raw bytes of hash."""
    try:
        vk = VerifyKey(verify_key_bytes)
        vk.verify(bytes.fromhex(entry_hash_hex), bytes.fromhex(sig_hex))
        return True
    except (BadSignatureError, ValueError):
        return False


def sign_checkpoint(signing_key_bytes: bytes, round_id: str, count: int, head_hash: str) -> str:
    """Sign Checkpoint using Ed25519 over canonical_json({round_id, count, head_hash})."""
    sk = SigningKey(signing_key_bytes)
    payload = canonical_json({"count": count, "head_hash": head_hash, "round_id": round_id})
    sig = sk.sign(payload).signature
    return sig.hex()


def verify_checkpoint(
    verify_key_bytes: bytes, round_id: str, count: int, head_hash: str, sig_hex: str
) -> bool:
    """Verify Ed25519 signature over canonical_json({round_id, count, head_hash})."""
    try:
        vk = VerifyKey(verify_key_bytes)
        payload = canonical_json({"count": count, "head_hash": head_hash, "round_id": round_id})
        vk.verify(payload, bytes.fromhex(sig_hex))
        return True
    except (BadSignatureError, ValueError):
        return False
