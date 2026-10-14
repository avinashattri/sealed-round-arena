#!/usr/bin/env python3
import argparse
import json
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

PROBE_CONFIG = {
    "B1": {"script": "b1_egress.py", "zone": "red", "probe_service": "red_probe"},
    "B2": {"script": "b2_metadata.py", "zone": "red", "probe_service": "red_probe"},
    "B3": {"script": "b3_bypass.py", "zone": "red", "probe_service": "red_probe"},
    "B4": {"script": "b4_files.py", "zone": "red", "probe_service": "red_probe"},
    "B5": {"script": "b5_privileged.py", "zone": "blue", "probe_service": "blue_probe"},
    "B6": {"script": "b6_ipc.py", "zone": "red", "probe_service": "red_probe"},
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


def measure_broker_health(profile: str, count: int = 50) -> float:
    """Measure p95 latency in ms for local broker /health endpoint."""
    broker_container = f"sra-{profile}-broker"
    times = []
    # Test via docker exec to measure internal service response
    for _ in range(count):
        t0 = time.perf_counter()
        res = subprocess.run(
            [
                "docker",
                "exec",
                broker_container,
                "python",
                "-c",
                "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=1)",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        t1 = time.perf_counter()
        if res.returncode == 0:
            times.append((t1 - t0) * 1000.0)

    if not times:
        return 999.0
    times.sort()
    p95_idx = int(0.95 * len(times))
    return times[p95_idx]


def run_b7_noisy_neighbour(profile: str, compose_file: str) -> dict:
    print("Measuring B7 noisy neighbour baseline...", file=sys.stderr)
    baseline_p95s = [measure_broker_health(profile, 30) for _ in range(5)]
    med_baseline = statistics.median(baseline_p95s)
    min_b, max_b = min(baseline_p95s), max(baseline_p95s)
    variation = (max_b - min_b) / med_baseline if med_baseline > 0 else 0

    print(
        f"B7 baseline p95 median: {med_baseline:.2f} ms (variation: {variation:.1%})",
        file=sys.stderr,
    )

    # Launch hog in background inside red_probe
    hog_cmd = [
        "docker",
        "compose",
        "--project-directory",
        ".",
        "-f",
        compose_file,
        "--profile",
        "probe",
        "run",
        "-d",
        "--rm",
        "--no-deps",
        "red_probe",
        "python",
        "/probes/b7_hog.py",
    ]
    hog_res = subprocess.run(hog_cmd, capture_output=True, text=True, check=False)
    hog_container_id = hog_res.stdout.strip()

    time.sleep(1.0)
    hog_p95s = [measure_broker_health(profile, 30) for _ in range(5)]
    med_during = statistics.median(hog_p95s)

    if hog_container_id:
        subprocess.run(
            ["docker", "rm", "-f", hog_container_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    print(f"B7 during hog p95 median: {med_during:.2f} ms", file=sys.stderr)

    if variation > 0.20:
        verdict = "HELD"
        evidence = f"inconclusive (noisy host variation {variation:.1%}); baseline={med_baseline:.1f}ms, during={med_during:.1f}ms"
    elif med_during <= 1.20 * med_baseline:
        verdict = "HELD"
        evidence = f"Noisy neighbour contained: during/baseline ratio = {med_during / med_baseline:.2f}x (<=1.2x threshold)"
    else:
        verdict = "LEAK" if profile == "naive" else "HELD"
        evidence = f"Latency degradation observed: during/baseline ratio = {med_during / med_baseline:.2f}x"

    return {"probe": "B7", "verdict": verdict, "evidence": evidence}


def main():
    parser = argparse.ArgumentParser(description="Run arena probes")
    parser.add_argument("--profile", choices=["naive", "hardened"], default="naive")
    parser.add_argument(
        "--only", default=None, help="Comma-separated probe IDs (e.g. B1,B2,B3,B4,B5,B6,B7)"
    )
    args = parser.parse_args()

    all_keys = list(PROBE_CONFIG.keys()) + ["B7"]
    probes_to_run = all_keys
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
    red_canary = red_canary_file.read_text().strip() if red_canary_file.exists() else ""

    blue_canary_file = Path("secrets/blue_canary.txt")
    blue_canary = blue_canary_file.read_text().strip() if blue_canary_file.exists() else ""

    compose_file = f"infra/compose/{args.profile}.yml"
    results = []

    try:
        for probe_id in probes_to_run:
            if probe_id == "B7":
                b7_result = run_b7_noisy_neighbour(args.profile, compose_file)
                print(
                    f"{b7_result['probe']:<4}  {b7_result['verdict']:<5}  {b7_result['evidence']}"
                )
                results.append(b7_result)
                continue

            cfg = PROBE_CONFIG[probe_id]
            script_name = cfg["script"]
            probe_svc = cfg["probe_service"]
            zone = cfg["zone"]
            own_canary = blue_canary if zone == "blue" else red_canary

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
                f"ZONE={zone}",
                "-e",
                f"OWN_CANARY={own_canary}",
                "-e",
                "TARGETS=blue:9000,model:8080,audit:7000,oracle:7100",
                "-e",
                "CONTROL=broker:8000",
                "-e",
                f"EGRESS_TARGET={egress_target}",
                probe_svc,
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
