from app.services.alert_engine import AlertState, process_reading


def test_temperature_hysteresis_triggers_and_clears():
    thresholds = {"temperature_high_c": 7.0, "gas_rise_delta": 10.0, "door_open_seconds": 180.0, "low_inventory_kg": 2.5}
    previous = {}
    reading = {"temperature_c": 8.5, "gas_voc": 110.0, "weight_kg": 5.0, "door_open": False, "door_open_seconds": 0.0}
    updated = process_reading(reading, thresholds, 120.0, previous)
    assert updated["temperature_high"].active is True

    reading["temperature_c"] = 5.0
    updated = process_reading(reading, thresholds, 120.0, updated)
    assert updated["temperature_high"].active is False


def test_gas_delta_alert_uses_baseline_and_stays_single_event():
    thresholds = {"temperature_high_c": 7.0, "gas_rise_delta": 10.0, "door_open_seconds": 180.0, "low_inventory_kg": 2.5}
    first = process_reading({"temperature_c": 5.0, "gas_voc": 150.0, "weight_kg": 5.0, "door_open": False, "door_open_seconds": 0.0}, thresholds, 120.0, {})
    second = process_reading({"temperature_c": 5.0, "gas_voc": 155.0, "weight_kg": 5.0, "door_open": False, "door_open_seconds": 0.0}, thresholds, 120.0, first)
    assert second["gas_rise"].active is True
    assert second["gas_rise"].message
