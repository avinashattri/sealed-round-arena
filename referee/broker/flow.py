import hashlib
import os
from pathlib import Path

from contracts.audit import Actor, AuditIn, Event
from contracts.crypto.seal import seal as seal_content
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

_event_counters: dict[tuple[str, str], int] = {}


def get_model_canary() -> str:
    return read_secret("MODEL_CANARY", "/run/secrets/model_canary", "secrets/model_canary.txt")


def get_public_prompt() -> str:
    if PUBLIC_PROMPT_PATH.exists():
        return PUBLIC_PROMPT_PATH.read_text(encoding="utf-8").strip()
    fallback = Path("loop/model/system_prompt_public.txt")
    if fallback.exists():
        return fallback.read_text(encoding="utf-8").strip()
    return "You are a helpful assistant."


async def audit(
    event: Event | str,
    cid: str | None = None,
    content: str | bytes | None = None,
    actor: Actor | str = Actor.BROKER,
) -> None:
    """flow.audit(event, cid, content=None, actor="broker"):
    content_hash = sha256(content); content sealed with the round public key
    to /sealed/<round>/<cid>.<event>.<n>.bin; sealed_ref set; failure raises.
    """
    round_id = manager.round_id
    campaign_id = manager.campaign_id

    content_hash = None
    sealed_ref = None

    if content is not None:
        if isinstance(content, str):
            content_bytes = content.encode("utf-8")
        else:
            content_bytes = content
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        if manager.round_pub_hex:
            cid_str = cid or "none"
            event_name = event.value if isinstance(event, Event) else str(event)
            key = (cid_str, event_name)
            _event_counters[key] = _event_counters.get(key, 0) + 1
            n = _event_counters[key]

            ciphertext = seal_content(manager.round_pub_hex, content_bytes)
            sealed_base = Path(os.environ.get("SEALED_DIR", "/sealed"))
            sealed_dir = sealed_base / round_id
            sealed_dir.mkdir(parents=True, exist_ok=True)
            fpath = sealed_dir / f"{cid_str}.{event_name}.{n}.bin"
            fpath.write_bytes(ciphertext)
            sealed_ref = str(fpath)

    actor_val = Actor(actor) if isinstance(actor, str) else actor
    event_val = Event(event) if isinstance(event, str) else event

    entry = AuditIn(
        campaign_id=campaign_id,
        round_id=round_id,
        challenge_id=cid,
        actor=actor_val,
        event=event_val,
        content_hash=content_hash,
        sealed_ref=sealed_ref,
        defense_digest=manager.defense_digest,
        model_digest=manager.model_digest,
        policy_version=1,
    )
    await call_audit(entry)


async def execute_submit_flow(req: Submit) -> Receipt:
    ch_id = req.challenge_id

    # Step 1: Audit request_received & gateway_decision ALLOW
    await audit(Event.REQUEST_RECEIVED, ch_id, content=req.payload, actor=Actor.BROKER)

    await audit(
        Event.GATEWAY_DECISION,
        ch_id,
        content=GatewayDecision.ALLOW.encode("utf-8"),
        actor=Actor.BROKER,
    )

    # Step 2: Call blue filter on input
    in_verdict = await call_blue_filter(
        "/filter/input", FilterRequest(challenge_id=ch_id, text=req.payload)
    )

    await audit(
        Event.BLUE_INPUT_VERDICT,
        ch_id,
        content=f"{in_verdict.verdict}:{in_verdict.reason_code}".encode(),
        actor=Actor.BLUE,
    )

    if in_verdict.verdict == Verdict.FLAG:
        await audit(
            Event.GATEWAY_DECISION,
            ch_id,
            content=GatewayDecision.REVIEW.encode("utf-8"),
            actor=Actor.BROKER,
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

    submit_n = manager.next_submit_n()
    cache_on = os.environ.get("MODEL_CACHE", "off").lower() in ("on", "true", "1")
    model_resp = await call_model(
        messages=messages,
        temperature=manager.temperature,
        seed=manager.seed_base + submit_n,
        max_tokens=req.max_tokens,
        cache_prompt=cache_on,
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
            await audit(
                Event.FINDING,
                ch_id,
                content=f"disallowed_tool:{tool_name}".encode(),
                actor=Actor.BROKER,
            )
            # Block unauthorized tool output
            return Receipt(challenge_id=ch_id, status="accepted")

    await audit(
        Event.MODEL_RESPONSE,
        ch_id,
        content=model_text.encode("utf-8"),
        actor=Actor.MODEL,
    )

    # Step 5: Call blue filter on output
    out_verdict = await call_blue_filter(
        "/filter/output", FilterRequest(challenge_id=ch_id, text=model_text)
    )

    await audit(
        Event.BLUE_OUTPUT_VERDICT,
        ch_id,
        content=f"{out_verdict.verdict}:{out_verdict.reason_code}".encode(),
        actor=Actor.BLUE,
    )

    if out_verdict.verdict != Verdict.PASS:
        return Receipt(challenge_id=ch_id, status="accepted")

    # Step 6: Call oracle scoring
    oracle_res = await call_oracle(OracleRequest(challenge_id=ch_id, text=model_text))

    oracle_content = f"leak={oracle_res.leak}:matched={','.join(oracle_res.matched)}".encode()
    await audit(
        Event.ORACLE_SCORE,
        ch_id,
        content=oracle_content,
        actor=Actor.ORACLE,
    )

    # Step 7: Audit delivered
    await audit(
        Event.DELIVERED,
        ch_id,
        content=model_text.encode("utf-8"),
        actor=Actor.BROKER,
    )

    # Red receives constant "accepted" receipt
    return Receipt(challenge_id=ch_id, status="accepted")
