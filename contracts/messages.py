from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CAMPAIGN_ID_REGEX = r"^c-[0-9]{3}$"
ROUND_ID_REGEX = r"^r-[0-9]{3}$"
CHALLENGE_ID_REGEX = r"^ch-[0-9]{4}$"


class Verdict(StrEnum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    FLAG = "FLAG"


class ReasonCode(StrEnum):
    R00 = "R00"  # none
    R01 = "R01"  # injection phrase
    R02 = "R02"  # encoded content
    R03 = "R03"  # policy
    R04 = "R04"  # prompt/secret-leak pattern
    R05 = "R05"  # classifier
    R99 = "R99"  # error (fail closed)


class GatewayDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REVIEW = "REVIEW"


class BaseContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Submit(BaseContract):
    campaign_id: str = Field(pattern=CAMPAIGN_ID_REGEX)
    round_id: str = Field(pattern=ROUND_ID_REGEX)
    challenge_id: str = Field(pattern=CHALLENGE_ID_REGEX)
    payload: str = Field(min_length=1, max_length=4000)
    max_tokens: int = Field(default=128, ge=1, le=256)


class Receipt(BaseContract):
    challenge_id: str = Field(pattern=CHALLENGE_ID_REGEX)
    status: Literal["accepted", "rejected"]


class FilterRequest(BaseContract):
    challenge_id: str = Field(pattern=CHALLENGE_ID_REGEX)
    text: str = Field(max_length=8000)


class FilterVerdict(BaseContract):
    verdict: Verdict
    reason_code: ReasonCode


class OracleRequest(BaseContract):
    challenge_id: str = Field(pattern=CHALLENGE_ID_REGEX)
    text: str = Field(max_length=8000)


class OracleResult(BaseContract):
    leak: bool
    matched: list[Literal["plain", "spaced", "reversed", "base64", "hex", "rot13"]]
    harm: bool | None = None
