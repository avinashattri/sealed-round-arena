from nacl.public import PrivateKey, PublicKey, SealedBox


def seal_payload(public_key_bytes: bytes, plaintext: bytes) -> bytes:
    """Encrypt payload using PyNaCl SealedBox with recipient public key."""
    pk = PublicKey(public_key_bytes)
    box = SealedBox(pk)
    return box.encrypt(plaintext)


def unseal_payload(private_key_bytes: bytes, ciphertext: bytes) -> bytes:
    """Decrypt payload using PyNaCl SealedBox with private key."""
    sk = PrivateKey(private_key_bytes)
    box = SealedBox(sk)
    return box.decrypt(ciphertext)
