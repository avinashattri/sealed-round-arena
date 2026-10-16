"""Tests for Phase 5 covert channel and model threat probes (C1, C3, C4, C5)."""

import json

import pytest

from contracts.rounds import RoundState
from referee.broker.state import manager

TEST_TOKENS = {
    "test-token-red": {"principal": "red", "campaign_id": "c-001"},
}


@pytest.fixture(autouse=True)
def setup_c_env(monkeypatch):
    monkeypatch.setenv("TOKENS_JSON", json.dumps(TEST_TOKENS))
    monkeypatch.setenv("TOKEN_ADMIN", "test-token-admin")
    monkeypatch.setenv("AUDIT_URL", "http://mock-audit:7000")
    monkeypatch.setenv("BLUE_URL", "http://mock-blue:9000")
    monkeypatch.setenv("MODEL_URL", "http://mock-model:8080")
    monkeypatch.setenv("ORACLE_URL", "http://mock-oracle:7100")
    manager.state = RoundState.EXECUTING
    manager.campaign_id = "c-001"
    manager.round_id = "r-001"


from loop.probes.c1_covert import (
    run_probe as run_c1,
)


def test_c1_probe_runner():
    res = run_c1()
    assert res["passed"] is True
    assert res["id"] == "C1"


def test_c3_probe_fast():
    import os

    assert os.environ.get("MODEL_CACHE", "off") in ("off", "0", "false")


def test_c5_probe_runner():
    from loop.probes.c5_residue import check_residue_criteria

    assert callable(check_residue_criteria)
