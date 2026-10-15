import sqlite3

import pytest
from fastapi.testclient import TestClient

from contracts.audit import Actor, Event
from contracts.crypto.sign import verify_checkpoint, verify_entry_hash
from referee.audit.app import app, store


@pytest.fixture(autouse=True)
def clean_store(tmp_path, monkeypatch):
    db_file = tmp_path / "test_audit.db"
    key_hex = "02" * 32
    monkeypatch.setenv("AUDIT_DB_PATH", str(db_file))
    monkeypatch.setenv("AUDIT_SIGNING_KEY", key_hex)
    monkeypatch.setenv("SVC_AUDIT_TOKEN", "valid_svc_token")

    # Reinitialize store
    store.db_path = str(db_file)
    store.signing_key_bytes = bytes.fromhex(key_hex)
    from nacl.signing import SigningKey

    store.signing_key = SigningKey(store.signing_key_bytes)
    store.verify_key_hex = store.signing_key.verify_key.encode().hex()
    store._init_db()


def test_1_append_100_events_and_export_in_order():
    client = TestClient(app)
    headers = {"Authorization": "Bearer valid_svc_token"}

    for i in range(1, 101):
        payload = {
            "campaign_id": "c-001",
            "round_id": "r-001",
            "challenge_id": f"ch-{i:04d}",
            "actor": "broker",
            "event": "request_received",
            "content_hash": "a" * 64,
        }
        res = client.post("/append", json=payload, headers=headers)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["seq"] == i

    # Export via admin
    export_res = client.get("/admin/export")
    assert export_res.status_code == 200
    entries = export_res.json()
    assert len(entries) == 100

    # Verify seq, hash chaining and signatures
    prev = "0" * 64
    vk_bytes = bytes.fromhex(store.verify_key_hex)
    for idx, e in enumerate(entries, start=1):
        assert e["seq"] == idx
        assert e["prev_hash"] == prev
        assert verify_entry_hash(vk_bytes, e["entry_hash"], e["sig"]) is True
        prev = e["entry_hash"]


def test_2_sqlite_no_update_no_delete_triggers():
    # Insert an entry first
    store.append(
        {
            "campaign_id": "c-001",
            "round_id": "r-001",
            "actor": Actor.BROKER,
            "event": Event.SEAL,
        }
    )

    conn = sqlite3.connect(store.db_path)
    # Test UPDATE trigger
    with pytest.raises(sqlite3.DatabaseError) as exc_update:
        conn.execute("UPDATE entries SET body = 'tampered' WHERE seq = 1")
    assert "append-only" in str(exc_update.value)

    # Test DELETE trigger
    with pytest.raises(sqlite3.DatabaseError) as exc_delete:
        conn.execute("DELETE FROM entries WHERE seq = 1")
    assert "append-only" in str(exc_delete.value)
    conn.close()


def test_3_a5_zone_tokens_get_403():
    client = TestClient(app)
    payload = {
        "campaign_id": "c-001",
        "round_id": "r-001",
        "actor": "broker",
        "event": "seal",
    }

    # Red/blue/model or invalid tokens
    for bad_token in ["token_red_xyz", "token_blue_xyz", "token_model_xyz", "invalid"]:
        res = client.post("/append", json=payload, headers={"Authorization": f"Bearer {bad_token}"})
        assert res.status_code == 403, f"Expected 403 for {bad_token}, got {res.status_code}"

    # Missing token
    res = client.post("/append", json=payload)
    assert res.status_code == 403


def test_4_checkpoint_valid():
    client = TestClient(app)
    headers = {"Authorization": "Bearer valid_svc_token"}

    for i in range(1, 4):
        client.post(
            "/append",
            json={
                "campaign_id": "c-001",
                "round_id": "r-001",
                "actor": "broker",
                "event": "seal",
            },
            headers=headers,
        )

    res = client.post("/admin/checkpoint?round_id=r-001")
    assert res.status_code == 200
    cp = res.json()
    assert cp["round_id"] == "r-001"
    assert cp["count"] == 3

    vk_bytes = bytes.fromhex(store.verify_key_hex)
    assert (
        verify_checkpoint(vk_bytes, cp["round_id"], cp["count"], cp["head_hash"], cp["sig"]) is True
    )
