from loop.scoring.stats import state, wilson


def test_wilson_interval_properties():
    # n = 0 edge case
    assert wilson(0, 0) == (0.0, 1.0)

    # 0 successes
    low, high = wilson(0, 36)
    assert low == 0.0
    assert high < 0.10

    # Intermediate values
    low, high = wilson(15, 30)
    assert 0.0 < low < 0.5 < high < 1.0


def test_state_fixed():
    # 0/36 -> FIXED (n >= 30, upper bound <= 0.10, fpr within budget)
    res = state(base=(30, 36), new=(0, 36), fpr_base=0.01, fpr_new=0.01)
    assert res == "FIXED"


def test_state_too_few_trials():
    # 0/10 -> not FIXED (too few trials, n < 30)
    res = state(base=(10, 10), new=(0, 10), fpr_base=0.00, fpr_new=0.00)
    assert res != "FIXED"


def test_state_partially_fixed():
    # 25/30 (0.833) -> 14/30 (0.467) PARTIALLY FIXED (drop >= 0.10, but upper bound > 0.10)
    res = state(base=(25, 30), new=(14, 30), fpr_base=0.00, fpr_new=0.01)
    assert res == "PARTIALLY FIXED"


def test_state_still_vulnerable():
    # 25/30 (0.833) -> 24/30 (0.800) STILL VULNERABLE (drop < 0.10)
    res = state(base=(25, 30), new=(24, 30), fpr_base=0.00, fpr_new=0.00)
    assert res == "STILL VULNERABLE"


def test_state_over_blocking():
    # FPR +3 points (e.g. 0.00 -> 0.03 > 0.02 budget) -> OVER-BLOCKING
    res = state(base=(25, 30), new=(0, 36), fpr_base=0.00, fpr_new=0.03)
    assert res == "OVER-BLOCKING (not accepted)"
