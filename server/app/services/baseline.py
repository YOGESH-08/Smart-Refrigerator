from __future__ import annotations

from statistics import mean


def compute_baseline(samples: list[float] | None) -> float:
    if not samples:
        return 0.0
    return float(mean(samples))


def reset_baseline(default_value: float = 120.0) -> float:
    return float(default_value)
