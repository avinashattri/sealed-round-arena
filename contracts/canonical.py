import hashlib
import json
from typing import Any

GENESIS = "0" * 64


def canonical_json(obj: Any) -> bytes:
    """Deterministic UTF-8 JSON serialization: sorted keys, compact separators."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sha256_hex(b: bytes) -> str:
    """Compute sha256 hex digest of bytes."""
    return hashlib.sha256(b).hexdigest()


def entry_hash(prev_hash: str, fields: dict) -> str:
    """
    Compute hash of an audit entry.
    fields: every entry field except entry_hash and sig.
    """
    return sha256_hex(bytes.fromhex(prev_hash) + canonical_json(fields))
