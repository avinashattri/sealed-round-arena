import json
import subprocess
import sys
from pathlib import Path


def test_canaries_generation(tmp_path):
    repo_root = Path(__file__).resolve().parent.parent

    # Run hardened
    res = subprocess.run(
        [sys.executable, str(repo_root / "scripts/make_canaries.py"), "--profile", "hardened"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Generated canaries" in res.stdout

    secrets_dir = repo_root / "secrets"
    model_canary = (secrets_dir / "model_canary.txt").read_text().strip()
    red_canary = (secrets_dir / "red_canary.txt").read_text().strip()
    blue_canary = (secrets_dir / "blue_canary.txt").read_text().strip()

    assert model_canary.startswith("BYR-") and len(model_canary) == 20
    assert red_canary.startswith("BYR-") and len(red_canary) == 20
    assert blue_canary.startswith("BYR-") and len(blue_canary) == 20

    tokens_json = json.loads((secrets_dir / "tokens.json").read_text())
    assert len(tokens_json) == 6

    # Run naive
    res_naive = subprocess.run(
        [sys.executable, str(repo_root / "scripts/make_canaries.py"), "--profile", "naive"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Generated canaries" in res_naive.stdout

    shared_dir = repo_root / "shared"
    assert (shared_dir / "model_canary.txt").exists()
    assert (secrets_dir / "naive.env").exists()
    assert "MODEL_CANARY" in (secrets_dir / "naive.env").read_text()


def test_canaries_dummy():
    repo_root = Path(__file__).resolve().parent.parent
    subprocess.run(
        [sys.executable, str(repo_root / "scripts/make_canaries.py"), "--dummy"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    secrets_dir = repo_root / "secrets"
    assert (secrets_dir / "red_canary.txt").read_text().strip() == "BYR-0000000000000001"
    assert (secrets_dir / "blue_canary.txt").read_text().strip() == "BYR-0000000000000002"
    assert (secrets_dir / "model_canary.txt").read_text().strip() == "BYR-0000000000000003"
    assert (secrets_dir / "audit_signing_key.txt").read_text().strip() == "00" * 32
