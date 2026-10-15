"""
Tamper functions for testing verify.py.
Each function takes a list of entry dicts and returns a NEW (tampered) list.
Never mutates the original.
"""

from __future__ import annotations

import copy
from typing import Any

ALL = None  # set after definitions


def flip(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Change the event field of entry 3 (seq 3, index 2)."""
    entries = copy.deepcopy(entries)
    for e in entries:
        if e.get("seq") == 3:
            # toggle between two event values
            original = e.get("event", "seal")
            e["event"] = "reveal" if original != "reveal" else "seal"
            break
    return entries


def delete(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop entry with seq 2."""
    entries = copy.deepcopy(entries)
    return [e for e in entries if e.get("seq") != 2]


def reorder(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Swap the last two entries so a higher-seq entry is followed by a lower-seq entry,
    triggering out-of-order detection in the verifier."""
    entries = copy.deepcopy(entries)
    if len(entries) >= 2:
        entries[-1], entries[-2] = entries[-2], entries[-1]
    return entries


def truncate(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop the last 3 entries."""
    entries = copy.deepcopy(entries)
    return entries[:-3] if len(entries) >= 3 else entries[:0]


def replay(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Duplicate entry with seq 3 (insert a copy after it)."""
    entries = copy.deepcopy(entries)
    dup = None
    for e in entries:
        if e.get("seq") == 3:
            dup = copy.deepcopy(e)
            break
    if dup is not None:
        idx = next(i for i, e in enumerate(entries) if e.get("seq") == 3)
        entries.insert(idx + 1, dup)
    return entries


ALL = {
    "flip": flip,
    "delete": delete,
    "reorder": reorder,
    "truncate": truncate,
    "replay": replay,
}
