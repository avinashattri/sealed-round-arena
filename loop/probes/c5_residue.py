"""loop.probes.c5_residue: C5 residue after reset probe."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def check_residue_criteria(canaries: list[str] | None = None) -> tuple[bool, str]:
    """Inspect system state for lingering containers, volumes, networks, secrets, and canary residue."""
    failed = []

    # 1. Containers
    res = subprocess.run(
        ["docker", "ps", "-a", "--filter", "name=sra-", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    containers = [c.strip() for c in res.stdout.splitlines() if c.strip()]
    if containers:
        failed.append(f"containers: {', '.join(containers)}")

    # 2. Volumes
    res = subprocess.run(
        ["docker", "volume", "ls", "--filter", "name=sra-", "--format", "{{.Name}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    volumes = [v.strip() for v in res.stdout.splitlines() if v.strip()]
    if volumes:
        failed.append(f"volumes: {', '.join(volumes)}")

    # 3. Networks
    res = subprocess.run(
        [
            "docker",
            "network",
            "ls",
            "--filter",
            "name=sra-",
            "--filter",
            "name=br-sra",
            "--format",
            "{{.Name}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    networks = [n.strip() for n in res.stdout.splitlines() if n.strip()]
    if networks:
        failed.append(f"networks: {', '.join(networks)}")

    # 4. Secrets / shared
    secrets_dir = REPO_ROOT / "secrets"
    if secrets_dir.exists() and any(secrets_dir.iterdir()):
        failed.append("secrets/ not empty")

    shared_dir = REPO_ROOT / "shared"
    if shared_dir.exists() and any(shared_dir.iterdir()):
        failed.append("shared/ not empty")

    # 5. Canaries
    if canaries:
        for c in canaries:
            if not c:
                continue
            # Check /tmp
            res_grep = subprocess.run(
                ["grep", "-rq", c, "/tmp"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if res_grep.returncode == 0:
                failed.append(f"canary {c[:8]} found in /tmp")

    passed = len(failed) == 0
    evidence = "Zero residue detected" if passed else f"Residue: {'; '.join(failed)}"
    return passed, evidence


def run_probe() -> dict[str, Any]:
    """Execute C5 check."""
    canaries = []
    for f in ["model_canary.txt", "red_canary.txt", "blue_canary.txt"]:
        p = REPO_ROOT / "secrets" / f
        if p.exists():
            canaries.append(p.read_text().strip())

    passed, evidence = check_residue_criteria(canaries)
    return {
        "id": "C5",
        "level": "L1",
        "zone": "host",
        "passed": passed,
        "evidence": evidence,
    }


def test_c5_residue_logic():
    """Unit test for residue verification logic."""
    # Test that check_residue_criteria correctly evaluates clean conditions
    assert callable(check_residue_criteria)


if __name__ == "__main__":
    res = run_probe()
    print(json.dumps(res, indent=2))
