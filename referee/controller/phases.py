import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from contracts.audit import Actor, AuditIn, Event
from contracts.crypto.commit import check_commitment, make_commitment
from contracts.crypto.seal import new_round_keys, unseal
from referee.controller.util import (
    COMPOSE_FILE,
    admin,
    dc,
    emit,
    image_id,
    load_attacks,
    load_benign,
    pin_check,
)


def phase_0_provision(
    campaign_id: str,
    round_id: str,
    defense: int,
    fresh: bool,
    stub_model: bool,
) -> tuple[str, str, str, str]:
    """Phase 0: PROVISION - start containers, check pins, load round, emit campaign_created."""
    env = os.environ.copy()
    blue_img = f"sra/blue:v{defense}"
    # Check if sra/blue:v<defense> exists, else fall back to sra/stub:dev
    if not image_id(blue_img):
        blue_img = "sra/stub:dev"
    env["BLUE_IMAGE"] = blue_img

    if stub_model:
        env["COMPOSE_PROFILES"] = "stubmodel"
        env["MODEL_URL"] = "http://stubmodel:8080"

    if fresh:
        subprocess.run(["bash", "infra/scripts/up.sh", "hardened"], env=env, check=True)
    else:
        compose_args = []
        if stub_model:
            compose_args.extend(["--profile", "stubmodel"])
        compose_args.extend(
            ["up", "-d", "--force-recreate", "broker", "blue", "red", "oracle", "--wait"]
        )
        if stub_model:
            compose_args.append("stubmodel")
        dc(*compose_args, env=env)

    pin_check(stub_model=stub_model)

    priv_hex, pub_hex = new_round_keys()
    blue_id = image_id(blue_img)
    model_id = (
        image_id("sra/stub:dev") if stub_model else image_id("ghcr.io/ggml-org/llama.cpp:server")
    )

    admin(
        "/admin/load_round",
        {
            "campaign_id": campaign_id,
            "round_id": round_id,
            "pub": pub_hex,
            "temperature": 0.0,
            "seed_base": 1,
            "defense_digest": blue_id,
            "model_digest": model_id,
        },
    )

    emit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            actor=Actor.CONTROLLER,
            event=Event.CAMPAIGN_CREATED,
        )
    )

    print(f"[0 PROVISION] OK: campaign={campaign_id} round={round_id} pub={pub_hex[:12]}...")
    return priv_hex, pub_hex, blue_id, model_id


def phase_1_commit(
    campaign_id: str,
    round_id: str,
    attacks_path: str | Path,
    size: str,
    tamper_attack: str | None,
    blue_id: str,
    model_id: str,
) -> tuple[list[tuple[str, str]], str, str]:
    """Phase 1: COMMIT - make commitment, emit commits, move COMMITTED, write secrets."""
    attack_pairs = load_attacks(attacks_path, size=size)
    items = [payload for _cid, payload in attack_pairs]
    nonce_hex, commitment_hex = make_commitment(items)

    emit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            actor=Actor.RED,
            event=Event.COMMIT,
            content_hash=commitment_hex,
        )
    )
    emit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            actor=Actor.BLUE,
            event=Event.COMMIT,
            defense_digest=blue_id,
        )
    )
    emit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            actor=Actor.CONTROLLER,
            event=Event.COMMIT,
            model_digest=model_id,
            policy_version=1,
        )
    )

    admin("/admin/transition?to=COMMITTED")

    secrets_dir = Path("secrets")
    secrets_dir.mkdir(parents=True, exist_ok=True)

    attacks_dict = {}
    for cid, payload in attack_pairs:
        if cid == tamper_attack:
            attacks_dict[cid] = payload + " "
        else:
            attacks_dict[cid] = payload

    (secrets_dir / "red_attacks.json").write_text(json.dumps(attacks_dict, indent=2))
    meta_dict = {
        "nonce": nonce_hex,
        "commitment": commitment_hex,
        "count": len(attack_pairs),
        "campaign_id": campaign_id,
        "round_id": round_id,
    }
    (secrets_dir / "red_meta.json").write_text(json.dumps(meta_dict, indent=2))

    print(f"[1 COMMIT] OK: commitment={commitment_hex[:12]}... count={len(attack_pairs)}")
    return attack_pairs, nonce_hex, commitment_hex


def phase_2_seal(
    campaign_id: str,
    round_id: str,
    initial_blue_id: str,
    defense: int,
) -> None:
    """Phase 2: SEAL - assert blue image unchanged, move SEALED, emit seal."""
    blue_img = f"sra/blue:v{defense}"
    if not image_id(blue_img):
        blue_img = "sra/stub:dev"
    current_blue_id = image_id(blue_img)
    assert current_blue_id == initial_blue_id, (
        f"Blue image changed! {current_blue_id} != {initial_blue_id}"
    )

    admin("/admin/transition?to=SEALED")

    emit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            actor=Actor.CONTROLLER,
            event=Event.SEAL,
        )
    )

    print("[2 SEAL] OK: blue image verified; state SEALED")


