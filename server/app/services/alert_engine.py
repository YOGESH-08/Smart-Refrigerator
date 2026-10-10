from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AlertState:
    active: bool = False
    acknowledged: bool = False
    resolved: bool = False
    first_seen: str | None = None
    last_triggered: str | None = None
    severity: str = "warning"
    message: str = ""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    if dt is None:
        dt = _utc_now()
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def evaluate_temperature(value: float, state: AlertState | None, threshold: float, hysteresis: float = 1.5, min_duration_s: int = 120) -> AlertState:
    state = state or AlertState()
    if value >= threshold:
        if not state.active:
            state.active = True
            state.first_seen = _iso()
            state.last_triggered = state.first_seen
            state.message = f"Temperature above {threshold}°C"
            state.severity = "high"
        else:
            state.last_triggered = _iso()
        return state
    clear_threshold = threshold - hysteresis
    if state.active and value <= clear_threshold:
        state.active = False
        state.resolved = True
        state.message = f"Temperature returned below {clear_threshold}°C"
        state.severity = "info"
    return state


def evaluate_gas_delta(current_gas: float, baseline: float, threshold: float, state: AlertState | None = None) -> AlertState:
    state = state or AlertState()
    delta = current_gas - baseline
    if delta >= threshold:
        if not state.active:
            state.active = True
            state.first_seen = _iso()
            state.last_triggered = state.first_seen
            state.message = f"Gas level increased by {delta:.1f} above baseline"
            state.severity = "high"
        else:
            state.last_triggered = _iso()
        return state
    if state.active and delta < threshold * 0.6:
        state.active = False
        state.resolved = True
        state.message = "Gas level back within baseline tolerance"
        state.severity = "info"
    return state


def evaluate_door_open(door_open: bool, elapsed_seconds: float, threshold: float, state: AlertState | None = None) -> AlertState:
    state = state or AlertState()
    if door_open and elapsed_seconds >= threshold:
        if not state.active:
            state.active = True
            state.first_seen = _iso()
            state.last_triggered = state.first_seen
            state.message = "Door has been open longer than configured threshold"
            state.severity = "medium"
        else:
            state.last_triggered = _iso()
        return state
    if state.active and (not door_open or elapsed_seconds < threshold * 0.75):
        state.active = False
        state.resolved = True
        state.message = "Door is closed or within acceptable duration"
        state.severity = "info"
    return state


def evaluate_low_inventory(weight_kg: float, threshold: float, state: AlertState | None = None) -> AlertState:
    state = state or AlertState()
    if weight_kg <= threshold:
        if not state.active:
            state.active = True
            state.first_seen = _iso()
            state.last_triggered = state.first_seen
            state.message = f"Inventory low: {weight_kg:.2f} kg remaining"
            state.severity = "medium"
        else:
            state.last_triggered = _iso()
        return state
    if state.active and weight_kg > threshold + 0.25:
        state.active = False
        state.resolved = True
        state.message = "Inventory recovered above critical threshold"
        state.severity = "info"
    return state


def evaluate_offline(last_seen_delta_s: float, threshold: float, state: AlertState | None = None) -> AlertState:
    state = state or AlertState()
    if last_seen_delta_s >= threshold:
        if not state.active:
            state.active = True
            state.first_seen = _iso()
            state.last_triggered = state.first_seen
            state.message = "Device offline: heartbeat exceeded threshold"
            state.severity = "high"
        else:
            state.last_triggered = _iso()
        return state
    if state.active and last_seen_delta_s < threshold * 0.8:
        state.active = False
        state.resolved = True
        state.message = "Device heartbeat recovered"
        state.severity = "info"
    return state


def create_alert_record(device_id: str, alert_type: str, state: AlertState, status: str = "active") -> dict[str, Any]:
    record = {
        "device_id": device_id,
        "alert_type": alert_type,
        "severity": state.severity,
        "status": status,
        "message": state.message,
        "first_seen": state.first_seen or _iso(),
        "last_triggered": state.last_triggered or state.first_seen or _iso(),
        "acknowledged_at": None,
        "acknowledged_by": None,
        "resolved_at": None,
    }
    return record


def build_alert_records(reading: dict[str, Any], thresholds: dict[str, float], baseline_gas: float, alert_state: dict[str, AlertState] | None = None) -> list[dict[str, Any]]:
    current = process_reading(reading, thresholds, baseline_gas, alert_state or {})
    generated: list[dict[str, Any]] = []
    rules = {
        "temperature_high": current.get("temperature_high"),
        "gas_rise": current.get("gas_rise"),
        "door_open": current.get("door_open"),
        "low_inventory": current.get("low_inventory"),
    }
    for key, state in rules.items():
        if not state:
            continue
        if state.active:
            record = create_alert_record(reading.get("device_id", "device-01"), key, state, "active")
            generated.append(record)
        elif state.resolved:
            record = create_alert_record(reading.get("device_id", "device-01"), key, state, "resolved")
            record["resolved_at"] = _iso()
            generated.append(record)
    return generated


def process_reading(reading: dict[str, Any], thresholds: dict[str, float], baseline_gas: float, alert_state: dict[str, AlertState] | None = None) -> dict[str, AlertState]:
    state = alert_state or {}
    state["temperature_high"] = evaluate_temperature(reading["temperature_c"], state.get("temperature_high"), thresholds["temperature_high_c"])
    state["gas_rise"] = evaluate_gas_delta(reading["gas_voc"], baseline_gas, thresholds["gas_rise_delta"], state.get("gas_rise"))
    state["door_open"] = evaluate_door_open(reading["door_open"], float(reading.get("door_open_seconds", 0.0)), thresholds["door_open_seconds"], state.get("door_open"))
    state["low_inventory"] = evaluate_low_inventory(reading["weight_kg"], thresholds["low_inventory_kg"], state.get("low_inventory"))
    return state


def rule_is_active(alert_state: AlertState | None) -> bool:
    return bool(alert_state and alert_state.active)


__all__ = [
    "AlertState",
    "process_reading",
    "build_alert_records",
    "evaluate_temperature",
    "evaluate_gas_delta",
    "evaluate_door_open",
    "evaluate_low_inventory",
    "evaluate_offline",
    "create_alert_record",
    "rule_is_active",
]
