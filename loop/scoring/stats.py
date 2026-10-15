import math


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Calculate the Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def state(
    base: tuple[int, int],
    new: tuple[int, int],
    fpr_base: float,
    fpr_new: float,
    thr: float = 0.10,
    fpr_budget: float = 0.02,
    min_drop: float = 0.10,
) -> str:
    """Classify the progression state between base and new defense rounds."""
    if fpr_new - fpr_base > fpr_budget:
        return "OVER-BLOCKING (not accepted)"
    k, n = new
    if n >= 30 and wilson(k, n)[1] <= thr:
        return "FIXED"
    if k / n <= base[0] / base[1] - min_drop:
        return "PARTIALLY FIXED"
    return "STILL VULNERABLE"
