import hmac
import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from contracts.audit import AuditIn
from contracts.messages import Receipt, Submit
from contracts.policy import check_policy
from contracts.rounds import RoundState

try:
    from referee.broker.admin import get_admin_token
    from referee.broker.flow import execute_submit_flow
    from referee.broker.state import manager
except ModuleNotFoundError:
    from broker.admin import get_admin_token
    from broker.flow import execute_submit_flow
    from broker.state import manager

app = FastAPI(title="Sealed Round Arena - Broker")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "bad request"})


MAX_BODY_SIZE = 16 * 1024  # 16 KB


def get_tokens_registry() -> dict[str, Any]:
    if "TOKENS_JSON" in os.environ:
        try:
            return json.loads(os.environ["TOKENS_JSON"])
        except (json.JSONDecodeError, TypeError):
            pass

    candidates = [
        os.environ.get("TOKENS_FILE"),
        "/run/secrets/tokens",
        "secrets/tokens.json",
    ]
    for c in candidates:
        if c and Path(c).exists():
            try:
                return json.loads(Path(c).read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/submit", response_model=Receipt)
async def submit(request: Request, authorization: str | None = Header(None)):
    # 1. Body size limit
    body = await request.body()
    if len(body) > MAX_BODY_SIZE:
        return Response(
            content="Payload Too Large",
            status_code=413,
            media_type="text/plain",
        )

    # 2. Bearer token authentication
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = authorization.split("Bearer ", 1)[1].strip()
    registry = get_tokens_registry()

    matched_info = None
    for reg_token, info in registry.items():
        if hmac.compare_digest(token, reg_token):
            matched_info = info
            break

    if not matched_info:
        raise HTTPException(status_code=401, detail="Unauthorized")

    principal = matched_info.get("principal", "")
    token_campaign = matched_info.get("campaign_id", "")

    # 3. Policy check
    if not check_policy(principal, "submit", "/submit"):
        raise HTTPException(status_code=403, detail="Forbidden")

    # 4. Parse schema
    try:
        data = json.loads(body.decode("utf-8"))
        req = Submit.model_validate(data)
    except (json.JSONDecodeError, ValidationError, UnicodeDecodeError):
        return JSONResponse(status_code=422, content={"error": "bad request"})

    # 5. Campaign match check (A2 probe)
    if req.campaign_id != token_campaign:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 6. Round state check
    if manager.state != RoundState.EXECUTING:
        raise HTTPException(status_code=409, detail="Conflict: Round not in EXECUTING state")

    return await execute_submit_flow(req)


# Admin routes (Loopback + token_admin only)
def verify_admin(request: Request, authorization: str | None):
    # Loopback check
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Forbidden: Admin is loopback only")

    # Token check
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    admin_token = get_admin_token()
    token = authorization.split("Bearer ", 1)[1].strip()
    if not admin_token or not hmac.compare_digest(token, admin_token):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/admin/state")
def admin_state(request: Request, authorization: str | None = Header(None)):
    verify_admin(request, authorization)
    return manager.get_info()


@app.post("/admin/transition")
def admin_transition(to: str, request: Request, authorization: str | None = Header(None)):
    verify_admin(request, authorization)
    try:
        manager.move(to)
        return manager.get_info()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/admin/load_round")
async def admin_load_round(request: Request, authorization: str | None = Header(None)):
    verify_admin(request, authorization)
    body = await request.json()
    manager.load_round(
        campaign_id=body.get("campaign_id", "c-001"),
        round_id=body.get("round_id", "r-001"),
        defense_digest=body.get("defense_digest"),
        model_digest=body.get("model_digest"),
        pub=body.get("pub"),
        temperature=body.get("temperature"),
        seed_base=body.get("seed_base"),
    )
    return manager.get_info()


@app.post("/admin/audit")
async def admin_audit(request: Request, authorization: str | None = Header(None)):
    """Controller writes events through the broker (broker is the only audit writer)."""
    verify_admin(request, authorization)
    try:
        body = await request.json()
        audit_in = AuditIn.model_validate(body)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid audit schema: {e}")
    try:
        from referee.broker.flow import call_audit as _call_audit
    except ModuleNotFoundError:
        from broker.flow import call_audit as _call_audit
    # call_audit is async so we need to await it
    result = await _call_audit(audit_in)
    return result


@app.post("/admin/submit", response_model=Receipt)
async def admin_submit(request: Request, authorization: str | None = Header(None)):
    """Controller benign stream: submit as controller principal (STAND-IN if stand_in_red)."""
    verify_admin(request, authorization)
    try:
        body = await request.json()
        req = Submit.model_validate(body)
    except ValidationError:
        raise HTTPException(status_code=422, detail="Unprocessable Entity")
    if manager.state != RoundState.EXECUTING:
        raise HTTPException(status_code=409, detail="Conflict: Round not in EXECUTING state")
    return await execute_submit_flow(req)
