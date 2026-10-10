from __future__ import annotations

from statistics import mean


def summarize_temperature(rows: list[dict]) -> dict:
    values = [float(row["temperature_c"]) for row in rows]
    if not values:
        return {"min": 0.0, "avg": 0.0, "max": 0.0}
    return {"min": min(values), "avg": mean(values), "max": max(values)}


def summarize_door_open(rows: list[dict]) -> int:
    return int(sum(1 for row in rows if bool(row.get("door_open"))))
