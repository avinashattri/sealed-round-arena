import json

import pytest
from fastapi.testclient import TestClient

from contracts.rounds import RoundState
from referee.broker.app import app
from referee.broker.state import manager

client = TestClient(app)

TEST_TOKENS = {
    "test-token-red": {"principal": "red", "campaign_id": "c-001"},
    "test-token-ctrl": {"principal": "controller", "campaign_id": "c-001"},
}


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    monkeypatch.setenv("TOKENS_JSON", json.dumps(TEST_TOKENS))
    monkeypatch.setenv("TOKEN_ADMIN", "test-token-admin")
    monkeypatch.setenv("AUDIT_URL", "http://mock-audit:7000")
    monkeypatch.setenv("BLUE_URL", "http://mock-blue:9000")
    monkeypatch.setenv("MODEL_URL", "http://mock-model:8080")
    monkeypatch.setenv("ORACLE_URL", "http://mock-oracle:7100")
    manager.state = RoundState.PROVISIONED
    manager.campaign_id = "c-001"
    manager.round_id = "r-001"


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_submit_outside_executing_raises_409():
    headers = {"Authorization": "Bearer test-token-red"}
    payload = {
        "campaign_id": "c-001",
        "round_id": "r-001",
        "challenge_id": "ch-0001",
        "payload": "test prompt",
    }
    resp = client.post("/submit", json=payload, headers=headers)
    assert resp.status_code == 409


def test_submit_bad_token_raises_401():
    manager.state = RoundState.EXECUTING
    headers = {"Authorization": "Bearer bad-token"}
    payload = {
        "campaign_id": "c-001",
        "round_id": "r-001",
        "challenge_id": "ch-0001",
        "payload": "test prompt",
    }
    resp = client.post("/submit", json=payload, headers=headers)
    assert resp.status_code == 401


def test_submit_bad_body_raises_422():
    manager.state = RoundState.EXECUTING
    headers = {"Authorization": "Bearer test-token-red"}
    # Missing required field round_id
    payload = {
        "campaign_id": "c-001",
        "challenge_id": "ch-0001",
        "payload": "test prompt",
    }
    resp = client.post("/submit", json=payload, headers=headers)
    assert resp.status_code == 422


def test_submit_extra_field_raises_422():
    manager.state = RoundState.EXECUTING
    headers = {"Authorization": "Bearer test-token-red"}
    payload = {
        "campaign_id": "c-001",
        "round_id": "r-001",
        "challenge_id": "ch-0001",
        "payload": "test prompt",
        "extra_unknown": "disallowed",
    }
    resp = client.post("/submit", json=payload, headers=headers)
    assert resp.status_code == 422


def test_submit_17kb_payload_raises_413():
    manager.state = RoundState.EXECUTING
    headers = {"Authorization": "Bearer test-token-red"}
    big_body = "x" * (17 * 1024)
    resp = client.post("/submit", content=big_body, headers=headers)
    assert resp.status_code == 413


def test_probe_a2_campaign_mismatch_raises_403():
    manager.state = RoundState.EXECUTING
    headers = {"Authorization": "Bearer test-token-red"}
    # Token is for c-001, submitting c-002
    payload = {
        "campaign_id": "c-002",
        "round_id": "r-001",
        "challenge_id": "ch-0001",
        "payload": "test prompt",
    }
    resp = client.post("/submit", json=payload, headers=headers)
    assert resp.status_code == 403


