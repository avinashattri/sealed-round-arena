import hashlib
import json

import pytest

from contracts.crypto.commit import make_commitment
from contracts.crypto.seal import new_round_keys, seal
from referee.controller.phases import phase_1_commit, phase_5_reveal, phase_6_results
from referee.controller.util import load_attacks, load_benign


def test_load_attacks_sizes(tmp_path):
    attacks_file = tmp_path / "attacks.json"
    attacks_file.write_text(json.dumps({"a1": "attack 1", "a2": "attack 2"}))

    mini = load_attacks(attacks_file, size="mini")
    assert len(mini) == 3
    assert mini[0][0] == "ch-0001"
    assert mini[1][0] == "ch-0002"
    assert mini[2][0] == "ch-0003"

    demo = load_attacks(attacks_file, size="demo")
    assert len(demo) == 4  # 2 items * 2 repeats

    full = load_attacks(attacks_file, size="full")
    assert len(full) == 12  # 2 items * 6 repeats


def test_load_benign_sizes():
    mini = load_benign(start_idx=4, size="mini")
    assert len(mini) == 3
    assert mini[0][0] == "ch-0004"

    demo = load_benign("demo")
    assert len(demo) == 40

    full = load_benign("full")
    assert len(full) == 120


def test_phase_1_commit_and_tamper(monkeypatch, tmp_path):
    # Mock admin and emit
    emitted = []
    admin_calls = []

    def mock_admin(route, obj=None):
        admin_calls.append((route, obj))
        return {"status": "ok"}

    def mock_emit(entry):
        emitted.append(entry)
        return {"status": "ok"}

    monkeypatch.setattr("referee.controller.phases.admin", mock_admin)
    monkeypatch.setattr("referee.controller.phases.emit", mock_emit)
    monkeypatch.chdir(tmp_path)

    attacks_file = tmp_path / "attacks.json"
    attacks_file.write_text(json.dumps({"a1": "alpha", "a2": "beta", "a3": "gamma"}))

    attack_pairs, nonce_hex, commitment_hex = phase_1_commit(
        campaign_id="c-001",
        round_id="r-001",
        attacks_path=attacks_file,
        size="mini",
        tamper_attack="ch-0003",
        blue_id="sha256:blue",
        model_id="sha256:model",
    )

    assert len(attack_pairs) == 3
    assert len(commitment_hex) == 64

    # Verify secrets files written
    red_attacks = json.loads((tmp_path / "secrets" / "red_attacks.json").read_text())
    assert red_attacks["ch-0001"] == "alpha"
    assert red_attacks["ch-0002"] == "beta"
    assert red_attacks["ch-0003"] == "gamma "  # Tampered with trailing space

    red_meta = json.loads((tmp_path / "secrets" / "red_meta.json").read_text())
    assert red_meta["nonce"] == nonce_hex
    assert red_meta["commitment"] == commitment_hex


def test_phase_5_reveal_success(monkeypatch, tmp_path):
    emitted = []
    admin_calls = []

    monkeypatch.setattr("referee.controller.phases.admin", lambda r, o=None: admin_calls.append(r))
    monkeypatch.setattr("referee.controller.phases.emit", lambda e: emitted.append(e))
    monkeypatch.chdir(tmp_path)

    priv_hex, pub_hex = new_round_keys()
    attack_pairs = [("ch-0001", "alpha"), ("ch-0002", "beta"), ("ch-0003", "gamma")]
    nonce_hex, commitment_hex = make_commitment([p for _, p in attack_pairs])

    # Create sealed files and audit export
    round_id = "r-001"
    sealed_dir = tmp_path / "evidence" / "sealed" / round_id
    sealed_dir.mkdir(parents=True)

    audit_entries = []
    for seq, (cid, payload) in enumerate(attack_pairs, start=1):
        cipher = seal(pub_hex, payload.encode("utf-8"))
        fname = f"{cid}.request_received.1.bin"
        (sealed_dir / fname).write_bytes(cipher)

        c_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        audit_entries.append(
            {
                "seq": seq,
                "challenge_id": cid,
                "event": "request_received",
                "content_hash": c_hash,
                "sealed_ref": f"/sealed/{round_id}/{fname}",
            }
        )

    (tmp_path / "evidence" / "audit_export.jsonl").write_text(
        "\n".join(json.dumps(e) for e in audit_entries)
    )

    # Phase 5 reveal should succeed
    phase_5_reveal(
        campaign_id="c-001",
        round_id=round_id,
        priv_hex=priv_hex,
        nonce_hex=nonce_hex,
        commitment_hex=commitment_hex,
        attack_pairs=attack_pairs,
    )

    # Check unsealed files exist in evidence/revealed/<round_id>/
    rev_dir = tmp_path / "evidence" / "revealed" / round_id
    assert (rev_dir / "ch-0001.request_received.1").read_text() == "alpha"
    assert (rev_dir / "ch-0002.request_received.1").read_text() == "beta"
    assert (rev_dir / "ch-0003.request_received.1").read_text() == "gamma"


