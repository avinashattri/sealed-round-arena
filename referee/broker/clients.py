import os
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError

from contracts.audit import AuditIn
from contracts.messages import (
    FilterRequest,
    FilterVerdict,
    OracleRequest,
    OracleResult,
    ReasonCode,
    Verdict,
)

AUDIT_URL = os.environ.get("AUDIT_URL", "http://audit:7000")
BLUE_URL = os.environ.get("BLUE_URL", "http://blue:9000")
MODEL_URL = os.environ.get("MODEL_URL", "http://model:8080")
ORACLE_URL = os.environ.get("ORACLE_URL", "http://oracle:7100")


def read_secret(env_var: str, default_path: str, fallback_path: str) -> str:
    if env_var in os.environ:
        return os.environ[env_var].strip()
    p1 = Path(default_path)
    if p1.exists():
        return p1.read_text().strip()
    p2 = Path(fallback_path)
    if p2.exists():
        return p2.read_text().strip()
    return ""


def get_svc_audit_token() -> str:
    return read_secret("SVC_AUDIT_TOKEN", "/run/secrets/svc_audit", "secrets/token_svc_audit.txt")


async def call_audit(audit_in: AuditIn) -> dict[str, Any]:
    token = get_svc_audit_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{AUDIT_URL}/append",
                content=audit_in.model_dump_json(),
                headers=headers,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Audit log failed with status {resp.status_code}: {resp.text}")
            return resp.json()
        except (httpx.HTTPError, OSError) as e:
            raise RuntimeError(f"Audit append connection failed: {e}") from e


async def call_blue_filter(route: str, req: FilterRequest) -> FilterVerdict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BLUE_URL}{route}",
                content=req.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                return FilterVerdict.model_validate(resp.json())
            return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R99)
        except (httpx.HTTPError, ValidationError, ValueError):
            return FilterVerdict(verdict=Verdict.BLOCK, reason_code=ReasonCode.R99)


async def call_model(
    messages: list[dict[str, Any]],
    temperature: float = 0.0,
    seed: int = 1,
    max_tokens: int = 128,
    cache_prompt: bool = False,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "messages": messages,
            "temperature": temperature,
            "seed": seed,
            "max_tokens": max_tokens,
            "cache_prompt": cache_prompt,
        }
        resp = await client.post(
            f"{MODEL_URL}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Model query failed with status {resp.status_code}: {resp.text}")
        return resp.json()


async def call_oracle(req: OracleRequest) -> OracleResult:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{ORACLE_URL}/score",
                content=req.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                return OracleResult.model_validate(resp.json())
            return OracleResult(leak=False, matched=[], harm=None)
        except (httpx.HTTPError, ValidationError, ValueError):
            return OracleResult(leak=False, matched=[], harm=None)
