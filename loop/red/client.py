import json
import os
import random
import sys
import time
from pathlib import Path

import httpx


def get_token_red() -> str:
    token = os.environ.get("TOKEN_RED")
    if token:
        return token.strip()
    for p in ["/run/secrets/token_red", "secrets/token_red.txt"]:
        path = Path(p)
        if path.exists():
            return path.read_text().strip()
    return ""


def get_red_attacks() -> dict[str, str]:
    for p in [
        "/tmp/red_attacks.json",
        "/run/secrets/red_attacks",
        "/run/secrets/red_attacks.json",
        "secrets/red_attacks.json",
    ]:
        path = Path(p)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def get_red_meta() -> dict:
    for p in [
        "/tmp/red_meta.json",
        "/run/secrets/red_meta",
        "/run/secrets/red_meta.json",
        "secrets/red_meta.json",
    ]:
        path = Path(p)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return {}


def main():
    token = get_token_red()
    if not token:
        sys.exit("Error: token_red not found")

    attacks = get_red_attacks()
    meta = get_red_meta()
    campaign_id = meta.get("campaign_id", "c-001")
    round_id = meta.get("round_id", "r-001")

    broker_url = os.environ.get("BROKER_URL", "http://broker:8000")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print(f"Red client starting: submitting {len(attacks)} attacks to {broker_url}...")

    for cid, payload in attacks.items():
        time.sleep(random.uniform(0.0, 1.5))
        body = {
            "campaign_id": campaign_id,
            "round_id": round_id,
            "challenge_id": cid,
            "payload": payload,
            "max_tokens": 128,
        }
        try:
            resp = httpx.post(f"{broker_url}/submit", json=body, headers=headers, timeout=10.0)
            if resp.status_code != 200:
                print(f"Failed to submit {cid}: {resp.status_code} - {resp.text}", file=sys.stderr)
            else:
                print(f"Submitted {cid}: {resp.json().get('status')}")
        except (httpx.HTTPError, OSError) as e:
            print(f"Error submitting {cid}: {e}", file=sys.stderr)

    print("Red client completed submissions.")


if __name__ == "__main__":
    main()