def test_phase_5_reveal_detects_tamper(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    priv_hex, pub_hex = new_round_keys()
    attack_pairs = [("ch-0001", "alpha"), ("ch-0002", "beta"), ("ch-0003", "gamma")]
    nonce_hex, commitment_hex = make_commitment([p for _, p in attack_pairs])

    round_id = "r-001"
    sealed_dir = tmp_path / "evidence" / "sealed" / round_id
    sealed_dir.mkdir(parents=True)

    # ch-0003 payload is tampered in sealed file
    audit_entries = []
    for seq, (cid, payload) in enumerate(attack_pairs, start=1):
        sent_payload = payload + " " if cid == "ch-0003" else payload
        cipher = seal(pub_hex, sent_payload.encode("utf-8"))
        fname = f"{cid}.request_received.1.bin"
        (sealed_dir / fname).write_bytes(cipher)

        c_hash = hashlib.sha256(sent_payload.encode("utf-8")).hexdigest()
        audit_entries.append(
            {
                "seq": seq,
                "challenge_id": cid,
                "event": "request_received",
                "content_hash": c_hash,
                "sealed_ref": f"/sealed/{round_id}/{fname}",
            }
        )

    (tmp_path / "evidence" / "audit_export.jsonl").write_text(
        "\n".join(json.dumps(e) for e in audit_entries)
    )

    with pytest.raises(SystemExit):
        phase_5_reveal(
            campaign_id="c-001",
            round_id=round_id,
            priv_hex=priv_hex,
            nonce_hex=nonce_hex,
            commitment_hex=commitment_hex,
            attack_pairs=attack_pairs,
        )

    captured = capsys.readouterr()
    assert "COMMITMENT MISMATCH: ['ch-0003']" in captured.out


def test_phase_6_results_generation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    round_id = "r-001"

    rev_dir = tmp_path / "evidence" / "revealed" / round_id
    rev_dir.mkdir(parents=True)
    (rev_dir / "ch-0001.request_received.1").write_text("attack alpha")
    (rev_dir / "b-001.request_received.1").write_text("benign text")

    audit_entries = [
        {"challenge_id": "ch-0001", "event": "request_received"},
        {"challenge_id": "ch-0001", "event": "gateway_decision"},
        {"challenge_id": "ch-0001", "event": "model_response"},
        {"challenge_id": "b-001", "event": "request_received"},
        {"challenge_id": "b-001", "event": "gateway_decision"},
    ]
    (tmp_path / "evidence" / "audit_export.jsonl").write_text(
        "\n".join(json.dumps(e) for e in audit_entries)
    )

    phase_6_results(
        campaign_id="c-001",
        round_id=round_id,
        attack_pairs=[("ch-0001", "attack alpha")],
        benign_items=[("b-001", "benign text")],
    )

    res_file = tmp_path / "evidence" / "results" / round_id / "results.json"
    assert res_file.exists()
    results = json.loads(res_file.read_text())
    assert len(results) == 2
    assert results[0]["challenge_id"] == "ch-0001"
    assert results[0]["label"] == "attack"
    assert results[1]["challenge_id"] == "b-001"
    assert results[1]["label"] == "benign"


def test_pin_check_aborts_on_mismatch(tmp_path, monkeypatch, capsys):
    from referee.controller.util import pin_check

    monkeypatch.chdir(tmp_path)
    locks_dir = tmp_path / "locks"
    locks_dir.mkdir()
    images_lock = locks_dir / "images.lock.json"
    images_lock.write_text(json.dumps({"sra/stub:dev": "sha256:wrong_digest"}))

    # Mock pin.py
    infra_scripts = tmp_path / "infra" / "scripts"
    infra_scripts.mkdir(parents=True)
    pin_script = infra_scripts / "pin.py"
    pin_script.write_text("""import sys
print("IMAGE MISMATCH: sra/stub:dev expected sha256:wrong_digest, got actual", file=sys.stderr)
sys.exit(1)
""")

    with pytest.raises(SystemExit):
        pin_check(stub_model=True)

    captured = capsys.readouterr()
    assert "IMAGE MISMATCH" in captured.err
