from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contracts.messages import CAMPAIGN_ID_REGEX, CHALLENGE_ID_REGEX, ROUND_ID_REGEX

HEX_64_REGEX = r"^[0-9a-f]{64}$"


class Actor(StrEnum):
    RED = "red"
    BLUE = "blue"
    MODEL = "model"
    BROKER = "broker"
    ORACLE = "oracle"
    CONTROLLER = "controller"


class Event(StrEnum):
    CAMPAIGN_CREATED = "campaign_created"
    COMMIT = "commit"
    SEAL = "seal"
    REQUEST_RECEIVED = "request_received"
    GATEWAY_DECISION = "gateway_decision"
    BLUE_INPUT_VERDICT = "blue_input_verdict"
    MODEL_RESPONSE = "model_response"
    BLUE_OUTPUT_VERDICT = "blue_output_verdict"
    ORACLE_SCORE = "oracle_score"
    DELIVERED = "delivered"
    CLOSE = "close"
    CHECKPOINT = "checkpoint"
    REVEAL = "reveal"
    FINDING = "finding"
    MITIGATION = "mitigation"
    RETEST_RESULT = "retest_result"
    PROBE_RESULT = "probe_result"
    RESET = "reset"


class BaseAudit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuditIn(BaseAudit):
    campaign_id: str = Field(pattern=CAMPAIGN_ID_REGEX)
    round_id: str = Field(pattern=ROUND_ID_REGEX)
    challenge_id: str | None = Field(default=None, pattern=CHALLENGE_ID_REGEX)
    parent: int | None = Field(default=None, ge=0)
    actor: Actor
    event: Event
    content_hash: str | None = Field(default=None, pattern=HEX_64_REGEX)
    sealed_ref: str | None = None
    defense_digest: str | None = None
    model_digest: str | None = None
    policy_version: int | None = None


class AuditEntry(BaseAudit):
    campaign_id: str = Field(pattern=CAMPAIGN_ID_REGEX)
    round_id: str = Field(pattern=ROUND_ID_REGEX)
    challenge_id: str | None = Field(default=None, pattern=CHALLENGE_ID_REGEX)
    parent: int | None = Field(default=None, ge=0)
    actor: Actor
    event: Event
    content_hash: str | None = Field(default=None, pattern=HEX_64_REGEX)
    sealed_ref: str | None = None
    defense_digest: str | None = None
    model_digest: str | None = None
    policy_version: int | None = None
    seq: int = Field(ge=0)
    ts: str  # ISO UTC
    prev_hash: str = Field(pattern=HEX_64_REGEX)
    entry_hash: str = Field(pattern=HEX_64_REGEX)
    sig: str


class Checkpoint(BaseAudit):
    round_id: str = Field(pattern=ROUND_ID_REGEX)
    count: int = Field(ge=0)
    head_hash: str = Field(pattern=HEX_64_REGEX)
    sig: str
