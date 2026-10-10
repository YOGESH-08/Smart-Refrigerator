from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone
from typing import Any

import requests


DEVICE_ID = "device-01"
SCENARIOS = {
    "normal": {"temp_offset": 0.0, "gas_offset": 0.0, "weight_offset": 0.0, "door_open": False},
    "warm": {"temp_offset": 6.0, "gas_offset": 25.0, "weight_offset": 0.0, "door_open": False},
    "door": {"temp_offset": 1.0, "gas_offset": 5.0, "weight_offset": 0.0, "door_open": True},
    "gas": {"temp_offset": 0.5, "gas_offset": 70.0, "weight_offset": 0.0, "door_open": False},
    "lowstock": {"temp_offset": 0.0, "gas_offset": 0.0, "weight_offset": -2.5, "door_open": False},
    "offline": {"temp_offset": 0.0, "gas_offset": 0.0, "weight_offset": 0.0, "door_open": False, "online": False},
    "demo": {"temp_offset": 0.0, "gas_offset": 0.0, "weight_offset": 0.0, "door_open": False},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_payload(scenario: str, tick: int) -> dict[str, Any]:
    base = SCENARIOS[scenario]
    temperature = 4.5 + random.gauss(0, 0.9) + base["temp_offset"] + (sin_like(tick) * 1.4)
    humidity = 48.0 + random.gauss(0, 2.8)
    gas = 110.0 + random.gauss(0, 12.0) + base["gas_offset"] + (max(0, 10 - tick % 60) * 0.8)
    weight = max(0.0, 5.0 + base["weight_offset"] + random.gauss(0, 0.4))
    door_open = bool(base.get("door_open", False)) if scenario != "demo" else bool(tick % 30 < 12)
    payload = {
        "device_id": DEVICE_ID,
        "temperature_c": round(temperature, 2),
        "humidity_pct": round(humidity, 2),
        "gas_voc": round(gas, 2),
        "weight_kg": round(weight, 2),
        "door_open": door_open,
        "battery_mv": round(3900 + random.gauss(0, 40), 1),
        "wifi_rssi_dbm": -62 + random.randint(-5, 5),
        "firmware_version": "1.1.0",
        "uptime_s": tick * 4,
    }
    return payload


def sin_like(value: int) -> float:
    import math

    return math.sin(value / 9.5)


def cycle_scenario(index: int) -> str:
    order = ["normal", "warm", "door", "gas", "lowstock", "demo"]
    return order[index % len(order)]


def run(api_url: str, interval: float, scenario: str, api_key: str) -> None:
    tick = 0
    current = scenario
    while True:
        if scenario == "demo":
            current = cycle_scenario(tick)
        if current == "offline":
            time.sleep(interval)
            tick += 1
            continue
        payload = build_payload(current, tick)
        response = requests.post(f"{api_url}/api/v1/readings", json=payload, headers={"X-API-Key": api_key}, timeout=5)
        response.raise_for_status()
        print(f"[{utc_now()}] {current}: {payload['temperature_c']}C / {payload['gas_voc']} VOC / door={payload['door_open']} / weight={payload['weight_kg']} kg")
        tick += 1
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Refrigerator device simulator")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS.keys()), default="normal")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--api-url", default="http://localhost:5000")
    parser.add_argument("--api-key", default="smart-fridge-demo-key")
    args = parser.parse_args()
    run(args.api_url, args.interval, args.scenario, args.api_key)
