#!/usr/bin/env python3
import argparse
import json
import os
import secrets
from pathlib import Path


def gen_canary(dummy: bool = False, index: int = 0) -> str:
    if dummy:
        return f"BYR-{index:016x}"
    return "BYR-" + secrets.token_hex(8)


def gen_token(name: str, dummy: bool = False, index: int = 0) -> str:
    if dummy:
        return f"dummy-token-{index}"
    return secrets.token_urlsafe(32)


def main():
    parser = argparse.ArgumentParser(description="Generate arena canaries and secret tokens")
    parser.add_argument("--profile", choices=["naive", "hardened"], default="hardened")
    parser.add_argument("--campaign", default="c-001", help="Campaign ID")
    parser.add_argument("--dummy", action="store_true", help="Generate deterministic dummy values")
    args = parser.parse_args()

    secrets_dir = Path("secrets")
    secrets_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(secrets_dir, 0o755)

    zones = ["red", "blue", "model"]
    canaries = {}
    for i, zone in enumerate(zones):
        canaries[zone] = gen_canary(args.dummy, index=i + 1)
        (secrets_dir / f"{zone}_canary.txt").write_text(canaries[zone].strip())

    # Audit signing key (32 bytes = 64 hex)
    audit_signing_key = "00" * 32 if args.dummy else secrets.token_hex(32)
    (secrets_dir / "audit_signing_key.txt").write_text(audit_signing_key.strip())
    (secrets_dir / "audit_signing_key").write_text(audit_signing_key.strip())

    # Tokens
    token_names = ["red", "controller", "svc_blue", "svc_oracle", "svc_audit", "admin"]
    tokens = {}
    tokens_registry = {}

    for i, name in enumerate(token_names):
        tok_val = gen_token(name, args.dummy, index=i + 1)
        tokens[name] = tok_val
        (secrets_dir / f"token_{name}.txt").write_text(tok_val.strip())
        principal = name.replace("svc_", "")
        tokens_registry[tok_val] = {
            "principal": principal,
            "campaign_id": args.campaign,
        }

    (secrets_dir / "tokens.json").write_text(json.dumps(tokens_registry, indent=2))

    # Empty attack placeholders if absent
    if not (secrets_dir / "red_attacks.json").exists():
        (secrets_dir / "red_attacks.json").write_text("{}")
    if not (secrets_dir / "red_meta.json").exists():
        (secrets_dir / "red_meta.json").write_text("{}")

    if args.profile == "naive":
        shared_dir = Path("shared")
        shared_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(shared_dir, 0o755)
        for zone in zones:
            (shared_dir / f"{zone}_canary.txt").write_text(canaries[zone].strip())
            os.chmod(shared_dir / f"{zone}_canary.txt", 0o644)

        naive_env = (
            f"RED_CANARY={canaries['red']}\n"
            f"BLUE_CANARY={canaries['blue']}\n"
            f"MODEL_CANARY={canaries['model']}\n"
            f"CANARY_RED={canaries['red']}\n"
            f"CANARY_BLUE={canaries['blue']}\n"
            f"CANARY_MODEL={canaries['model']}\n"
        )
        (secrets_dir / "naive.env").write_text(naive_env)

    # Set permissions 0644 for all files in secrets
    for p in secrets_dir.iterdir():
        if p.is_file():
            os.chmod(p, 0o644)

    print(f"Generated canaries and secrets for profile={args.profile} (dummy={args.dummy})")


if __name__ == "__main__":
    main()
