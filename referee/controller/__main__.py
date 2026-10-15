import argparse

from referee.controller.phases import (
    phase_0_provision,
    phase_1_commit,
    phase_2_seal,
    phase_3_execute,
    phase_4_close,
    phase_5_reveal,
    phase_6_results,
)


def main():
    parser = argparse.ArgumentParser(description="Sealed Round Arena Controller")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run arena round")
    run_parser.add_argument("--campaign", default="c-001", help="Campaign ID")
    run_parser.add_argument("--round", default="r-001", help="Round ID")
    run_parser.add_argument(
        "--attacks", default="loop/data/attacks/F1.json", help="Path to attacks JSON"
    )
    run_parser.add_argument("--defense", type=int, default=1, help="Defense version (1, 2, 3)")
    run_parser.add_argument(
        "--size", choices=["mini", "demo", "full"], default="mini", help="Round workload size"
    )
    run_parser.add_argument(
        "--tamper-attack", default=None, help="Tamper specific attack payload (e.g. ch-0003)"
    )
    run_parser.add_argument(
        "--stub-model", action="store_true", help="Use stubmodel instead of real model"
    )
    run_parser.add_argument(
        "--stand-in-red", action="store_true", help="Controller sends attacks as stand-in red"
    )
    run_parser.add_argument(
        "--fresh", action="store_true", help="Tear down and restart environment cleanly"
    )

    args = parser.parse_args()

    if args.command == "run":
        # 0 PROVISION
        priv_hex, _pub_hex, blue_id, model_id = phase_0_provision(
            campaign_id=args.campaign,
            round_id=args.round,
            defense=args.defense,
            fresh=args.fresh,
            stub_model=args.stub_model,
        )

        # 1 COMMIT
        attack_pairs, nonce_hex, commitment_hex = phase_1_commit(
            campaign_id=args.campaign,
            round_id=args.round,
            attacks_path=args.attacks,
            size=args.size,
            tamper_attack=args.tamper_attack,
            blue_id=blue_id,
            model_id=model_id,
        )

        # 2 SEAL
        phase_2_seal(
            campaign_id=args.campaign,
            round_id=args.round,
            initial_blue_id=blue_id,
            defense=args.defense,
        )

        # 3 EXECUTE
        benign_items = phase_3_execute(
            campaign_id=args.campaign,
            round_id=args.round,
            attack_pairs=attack_pairs,
            size=args.size,
            stand_in_red=args.stand_in_red,
        )

        # 4 CLOSE
        phase_4_close(
            campaign_id=args.campaign,
            round_id=args.round,
            stub_model=args.stub_model,
            initial_blue_id=blue_id,
            defense=args.defense,
        )

        # 5 REVEAL
        phase_5_reveal(
            campaign_id=args.campaign,
            round_id=args.round,
            priv_hex=priv_hex,
            nonce_hex=nonce_hex,
            commitment_hex=commitment_hex,
            attack_pairs=attack_pairs,
        )

        # 6 RESULTS
        phase_6_results(
            campaign_id=args.campaign,
            round_id=args.round,
            attack_pairs=attack_pairs,
            benign_items=benign_items,
        )


if __name__ == "__main__":
    main()
