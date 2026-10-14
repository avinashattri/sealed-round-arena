#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

PROBE_SCRIPTS = {
    "B1": "b1_egress.py",
    "B3": "b3_bypass.py",
    "B4": "b4_files.py",
}


def get_network_gateway(profile: str) -> str:
    net_name = "sra-naive_arena" if profile == "naive" else "sra-hardened_red_net"
    cmd = [
        "docker",
        "network",
        "inspect",
        net_name,
        "-f",
        "{{(index .IPAM.Config 0).Gateway}}",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode == 0 and res.stdout.strip():
        return res.stdout.strip()
    return "127.0.0.1"


def main():
    parser = argparse.ArgumentParser(description="Run arena probes")
    parser.add_argument("--profile", choices=["naive", "hardened"], default="naive")
    parser.add_argument("--only", default=None, help="Comma-separated probe IDs (e.g. B1,B3,B4)")
    args = parser.parse_args()

    probes_to_run = list(PROBE_SCRIPTS.keys())
    if args.only:
        filter_ids = [p.strip().upper() for p in args.only.split(",") if p.strip()]
        probes_to_run = [p for p in probes_to_run if p in filter_ids]

    gateway = get_network_gateway(args.profile)
    egress_target = f"{gateway}:9999"

    # Start throwaway HTTP listener on gateway for B1
    listener_proc = None
    if "B1" in probes_to_run:
        try:
            listener_cmd = [
                sys.executable,
                "-m",
                "http.server",
                "9999",
                "--bind",
                gateway,
                "--directory",
                "/tmp",
            ]
            listener_proc = subprocess.Popen(
                listener_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.5)
        except OSError as e:
            print(f"Warning: could not bind listener to {gateway}: {e}", file=sys.stderr)

    red_canary_file = Path("secrets/red_canary.txt")
    own_canary = red_canary_file.read_text().strip() if red_canary_file.exists() else ""

    compose_file = f"infra/compose/{args.profile}.yml"
    results = []

    try:
        for probe_id in probes_to_run:
            script_name = PROBE_SCRIPTS[probe_id]
            cmd = [
                "docker",
                "compose",
                "--project-directory",
                ".",
                "-f",
                compose_file,
                "--profile",
                "probe",
                "run",
                "--rm",
                "--no-deps",
                "-e",
                "ZONE=red",
                "-e",
                f"OWN_CANARY={own_canary}",
                "-e",
                "TARGETS=blue:9000,model:8080,audit:7000,oracle:7100",
                "-e",
                "CONTROL=broker:8000",
                "-e",
                f"EGRESS_TARGET={egress_target}",
                "red_probe",
                "python",
                f"/probes/{script_name}",
            ]

            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output_lines = [
                line.strip() for line in res.stdout.splitlines() if line.strip().startswith("{")
            ]

            parsed = None
            for line in output_lines:
                try:
                    data = json.loads(line)
                    if data.get("probe") == probe_id:
                        parsed = data
                        break
                except (json.JSONDecodeError, KeyError):
                    pass

            if parsed:
                verdict = parsed.get("verdict", "ERROR")
                evidence = parsed.get("evidence", "")
            else:
                verdict = "ERROR"
                evidence = f"Container failed or produced invalid output: {res.stderr[:100]}"

            print(f"{probe_id:<4}  {verdict:<5}  {evidence}")
            results.append(
                {
                    "probe": probe_id,
                    "verdict": verdict,
                    "evidence": evidence,
                }
            )
    finally:
        if listener_proc:
            listener_proc.terminate()
            try:
                listener_proc.wait(timeout=2)
            except OSError:
                listener_proc.kill()

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out_dir = Path("evidence/results")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"probes_{args.profile}_{ts}.json"
    out_file.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
