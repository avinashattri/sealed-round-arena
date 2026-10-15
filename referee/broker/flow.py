import hashlib
import os
from pathlib import Path

from contracts.audit import Actor, AuditIn, Event
from contracts.messages import (
    FilterRequest,
    GatewayDecision,
    OracleRequest,
    Receipt,
    Submit,
    Verdict,
)
from contracts.policy import check_policy
from contracts.prompt import build_system_prompt

try:
    from referee.broker.clients import (
        call_audit,
        call_blue_filter,
        call_model,
        call_oracle,
        read_secret,
    )
    from referee.broker.state import manager
except ModuleNotFoundError:
    from broker.clients import (
        call_audit,
        call_blue_filter,
        call_model,
        call_oracle,
        read_secret,
    )
    from broker.state import manager

PUBLIC_PROMPT_PATH = Path(os.environ.get("PUBLIC_PROMPT_PATH", "/app/system_prompt_public.txt"))


def get_model_canary() -> str:
    return read_secret("MODEL_CANARY", "/run/secrets/model_canary", "secrets/model_canary.txt")


def get_public_prompt() -> str:
    if PUBLIC_PROMPT_PATH.exists():
        return PUBLIC_PROMPT_PATH.read_text(encoding="utf-8").strip()
    fallback = Path("loop/model/system_prompt_public.txt")
    if fallback.exists():
        return fallback.read_text(encoding="utf-8").strip()
    return "You are a helpful assistant."


async def execute_submit_flow(req: Submit) -> Receipt:
    campaign_id = manager.campaign_id
    round_id = manager.round_id
    ch_id = req.challenge_id

    req_hash = hashlib.sha256(req.payload.encode("utf-8")).hexdigest()

    # Step 1: Audit request_received & gateway_decision ALLOW
    await call_audit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            challenge_id=ch_id,
            actor=Actor.BROKER,
            event=Event.REQUEST_RECEIVED,
            content_hash=req_hash,
            defense_digest=manager.defense_digest,
            model_digest=manager.model_digest,
            policy_version=1,
        )
    )

    await call_audit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            challenge_id=ch_id,
            actor=Actor.BROKER,
            event=Event.GATEWAY_DECISION,
            content_hash=hashlib.sha256(GatewayDecision.ALLOW.encode()).hexdigest(),
        )
    )

    # Step 2: Call blue filter on input
    in_verdict = await call_blue_filter(
        "/filter/input", FilterRequest(challenge_id=ch_id, text=req.payload)
    )

    await call_audit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            challenge_id=ch_id,
            actor=Actor.BLUE,
            event=Event.BLUE_INPUT_VERDICT,
            content_hash=hashlib.sha256(
                f"{in_verdict.verdict}:{in_verdict.reason_code}".encode()
            ).hexdigest(),
        )
    )

    if in_verdict.verdict == Verdict.FLAG:
        await call_audit(
            AuditIn(
                campaign_id=campaign_id,
                round_id=round_id,
                challenge_id=ch_id,
                actor=Actor.BROKER,
                event=Event.GATEWAY_DECISION,
                content_hash=hashlib.sha256(GatewayDecision.REVIEW.encode()).hexdigest(),
            )
        )

    if in_verdict.verdict != Verdict.PASS:
        # Input blocked by Blue defense
        return Receipt(challenge_id=ch_id, status="accepted")

    # Step 3: Query Model
    canary = get_model_canary()
    public_prompt = get_public_prompt()
    system_prompt = build_system_prompt(public_prompt, canary)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.payload},
    ]

    model_resp = await call_model(
        messages=messages,
        temperature=0.0,
        seed=1,
        max_tokens=req.max_tokens,
    )

    choice = model_resp.get("choices", [{}])[0]
    message = choice.get("message", {})
    model_text = message.get("content", "") or ""

    # Step 4: Enforce tool call allowlist (A4 probe)
    tool_calls = message.get("tool_calls", [])
    for tc in tool_calls:
        func = tc.get("function", {})
        tool_name = func.get("name", "")
        if not check_policy("model", "tool_call", tool_name):
            # Unauthorized tool call detected
            await call_audit(
                AuditIn(
                    campaign_id=campaign_id,
                    round_id=round_id,
                    challenge_id=ch_id,
                    actor=Actor.BROKER,
                    event=Event.FINDING,
                    content_hash=hashlib.sha256(
                        f"disallowed_tool:{tool_name}".encode()
                    ).hexdigest(),
                )
            )
            # Block unauthorized tool output
            return Receipt(challenge_id=ch_id, status="accepted")

    resp_hash = hashlib.sha256(model_text.encode("utf-8")).hexdigest()
    await call_audit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            challenge_id=ch_id,
            actor=Actor.MODEL,
            event=Event.MODEL_RESPONSE,
            content_hash=resp_hash,
        )
    )

    # Step 5: Call blue filter on output
    out_verdict = await call_blue_filter(
        "/filter/output", FilterRequest(challenge_id=ch_id, text=model_text)
    )

    await call_audit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            challenge_id=ch_id,
            actor=Actor.BLUE,
            event=Event.BLUE_OUTPUT_VERDICT,
            content_hash=hashlib.sha256(
                f"{out_verdict.verdict}:{out_verdict.reason_code}".encode()
            ).hexdigest(),
        )
    )

    if out_verdict.verdict != Verdict.PASS:
        return Receipt(challenge_id=ch_id, status="accepted")

    # Step 6: Call oracle scoring
    oracle_res = await call_oracle(OracleRequest(challenge_id=ch_id, text=model_text))

    oracle_hash = hashlib.sha256(
        f"leak={oracle_res.leak}:matched={','.join(oracle_res.matched)}".encode()
    ).hexdigest()

    await call_audit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            challenge_id=ch_id,
            actor=Actor.ORACLE,
            event=Event.ORACLE_SCORE,
            content_hash=oracle_hash,
        )
    )

    # Step 7: Audit delivered
    await call_audit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            challenge_id=ch_id,
            actor=Actor.BROKER,
            event=Event.DELIVERED,
            content_hash=resp_hash,
        )
    )

    # Red receives constant "accepted" receipt
    return Receipt(challenge_id=ch_id, status="accepted")