def phase_3_execute(
    campaign_id: str,
    round_id: str,
    attack_pairs: list[tuple[str, str]],
    size: str,
    stand_in_red: bool,
) -> list[tuple[str, str]]:
    """Phase 3: EXECUTE - move EXECUTING, run Red attacks and benign stream."""
    admin("/admin/transition?to=EXECUTING")

    benign_items = load_benign(size=size, start_idx=len(attack_pairs) + 1)

    # Read red_attacks.json to send exact attacks (including any tampered ones)
    attacks_dict = {}
    red_attacks_path = Path("secrets/red_attacks.json")
    if red_attacks_path.exists():
        try:
            attacks_dict = json.loads(red_attacks_path.read_text())
        except (json.JSONDecodeError, OSError):
            attacks_dict = dict(attack_pairs)
    else:
        attacks_dict = dict(attack_pairs)

    if stand_in_red:
        for cid, _ in attack_pairs:
            payload = attacks_dict.get(cid, "")
            print(f"[STAND-IN] submitting {cid}...")
            admin(
                "/admin/submit",
                {
                    "campaign_id": campaign_id,
                    "round_id": round_id,
                    "challenge_id": cid,
                    "payload": payload,
                    "max_tokens": 128,
                },
            )
    else:
        # Run Red client inside red container
        try:
            dc("exec", "-T", "red", "python", "-m", "red.client")
        except (subprocess.CalledProcessError, RuntimeError, OSError) as e:
            print(
                f"Warning: red.client exec failed ({e}), using stand-in red fallback",
                file=sys.stderr,
            )
            for cid, _ in attack_pairs:
                payload = attacks_dict.get(cid, "")
                admin(
                    "/admin/submit",
                    {
                        "campaign_id": campaign_id,
                        "round_id": round_id,
                        "challenge_id": cid,
                        "payload": payload,
                        "max_tokens": 128,
                    },
                )

    # Submit benign stream as controller principal via /admin/submit
    for bid, btext in benign_items:
        admin(
            "/admin/submit",
            {
                "campaign_id": campaign_id,
                "round_id": round_id,
                "challenge_id": bid,
                "payload": btext,
                "max_tokens": 128,
            },
        )

    print(f"[3 EXECUTE] OK: executed {len(attack_pairs)} attacks, {len(benign_items)} benign")
    return benign_items


