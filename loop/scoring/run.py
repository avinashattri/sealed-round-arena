"""loop.scoring.run: 3-round defense progression runner and reporter."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from loop.scoring.collect import collect_round
from loop.scoring.stats import state


def run_loop(
    family: str = "F1",
    size: str = "demo",
    stub_model: bool = False,
    stand_in_red: bool = False,
) -> dict[str, Any]:
    attacks_path = f"loop/data/attacks/{family}.json"
    rounds_data = []

    print(f"=== Starting 3-Round Arena Loop: Family={family}, Size={size} ===")

    prev_res = None
    for v in [1, 2, 3]:
        round_id = f"r-00{v}"
        print(f"\n--> Executing Round {v} (Defense v{v}, Round ID {round_id})...")

        cmd = [
            sys.executable,
            "-m",
            "referee.controller",
            "run",
            "--campaign",
            "c-001",
            "--round",
            round_id,
            "--attacks",
            attacks_path,
            "--defense",
            str(v),
            "--size",
            size,
        ]
        if v == 1:
            cmd.append("--fresh")
        if stub_model:
            cmd.append("--stub-model")
        if stand_in_red:
            cmd.append("--stand-in-red")

        res_proc = subprocess.run(cmd, check=False)
        if res_proc.returncode != 0:
            print(
                f"Error: Controller failed on round {round_id} with exit code {res_proc.returncode}",
                file=sys.stderr,
            )
            sys.exit(res_proc.returncode)

        res = collect_round(round_id=round_id, attacks_path=attacks_path)

        if v == 1:
            st = "(baseline)"
        else:
            base_k, base_n = prev_res["metrics"]["pooled_asr"][:2]
            new_k, new_n = res["metrics"]["pooled_asr"][:2]
            fpr_base = prev_res["metrics"]["fpr"]
            fpr_new = res["metrics"]["fpr"]

            st = state(
                base=(base_k, base_n),
                new=(new_k, new_n),
                fpr_base=fpr_base,
                fpr_new=fpr_new,
            )
            if new_n < 30 and new_k == 0:
                st = "see note (n<30)"

        res["state"] = st
        rounds_data.append(res)
        prev_res = res
        print(f"--> Completed Round {v}: State={st}")

    header = "Round  Defense  Seed ASR   Variants ASR   Pooled ASR   [95% CI]        FPR     State"
    separator = "-" * len(header)
    print()
    print(header)
    print(separator)

    n_less_than_30 = False
    last_ci_high = 0.0

    for idx, r in enumerate(rounds_data, start=1):
        m = r["metrics"]
        def_label = f"v{idx}"
        s_k, s_n = m["seed_asr"]
        v_k, v_n = m["variants_asr"]
        p_k, p_n, (ci_low, ci_high) = m["pooled_asr"]
        fpr = m["fpr"]
        st = r["state"]

        seed_str = f"{s_k}/{s_n}"
        var_str = f"{v_k}/{v_n}"
        pool_str = f"{p_k}/{p_n}"
        ci_str = f"[{ci_low:.2f}, {ci_high:.2f}]"
        fpr_str = f"{fpr * 100:.1f}%"

        if p_n < 30:
            n_less_than_30 = True
            last_ci_high = ci_high

        print(
            f"{idx:<6} {def_label:<8} {seed_str:<10} {var_str:<14} {pool_str:<12} {ci_str:<15} {fpr_str:<7} {st}"
        )

    print(separator)
    if n_less_than_30:
        print(
            f"Note: n<30 trials; Wilson upper bound is {last_ci_high:.2f} (requires n>=30 to certify FIXED)."
        )

    v1_rows = rounds_data[0]["rows"]
    breaches = [row for row in v1_rows if "BREACH" in row["path_label"]]
    if breaches:
        cid_val = breaches[0]["cid"]
        pl_val = breaches[0]["path_label"]
        print(f"\nv1 trace sample: {cid_val} -> {pl_val}")

    results_dir = Path("evidence/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    loop_summary = {
        "family": family,
        "size": size,
        "rounds": [
            {
                "round": idx,
                "round_id": f"r-00{idx}",
                "defense": f"v{idx}",
                "seed_asr": list(r["metrics"]["seed_asr"]),
                "variants_asr": list(r["metrics"]["variants_asr"]),
                "pooled_asr": [r["metrics"]["pooled_asr"][0], r["metrics"]["pooled_asr"][1]],
                "ci": [
                    round(r["metrics"]["pooled_asr"][2][0], 4),
                    round(r["metrics"]["pooled_asr"][2][1], 4),
                ],
                "fpr": round(r["metrics"]["fpr"], 4),
                "detection_rate": round(r["metrics"]["detection_rate"], 4),
                "state": r["state"],
                "total_challenges": len(r["rows"]),
            }
            for idx, r in enumerate(rounds_data, start=1)
        ],
    }
    (results_dir / "loop.json").write_text(json.dumps(loop_summary, indent=2))
    print("\nLoop results written to evidence/results/loop.json")
    return loop_summary


def main():
    parser = argparse.ArgumentParser(description="Run 3-round defense progression loop")
    parser.add_argument("--family", default="F1", help="Attack family name (e.g. F1)")
    parser.add_argument(
        "--size", choices=["mini", "demo", "full"], default="demo", help="Workload size"
    )
    parser.add_argument(
        "--stub-model", action="store_true", help="Use stubmodel instead of real model"
    )
    parser.add_argument("--stand-in-red", action="store_true", help="Use stand-in red submissions")

    args = parser.parse_args()
    run_loop(
        family=args.family,
        size=args.size,
        stub_model=args.stub_model,
        stand_in_red=args.stand_in_red,
    )


if __name__ == "__main__":
    main()
