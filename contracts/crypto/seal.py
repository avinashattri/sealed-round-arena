"""
Sealed-box crypto using PyNaCl Curve25519/X25519.
new_round_keys() -> (priv_hex, pub_hex)
seal(pub_hex, data: bytes) -> bytes   (ciphertext)
unseal(priv_hex, blob: bytes) -> bytes (plaintext; raises CryptoError on wrong key/tamper)
"""

from nacl.exceptions import CryptoError  # re-exported for callers
from nacl.public import PrivateKey, PublicKey, SealedBox

__all__ = ["CryptoError", "new_round_keys", "seal", "unseal"]


def new_round_keys() -> tuple[str, str]:
    """Generate a fresh Curve25519 key pair. Returns (priv_hex, pub_hex)."""
    sk = PrivateKey.generate()
    return sk.encode().hex(), sk.public_key.encode().hex()


def seal(pub_hex: str, data: bytes) -> bytes:
    """Encrypt data for the holder of the matching private key (SealedBox)."""
    pk = PublicKey(bytes.fromhex(pub_hex))
    box = SealedBox(pk)
    return box.encrypt(data)


def unseal(priv_hex: str, blob: bytes) -> bytes:
    """Decrypt a sealed blob with the private key. Raises nacl.exceptions.CryptoError on failure."""
    sk = PrivateKey(bytes.fromhex(priv_hex))
    box = SealedBox(sk)
    return box.decrypt(blob)