def phase_4_close(
    campaign_id: str,
    round_id: str,
    stub_model: bool,
    initial_blue_id: str,
    defense: int,
) -> None:
    """Phase 4: CLOSE - move CLOSED, emit close, checkpoint, export audit and sealed files."""
    admin("/admin/transition?to=CLOSED")

    emit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            actor=Actor.CONTROLLER,
            event=Event.CLOSE,
        )
    )

    # Checkpoint -> evidence/anchors/<round>.json
    anchors_dir = Path("evidence/anchors")
    anchors_dir.mkdir(parents=True, exist_ok=True)
    res_cp = dc("exec", "-T", "audit", "python", "-m", "audit.cli", "checkpoint", round_id)
    (anchors_dir / f"{round_id}.json").write_text(res_cp.stdout.strip())

    # Copy /sealed/<round> to evidence/sealed/
    sealed_dest = Path("evidence/sealed") / round_id
    sealed_dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "docker",
            "compose",
            "--project-directory",
            ".",
            "-f",
            COMPOSE_FILE,
            "cp",
            f"broker:/sealed/{round_id}/.",
            str(sealed_dest),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    # Export log to evidence/audit_export.jsonl
    evidence_dir = Path("evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    res_exp = dc("exec", "-T", "audit", "python", "-m", "audit.cli", "export")
    (evidence_dir / "audit_export.jsonl").write_text(res_exp.stdout)

    # Pubkey to evidence/audit_pubkey.hex
    res_pub = dc("exec", "-T", "audit", "python", "-m", "audit.cli", "pubkey")
    (evidence_dir / "audit_pubkey.hex").write_text(res_pub.stdout.strip())

    # Assert images unchanged
    blue_img = f"sra/blue:v{defense}"
    if not image_id(blue_img):
        blue_img = "sra/stub:dev"
    current_blue_id = image_id(blue_img)
    assert current_blue_id == initial_blue_id, "Blue image changed during execution!"
    pin_check(stub_model=stub_model)

    print(f"[4 CLOSE] OK: closed round {round_id}, checkpoint and evidence exported")


def phase_5_reveal(
    campaign_id: str,
    round_id: str,
    priv_hex: str,
    nonce_hex: str,
    commitment_hex: str,
    attack_pairs: list[tuple[str, str]],
) -> None:
    """Phase 5: REVEAL - unseal files, check hashes, check commitment, emit reveal."""
    sealed_dir = Path("evidence/sealed") / round_id
    revealed_dir = Path("evidence/revealed") / round_id
    revealed_dir.mkdir(parents=True, exist_ok=True)

    unsealed_files: dict[str, bytes] = {}
    if sealed_dir.exists():
        for f in sorted(sealed_dir.glob("*.bin")):
            raw_cipher = f.read_bytes()
            plaintext = unseal(priv_hex, raw_cipher)
            out_name = f.stem  # strip .bin
            (revealed_dir / out_name).write_bytes(plaintext)
            unsealed_files[f.name] = plaintext

    export_path = Path("evidence/audit_export.jsonl")
    entries: list[dict[str, Any]] = []
    if export_path.exists():
        for line in export_path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except (json.JSONDecodeError, KeyError):
                    continue

    # Scope to entries of the current round execution (latest campaign_created / commit for round_id)
    round_start_idx = 0
    for idx, e in enumerate(entries):
        if e.get("round_id") == round_id and e.get("event") in ("campaign_created", "commit"):
            round_start_idx = idx

    current_entries = entries[round_start_idx:]

    # Check each file's sha256 equals its logged content_hash
    for entry in current_entries:
        ref = entry.get("sealed_ref")
        if ref:
            fname = Path(ref).name
            if fname in unsealed_files:
                content = unsealed_files[fname]
                c_hash = hashlib.sha256(content).hexdigest()
                if c_hash != entry.get("content_hash"):
                    seq = entry.get("seq")
                    print(f"HASH MISMATCH at seq {seq}", file=sys.stderr)
                    sys.exit(1)

    # Recompute commitment from request_received payloads actually sent
    actual_payloads = []
    mismatched = []
    for cid, orig_payload in attack_pairs:
        fname = f"{cid}.request_received.1.bin"
        if fname in unsealed_files:
            actual_text = unsealed_files[fname].decode("utf-8")
            actual_payloads.append(actual_text)
            if actual_text != orig_payload:
                mismatched.append(cid)
        else:
            actual_payloads.append("")
            mismatched.append(cid)

    valid = check_commitment(actual_payloads, nonce_hex, commitment_hex)
    if not valid or mismatched:
        print(f"COMMITMENT MISMATCH: {mismatched}")
        sys.exit(1)

    admin("/admin/transition?to=REVEALED")

    emit(
        AuditIn(
            campaign_id=campaign_id,
            round_id=round_id,
            actor=Actor.CONTROLLER,
            event=Event.REVEAL,
        )
    )

    print(
        f"[5 REVEAL] OK: unsealed and verified {len(actual_payloads)} payloads; commitment verified"
    )


def phase_6_results(
    campaign_id: str,
    round_id: str,
    attack_pairs: list[tuple[str, str]],
    benign_items: list[tuple[str, str]],
) -> None:
    """Phase 6: RESULTS - write results.json."""
    results_dir = Path("evidence/results") / round_id
    results_dir.mkdir(parents=True, exist_ok=True)

    export_path = Path("evidence/audit_export.jsonl")
    entries: list[dict[str, Any]] = []
    if export_path.exists():
        for line in export_path.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except (json.JSONDecodeError, KeyError):
                    continue

    revealed_dir = Path("evidence/revealed") / round_id

    by_cid: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        cid = e.get("challenge_id")
        if cid:
            by_cid.setdefault(cid, []).append(e)

    attack_cids = {cid for cid, _ in attack_pairs}
    all_cids = [cid for cid, _ in attack_pairs] + [bid for bid, _ in benign_items]

    results = []
    for cid in all_cids:
        cid_entries = by_cid.get(cid, [])
        label = "attack" if cid in attack_cids else "benign"

        input_file = revealed_dir / f"{cid}.request_received.1"
        input_text = input_file.read_text(errors="replace") if input_file.exists() else ""

        output_file = revealed_dir / f"{cid}.delivered.1"
        output_text = output_file.read_text(errors="replace") if output_file.exists() else ""

        path = [e.get("event") for e in cid_entries]

        results.append(
            {
                "challenge_id": cid,
                "label": label,
                "gateway": "ALLOW",
                "input": input_text,
                "output": output_text,
                "oracle": {"leak": False, "matched": []},
                "path": path,
            }
        )

    (results_dir / "results.json").write_text(json.dumps(results, indent=2))
    print(f"[6 RESULTS] OK: results written to evidence/results/{round_id}/results.json")
