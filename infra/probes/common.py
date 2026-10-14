import json
import os
import sys


def emit(probe_id: str, verdict: str, evidence: str, extra: dict | None = None):
    """
    Emit probe result as a single JSON line to stdout and exit.
    verdict: 'HELD', 'LEAK', or 'ERROR'
    """
    payload = {
        "probe": probe_id,
        "verdict": verdict,
        "evidence": evidence,
        **(extra or {}),
    }
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()
    os._exit(0)
