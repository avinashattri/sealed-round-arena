from enum import StrEnum


class RoundState(StrEnum):
    PROVISIONED = "PROVISIONED"
    COMMITTED = "COMMITTED"
    SEALED = "SEALED"
    EXECUTING = "EXECUTING"
    CLOSED = "CLOSED"
    REVEALED = "REVEALED"
    ANALYSED = "ANALYSED"
    RESET = "RESET"


VALID_TRANSITIONS = {
    RoundState.PROVISIONED: RoundState.COMMITTED,
    RoundState.COMMITTED: RoundState.SEALED,
    RoundState.SEALED: RoundState.EXECUTING,
    RoundState.EXECUTING: RoundState.CLOSED,
    RoundState.CLOSED: RoundState.REVEALED,
    RoundState.REVEALED: RoundState.ANALYSED,
    RoundState.ANALYSED: RoundState.RESET,
    RoundState.RESET: RoundState.PROVISIONED,
}


def can_move(current: str | RoundState, target: str | RoundState) -> bool:
    """Check if transitioning from current state to target state is allowed."""
    try:
        curr_state = RoundState(current)
        tgt_state = RoundState(target)
    except ValueError:
        return False

    return VALID_TRANSITIONS.get(curr_state) == tgt_state
