import pytest
from pydantic import ValidationError

from contracts.canonical import GENESIS, canonical_json, entry_hash
from contracts.messages import Submit
from contracts.policy import check_policy
from contracts.rounds import RoundState, can_move


def test_1_extra_field_in_submit_raises():
    with pytest.raises(ValidationError):
        Submit(
            campaign_id="c-001",
            round_id="r-001",
            challenge_id="ch-0001",
            payload="valid payload",
            extra_field="disallowed",
        )


def test_2_4001_char_payload_raises():
    with pytest.raises(ValidationError):
        Submit(
            campaign_id="c-001",
            round_id="r-001",
            challenge_id="ch-0001",
            payload="x" * 4001,
        )


def test_3_canonical_json_is_key_order_independent():
    obj1 = {"z": 1, "a": 2, "m": {"b": 3, "a": 4}}
    obj2 = {"a": 2, "z": 1, "m": {"a": 4, "b": 3}}
    assert canonical_json(obj1) == canonical_json(obj2)


def test_4_policy_lookup_for_an_unlisted_principal_is_false():
    assert check_policy("unlisted_hacker", "submit", "/submit") is False


def test_5_can_move_sealed_closed_is_false():
    assert can_move(RoundState.SEALED, RoundState.CLOSED) is False
    assert can_move("SEALED", "CLOSED") is False


def test_6_golden_hash():
    # Golden hash computed for GENESIS and {"a": 1}
    expected = "b06a229070741292512e8760f470dd7a4c46ccfdf253df781d88dabe58c1ccb1"
    actual = entry_hash(GENESIS, {"a": 1})
    assert actual == expected


# ── P3.T3 Crypto tests ─────────────────────────────────────────────────────


def test_7_commitment_roundtrip():
    """make_commitment(items) -> (nonce_hex, commitment_hex); check_commitment verifies."""
    from contracts.crypto.commit import check_commitment, make_commitment

    items = ["attack A", "attack B", "attack C"]
    nonce_hex, commitment_hex = make_commitment(items)

    assert len(nonce_hex) == 64  # 32 bytes = 64 hex chars
    assert len(commitment_hex) == 64  # SHA256 = 64 hex chars
    assert check_commitment(items, nonce_hex, commitment_hex) is True


def test_8_commitment_fails_when_payload_changes():
    """Altering one item breaks the commitment."""
    from contracts.crypto.commit import check_commitment, make_commitment

    items = ["attack A", "attack B"]
    nonce_hex, commitment_hex = make_commitment(items)

    tampered = ["attack A", "attack B TAMPERED"]
    assert check_commitment(tampered, nonce_hex, commitment_hex) is False


def test_9_seal_unseal_roundtrip():
    """seal(pub_hex, data) / unseal(priv_hex, blob) roundtrip."""
    from contracts.crypto.seal import new_round_keys, seal, unseal

    priv_hex, pub_hex = new_round_keys()
    plaintext = b"super secret attack payload"
    blob = seal(pub_hex, plaintext)
    recovered = unseal(priv_hex, blob)

    assert recovered == plaintext


def test_10_wrong_private_key_raises():
    """Unsealing with wrong private key raises CryptoError."""
    from nacl.exceptions import CryptoError

    from contracts.crypto.seal import CryptoError as SealCryptoError
    from contracts.crypto.seal import new_round_keys, seal, unseal

    assert SealCryptoError is CryptoError

    _, pub_hex = new_round_keys()
    wrong_priv_hex, _ = new_round_keys()

    blob = seal(pub_hex, b"secret")
    import pytest

    with pytest.raises(CryptoError):
        unseal(wrong_priv_hex, blob)


def test_11_flipped_ciphertext_byte_raises():
    """Bit-flip in ciphertext raises CryptoError."""
    from nacl.exceptions import CryptoError

    from contracts.crypto.seal import new_round_keys, seal, unseal

    priv_hex, pub_hex = new_round_keys()
    blob = bytearray(seal(pub_hex, b"secret"))
    blob[10] ^= 0xFF  # flip bits in one byte

    import pytest

    with pytest.raises(CryptoError):
        unseal(priv_hex, bytes(blob))