def test_admin_state_and_transition():
    admin_headers = {"Authorization": "Bearer test-token-admin"}
    resp = client.get("/admin/state", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["state"] == "PROVISIONED"

    resp2 = client.post("/admin/transition?to=COMMITTED", headers=admin_headers)
    assert resp2.status_code == 200
    assert resp2.json()["state"] == "COMMITTED"


def test_admin_bad_token_raises_401():
    headers = {"Authorization": "Bearer wrong-admin"}
    resp = client.get("/admin/state", headers=headers)
    assert resp.status_code == 401


def test_admin_non_loopback_raises_403():
    # Simulate client from foreign IP
    headers = {"Authorization": "Bearer test-token-admin"}
    foreign_client = TestClient(app, client=("192.168.1.50", 12345))
    resp = foreign_client.get("/admin/state", headers=headers)
    assert resp.status_code == 403


def test_model_cache_off_by_default(monkeypatch):
    """cache_prompt must be False when MODEL_CACHE is not set."""
    monkeypatch.delenv("MODEL_CACHE", raising=False)

    captured = {}

    async def mock_call_model(messages, temperature, seed, max_tokens, cache_prompt=False):
        captured["cache_prompt"] = cache_prompt
        return {"choices": [{"message": {"content": "ok", "tool_calls": []}}]}

    import referee.broker.flow as flow_mod

    monkeypatch.setattr(flow_mod, "call_model", mock_call_model)
    monkeypatch.setattr(flow_mod, "call_blue_filter", lambda *_a, **_kw: None)
    monkeypatch.setattr(flow_mod, "call_oracle", lambda *_a, **_kw: None)
    monkeypatch.setattr(flow_mod, "call_audit", lambda *_a, **_kw: None)

    from contracts.messages import FilterVerdict, OracleResult, ReasonCode, Verdict

    async def mock_blue(*_a, **_kw):
        return FilterVerdict(verdict=Verdict.PASS, reason_code=ReasonCode.R00)

    async def mock_oracle(*_a, **_kw):
        return OracleResult(leak=False, matched=[])

    async def mock_audit(*_a, **_kw):
        return {}

    monkeypatch.setattr(flow_mod, "call_blue_filter", mock_blue)
    monkeypatch.setattr(flow_mod, "call_oracle", mock_oracle)
    monkeypatch.setattr(flow_mod, "call_audit", mock_audit)

    from contracts.messages import Submit
    from contracts.rounds import RoundState
    from referee.broker.state import manager

    manager.state = RoundState.EXECUTING
    manager.round_pub_hex = None  # no sealing in this unit test

    import asyncio

    req = Submit(campaign_id="c-001", round_id="r-001", challenge_id="ch-0001", payload="hello")
    asyncio.run(flow_mod.execute_submit_flow(req))

    assert captured.get("cache_prompt") is False, "MODEL_CACHE=off must yield cache_prompt=False"


def test_model_cache_on_when_env_set(monkeypatch):
    """cache_prompt must be True when MODEL_CACHE=on."""
    monkeypatch.setenv("MODEL_CACHE", "on")

    captured = {}

    async def mock_call_model(messages, temperature, seed, max_tokens, cache_prompt=False):
        captured["cache_prompt"] = cache_prompt
        return {"choices": [{"message": {"content": "ok", "tool_calls": []}}]}

    import referee.broker.flow as flow_mod

    monkeypatch.setattr(flow_mod, "call_model", mock_call_model)

    from contracts.messages import FilterVerdict, OracleResult, ReasonCode, Verdict

    async def mock_blue(*_a, **_kw):
        return FilterVerdict(verdict=Verdict.PASS, reason_code=ReasonCode.R00)

    async def mock_oracle(*_a, **_kw):
        return OracleResult(leak=False, matched=[])

    async def mock_audit(*_a, **_kw):
        return {}

    monkeypatch.setattr(flow_mod, "call_blue_filter", mock_blue)
    monkeypatch.setattr(flow_mod, "call_oracle", mock_oracle)
    monkeypatch.setattr(flow_mod, "call_audit", mock_audit)

    from contracts.messages import Submit
    from contracts.rounds import RoundState
    from referee.broker.state import manager

    manager.state = RoundState.EXECUTING
    manager.round_pub_hex = None

    import asyncio

    req = Submit(campaign_id="c-001", round_id="r-001", challenge_id="ch-0001", payload="hello")
    asyncio.run(flow_mod.execute_submit_flow(req))

    assert captured.get("cache_prompt") is True, "MODEL_CACHE=on must yield cache_prompt=True"


def test_flow_audit_computes_sha256_and_seals(monkeypatch, tmp_path):
    """flow.audit computes sha256, seals payload to disk, sets sealed_ref."""
    import asyncio
    import hashlib

    import referee.broker.flow as flow_mod
    from contracts.audit import Actor, Event
    from contracts.crypto.seal import new_round_keys, unseal
    from referee.broker.state import manager

    priv_hex, pub_hex = new_round_keys()
    manager.round_pub_hex = pub_hex
    manager.round_id = "r-001"
    manager.campaign_id = "c-001"

    monkeypatch.setenv("SEALED_DIR", str(tmp_path / "sealed"))

    captured_audit = []

    async def mock_call_audit(audit_in):
        captured_audit.append(audit_in)
        return {"status": "ok"}

    monkeypatch.setattr(flow_mod, "call_audit", mock_call_audit)

    payload = "secret attack test"
    expected_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    asyncio.run(
        flow_mod.audit(Event.REQUEST_RECEIVED, "ch-0001", content=payload, actor=Actor.BROKER)
    )

    assert len(captured_audit) == 1
    entry = captured_audit[0]
    assert entry.content_hash == expected_hash
    assert entry.sealed_ref is not None
    assert "ch-0001.request_received.1.bin" in entry.sealed_ref

    # Verify unsealing recovered the exact plaintext
    from pathlib import Path

    sealed_data = Path(entry.sealed_ref).read_bytes()
    recovered = unseal(priv_hex, sealed_data)
    assert recovered == payload.encode()


def test_flow_audit_failure_raises(monkeypatch):
    """flow.audit raises when underlying call fails."""
    import asyncio

    import pytest

    import referee.broker.flow as flow_mod
    from contracts.audit import Actor, Event
    from referee.broker.state import manager

    manager.round_pub_hex = "invalid_hex"

    with pytest.raises(ValueError):
        asyncio.run(
            flow_mod.audit(Event.REQUEST_RECEIVED, "ch-0001", content="test", actor=Actor.BROKER)
        )
