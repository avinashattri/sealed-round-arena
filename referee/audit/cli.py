import argparse
import json
import sys
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description="Audit Service Admin CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("export", help="Export audit log as JSONL")

    cp_parser = subparsers.add_parser("checkpoint", help="Generate signed checkpoint")
    cp_parser.add_argument("round_id", help="Round ID (e.g. r-001)")

    subparsers.add_parser("pubkey", help="Get audit signing verify key hex")

    args = parser.parse_args()
    base_url = "http://127.0.0.1:7000"

    try:
        if args.command == "export":
            req = urllib.request.Request(f"{base_url}/admin/export")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                for entry in data:
                    print(json.dumps(entry, sort_keys=True))
        elif args.command == "checkpoint":
            url = f"{base_url}/admin/checkpoint?round_id={urllib.parse.quote(args.round_id)}"
            req = urllib.request.Request(url, data=b"", method="POST")
            with urllib.request.urlopen(req) as resp:
                print(resp.read().decode().strip())
        elif args.command == "pubkey":
            req = urllib.request.Request(f"{base_url}/admin/pubkey")
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                print(data["verify_key_hex"])
    except Exception as e:
        print(f"Error executing audit CLI: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
