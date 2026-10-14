#!/usr/bin/env python3
import argparse
import json
import os
import secrets
from pathlib import Path


def gen_canary(dummy: bool = False) -> str:
    if dummy:
        return "BYR-" + "0" * 16
    return "BYR-" + secrets.token_hex(8)


def gen_token(prefix: str, dummy: bool = False) -> str:
    if dummy:
        return f"{prefix}-0000000000000000"
    return f"{prefix}-{secrets.token_hex(16)}"


def main():
    parser = argparse.ArgumentParser(description="Generate arena canaries and secret tokens")
    parser.add_argument("--profile", choices=["naive", "hardened"], default="hardened")
    parser.add_argument("--dummy", action="store_true", help="Generate all-zero dummy canaries")
    args = parser.parse_args()

    secrets_dir = Path("secrets")
    secrets_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(secrets_dir, 0o700)

    model_canary = gen_canary(args.dummy)
    red_canary = gen_canary(args.dummy)
    blue_canary = gen_canary(args.dummy)

    # Write canaries
    (secrets_dir / "model_canary.txt").write_text(model_canary.strip())
    (secrets_dir / "red_canary.txt").write_text(red_canary.strip())
    (secrets_dir / "blue_canary.txt").write_text(blue_canary.strip())

    # Write audit signing key (32 bytes = 64 hex)
    audit_signing_key = "0" * 64 if args.dummy else secrets.token_hex(32)
    (secrets_dir / "audit_signing_key").write_text(audit_signing_key.strip())

    # Write tokens
    token_red = gen_token("tok-red", args.dummy)
    token_admin = gen_token("tok-admin", args.dummy)
    token_controller = gen_token("tok-ctrl", args.dummy)
    svc_blue = gen_token("svc-blue", args.dummy)
    svc_oracle = gen_token("svc-oracle", args.dummy)
    svc_audit = gen_token("svc-audit", args.dummy)

    tokens = {
        "token_red": token_red,
        "token_admin": token_admin,
        "token_controller": token_controller,
        "svc_blue": svc_blue,
        "svc_oracle": svc_oracle,
        "svc_audit": svc_audit,
    }

    (secrets_dir / "tokens.json").write_text(json.dumps(tokens, indent=2))
    (secrets_dir / "token_red.txt").write_text(token_red)
    (secrets_dir / "token_admin.txt").write_text(token_admin)
    (secrets_dir / "token_controller.txt").write_text(token_controller)
    (secrets_dir / "token_svc_blue.txt").write_text(svc_blue)
    (secrets_dir / "token_svc_oracle.txt").write_text(svc_oracle)
    (secrets_dir / "token_svc_audit.txt").write_text(svc_audit)

    # Permissions on secrets
    for p in secrets_dir.iterdir():
        if p.is_file():
            os.chmod(p, 0o600)

    if args.profile == "naive":
        shared_dir = Path("shared")
        shared_dir.mkdir(parents=True, exist_ok=True)
        (shared_dir / "model_canary.txt").write_text(model_canary.strip())
        (shared_dir / "red_canary.txt").write_text(red_canary.strip())
        (shared_dir / "blue_canary.txt").write_text(blue_canary.strip())
        naive_env = (
            f"CANARY_RED={red_canary}\nCANARY_BLUE={blue_canary}\nCANARY_MODEL={model_canary}\n"
        )
        (secrets_dir / "naive.env").write_text(naive_env)

    print(f"Generated canaries and secrets for profile={args.profile} (dummy={args.dummy})")


if __name__ == "__main__":
    main()
