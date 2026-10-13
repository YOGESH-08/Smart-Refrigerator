from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone
from typing import Any

import requests


DEVICE_ID = "refrigerator-01"
SCENARIOS = {
    "normal": {"temp_offset": 0.0, "gas_offset": 0.0, "weight_offset": 0.0, "door_open": False},
    "warm": {"temp_offset": 19.0, "gas_offset": 25.0, "door_open": False},
    "door": {"temp_offset": 1.0, "gas_offset": 5.0, "door_open": True},
    "gas": {"temp_offset": 0.5, "gas_offset": 700.0, "door_open": False},
    "lowstock": {"temp_offset": 0.0, "gas_offset": 0.0, "door_open": False},
    "offline": {"temp_offset": 0.0, "gas_offset": 0.0, "door_open": False, "online": False},
    "demo": {"temp_offset": 0.0, "gas_offset": 0.0, "door_open": False},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_payload(scenario: str, tick: int) -> dict[str, Any]:
    base = SCENARIOS[scenario]
    temperature = 4.5 + random.gauss(0, 0.9) + base["temp_offset"] + (sin_like(tick) * 1.4)
    gas = max(0, min(4095, round(1400 + random.gauss(0, 45) + base["gas_offset"] + (max(0, 10 - tick % 60) * 4))))
    temperature_alarm = temperature > 29.0
    door_open = bool(base.get("door_open", False)) if scenario != "demo" else bool(tick % 30 < 12)
    payload = {
        "device_id": DEVICE_ID,
        "temperature_c": round(temperature, 2),
        "gas_adc_raw": gas,
        "door_open": door_open,
        "door_sensor_verified": False,
        "temperature_sensor_ok": True,
        "gas_sensor_ok": True,
        "alarm_active": temperature_alarm,
        "alarm_muted": False,
        "mute_remaining_s": 0,
        "fan_on": temperature_alarm,
        "red_led_on": temperature_alarm,
        "green_led_on": not temperature_alarm,
        "buzzer_on": temperature_alarm,
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
        print(f"[{utc_now()}] {current}: {payload['temperature_c']}C / MQ-135 ADC={payload['gas_adc_raw']} / alarm={payload['alarm_active']}")
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
