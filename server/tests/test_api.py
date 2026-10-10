def test_readings_endpoint_stores_payload(app_client):
    response = app_client.post(
        "/api/v1/readings",
        json={
            "device_id": "device-01",
            "temperature_c": 6.8,
            "humidity_pct": 48.2,
            "gas_voc": 130.0,
            "weight_kg": 4.1,
            "door_open": False,
            "battery_mv": 3900,
            "wifi_rssi_dbm": -60,
            "firmware_version": "1.1.0",
            "uptime_s": 3450,
        },
        headers={"X-API-Key": "smart-fridge-demo-key"},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["data"]["device_id"] == "device-01"


def test_latest_and_export_endpoints(app_client):
    app_client.post(
        "/api/v1/readings",
        json={
            "device_id": "device-01",
            "temperature_c": 5.6,
            "humidity_pct": 44.0,
            "gas_voc": 100.0,
            "weight_kg": 3.5,
            "door_open": False,
            "battery_mv": 3920,
            "wifi_rssi_dbm": -58,
            "firmware_version": "1.1.0",
            "uptime_s": 3000,
        },
        headers={"X-API-Key": "smart-fridge-demo-key"},
    )

    latest = app_client.get("/api/v1/readings/latest").get_json()
    assert latest["meta"]["count"] == 1
    assert latest["data"]["device_id"] == "device-01"

    export = app_client.get("/api/v1/export.csv")
    assert export.status_code == 200
    assert "temperature_c" in export.get_data(as_text=True)


def test_alerts_and_settings_endpoints(app_client):
    app_client.post(
        "/api/v1/readings",
        json={
            "device_id": "device-01",
            "temperature_c": 9.0,
            "humidity_pct": 55.0,
            "gas_voc": 150.0,
            "weight_kg": 1.7,
            "door_open": True,
            "battery_mv": 3900,
            "wifi_rssi_dbm": -62,
            "firmware_version": "1.1.0",
            "uptime_s": 9000,
        },
        headers={"X-API-Key": "smart-fridge-demo-key"},
    )

    alerts = app_client.get("/api/v1/alerts")
    assert alerts.status_code == 200
    alert_data = alerts.get_json()["data"]
    assert len(alert_data) >= 1

    ack = app_client.post(
        "/api/v1/alerts/1/ack",
        json={"acknowledged_by": "faculty"},
    )
    assert ack.status_code == 200

    thresholds = app_client.get("/api/v1/settings/thresholds")
    assert thresholds.status_code == 200
    assert "temperature_high_c" in thresholds.get_json()["data"]

    updated = app_client.put(
        "/api/v1/settings/thresholds",
        json={"temperature_high_c": 8.0, "gas_rise_delta": 12.0, "door_open_seconds": 200.0, "low_inventory_kg": 3.0, "offline_seconds": 120.0},
    )
    assert updated.status_code == 200

    status = app_client.get("/api/v1/device/status?device_id=device-01")
    assert status.status_code == 200
    assert status.get_json()["data"]["device_id"] == "device-01"
