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
