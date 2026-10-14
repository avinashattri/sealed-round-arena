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
