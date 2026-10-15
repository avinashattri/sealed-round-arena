import hmac
import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException

from contracts.messages import FilterRequest, FilterVerdict, ReasonCode, Verdict

try:
    from loop.blue.rules import filter_input, filter_output
except ModuleNotFoundError:
    from blue.rules import filter_input, filter_output

BLUE_VERSION = int(os.environ.get("BLUE_VERSION", "1"))

app = FastAPI(title="Sealed Round Arena - Blue Defense")


def get_svc_blue_token() -> str:
    token = os.environ.get("SVC_BLUE_TOKEN")
    if token:
        return token.strip()
    for p in ["/run/secrets/svc_blue", "secrets/token_svc_blue.txt"]:
        path = Path(p)
        if path.exists():
            return path.read_text().strip()
    return "dev_svc_blue_token"


def verify_svc_blue(authorization: str | None):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    expected = get_svc_blue_token().strip()
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Forbidden: invalid blue service token")


@app.get("/health")
def health():
    return {"status": "ok", "service": "blue", "version": BLUE_VERSION}


@app.post("/filter/input", response_model=FilterVerdict)
async def api_filter_input(
    req: FilterRequest, authorization: str | None = Header(None)
) -> FilterVerdict:
    try:
        verify_svc_blue(authorization)
        return filter_input(req.text, version=BLUE_VERSION)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 -- fail closed
        return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R99)


@app.post("/filter/output", response_model=FilterVerdict)
async def api_filter_output(
    req: FilterRequest, authorization: str | None = Header(None)
) -> FilterVerdict:
    try:
        verify_svc_blue(authorization)
        return filter_output(req.text, version=BLUE_VERSION)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 -- fail closed
        return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R99)
