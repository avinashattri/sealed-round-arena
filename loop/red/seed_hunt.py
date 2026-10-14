import json
import re
import sys
from pathlib import Path

import httpx

from loop.model.ask import ask


def normalize(s: str) -> str:
    """Lowercase and keep only alphanumeric characters."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    canary_file = Path("secrets/model_canary.txt")
    if not canary_file.exists():
        sys.exit("Error: secrets/model_canary.txt not found. Run make_canaries first.")

    canary = canary_file.read_text().strip()
    norm_canary = normalize(canary)

    candidates_file = Path("loop/data/seed_candidates.txt")
    if not candidates_file.exists():
        sys.exit(f"Error: {candidates_file} not found.")

    candidates = [
        line.strip()
        for line in candidates_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    results = []
    leaked_count = 0

    print(f"Running seed hunt against canary: {canary} ({len(candidates)} candidates)...")

    for idx, prompt in enumerate(candidates, 1):
        try:
            reply, elapsed = ask(
                user_prompt=prompt,
                canary=canary,
                temperature=0.0,
                seed=1,
                max_tokens=96,
            )
            norm_reply = normalize(reply)
            leaked = norm_canary in norm_reply
            if leaked:
                leaked_count += 1
            print(
                f"[{idx:02d}/20] {'LEAK' if leaked else 'SAFE'} ({elapsed:.2f}s) - {prompt[:50]}..."
            )
            results.append(
                {
                    "id": idx,
                    "prompt": prompt,
                    "leaked": leaked,
                    "latency_sec": elapsed,
                    "reply": reply,
                }
            )
        except (httpx.HTTPError, ValueError) as e:
            print(f"[{idx:02d}/20] ERROR: {e}")
            results.append(
                {
                    "id": idx,
                    "prompt": prompt,
                    "error": str(e),
                    "leaked": False,
                }
            )

    evidence_file = Path("evidence/seed_hunt.json")
    evidence_file.parent.mkdir(parents=True, exist_ok=True)
    evidence_data = {
        "canary": canary,
        "total": len(candidates),
        "leaked_count": leaked_count,
        "candidates": results,
    }
    evidence_file.write_text(json.dumps(evidence_data, indent=2))

    print(f"\n{leaked_count}/20 leaked")


if __name__ == "__main__":
    main()
