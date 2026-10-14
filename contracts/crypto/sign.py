from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


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
