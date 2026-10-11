import sqlite3

from app.repository.repository import Repository


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


def test_reading_accepts_uninstalled_sensors_as_null(app_client):
    response = app_client.post(
        "/api/v1/readings",
        json={
            "device_id": "refrigerator-01",
            "temperature_c": 5.1,
            "gas_voc": 117.0,
            "humidity_pct": None,
            "weight_kg": None,
            "door_open": False,
            "door_open_seconds": 0,
            "firmware_version": "1.2.0",
        },
        headers={"X-API-Key": "smart-fridge-demo-key"},
    )

    assert response.status_code == 201
    reading = response.get_json()["data"]
    assert reading["humidity_pct"] is None
    assert reading["weight_kg"] is None
    assert not any(
        alert["alert_type"] == "low_inventory"
        for alert in app_client.get("/api/v1/alerts").get_json()["data"]
    )


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


def test_legacy_readings_database_migrates_without_losing_rows(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                temperature_c REAL NOT NULL,
                humidity_pct REAL NOT NULL,
                gas_voc REAL NOT NULL,
                weight_kg REAL NOT NULL,
                door_open INTEGER NOT NULL,
                battery_mv REAL,
                wifi_rssi_dbm INTEGER,
                firmware_version TEXT,
                uptime_s INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO readings (
                device_id, timestamp, temperature_c, humidity_pct, gas_voc,
                weight_kg, door_open, firmware_version, uptime_s, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("refrigerator-01", "2026-10-10T00:00:00+00:00", 5.0, 40.0, 120.0, 4.0, 0, "1.1.0", 15, "2026-10-10T00:00:00+00:00"),
        )

    repository = Repository(str(db_path))
    repository.init_db()
    old_reading = repository.get_latest_reading("refrigerator-01")
    new_reading = repository.insert_reading(
        {
            "device_id": "refrigerator-01",
            "temperature_c": 5.2,
            "gas_voc": 121.0,
            "door_open": False,
            "humidity_pct": None,
            "weight_kg": None,
        }
    )

    assert old_reading is not None
    assert old_reading["temperature_c"] == 5.0
    assert new_reading is not None
    assert new_reading["humidity_pct"] is None
    assert new_reading["weight_kg"] is None
