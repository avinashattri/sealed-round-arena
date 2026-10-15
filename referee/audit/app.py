import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request
from pydantic import ValidationError

from contracts.audit import AuditIn

try:
    from referee.audit.store import AuditStore
except ModuleNotFoundError:
    from audit.store import AuditStore

app = FastAPI(title="Sealed Round Arena - Audit Service")
store = AuditStore()


def get_svc_audit_token() -> str:
    token = os.environ.get("SVC_AUDIT_TOKEN")
    if token:
        return token.strip()
    for p in ["/run/secrets/svc_audit", "secrets/token_svc_audit.txt"]:
        path = Path(p)
        if path.exists():
            return path.read_text().strip()
    return "dev_svc_audit_token"


def verify_svc_audit(authorization: str | None = Header(None)):
    if not authorization:
        raise HTTPException(status_code=403, detail="Missing authorization header")
    token = authorization
    token = token.removeprefix("Bearer ")
    if not hmac.compare_digest(token.strip(), get_svc_audit_token().strip()):
        raise HTTPException(status_code=403, detail="Forbidden: invalid audit service token")


def verify_loopback(request: Request):
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Forbidden: loopback access only")


@app.get("/health")
def health():
    count, head_hash, _ = store.head()
    return {"status": "ok", "count": count, "head_hash": head_hash}


@app.post("/append")
async def append_entry(request: Request, authorization: str | None = Header(None)):
    verify_svc_audit(authorization)
    try:
        body = await request.json()
        audit_in = AuditIn.model_validate(body)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Invalid audit entry schema: {e}")

    entry = store.append(audit_in.model_dump())
    return entry.model_dump()


@app.post("/admin/checkpoint")
def admin_checkpoint(
    request: Request,
    round_id: str = Query(..., pattern=r"^r-[0-9]{3}$"),
):
    verify_loopback(request)
    cp = store.checkpoint(round_id)
    return cp.model_dump()


@app.get("/admin/export")
def admin_export(request: Request):
    verify_loopback(request)
    return store.export()


@app.get("/admin/pubkey")
def admin_pubkey(request: Request):
    verify_loopback(request)
    return {"verify_key_hex": store.verify_key_hex}
