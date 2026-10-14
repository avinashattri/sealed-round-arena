import argparse
import json
import os
import sys
from pathlib import Path

import httpx


def get_admin_token() -> str:
    if "TOKEN_ADMIN" in os.environ:
        return os.environ["TOKEN_ADMIN"].strip()
    p1 = Path("/run/secrets/token_admin")
    if p1.exists():
        return p1.read_text().strip()
    p2 = Path("secrets/token_admin.txt")
    if p2.exists():
        return p2.read_text().strip()
    return ""


def main():
    parser = argparse.ArgumentParser(description="Broker admin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("state")

    move_parser = subparsers.add_parser("move")
    move_parser.add_argument("target_state")

    load_parser = subparsers.add_parser("load_round")
    load_parser.add_argument("campaign_id")
    load_parser.add_argument("round_id")

    args = parser.parse_args()

    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    base_url = os.environ.get("BROKER_URL", "http://127.0.0.1:8000")

    if args.command == "state":
        resp = httpx.get(f"{base_url}/admin/state", headers=headers)
        if resp.status_code != 200:
            sys.exit(f"Failed ({resp.status_code}): {resp.text}")
        print(json.dumps(resp.json(), indent=2))

    elif args.command == "move":
        resp = httpx.post(
            f"{base_url}/admin/transition",
            params={"to": args.target_state},
            headers=headers,
        )
        if resp.status_code != 200:
            sys.exit(f"Failed ({resp.status_code}): {resp.text}")
        print(json.dumps(resp.json(), indent=2))

    elif args.command == "load_round":
        resp = httpx.post(
            f"{base_url}/admin/load_round",
            json={"campaign_id": args.campaign_id, "round_id": args.round_id},
            headers=headers,
        )
        if resp.status_code != 200:
            sys.exit(f"Failed ({resp.status_code}): {resp.text}")
        print(json.dumps(resp.json(), indent=2))


if __name__ == "__main__":
    main()
