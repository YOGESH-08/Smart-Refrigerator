from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Iterable


class Repository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    temperature_c REAL,
                    humidity_pct REAL,
                    gas_voc REAL,
                    gas_adc_raw INTEGER,
                    weight_kg REAL,
                    door_open INTEGER NOT NULL,
                    touch_pressed INTEGER,
                    rfid_reader_ok INTEGER,
                    door_open_seconds REAL,
                    battery_mv REAL,
                    wifi_rssi_dbm INTEGER,
                    firmware_version TEXT,
                    uptime_s INTEGER,
                    temperature_sensor_ok INTEGER,
                    gas_sensor_ok INTEGER,
                    door_sensor_verified INTEGER NOT NULL DEFAULT 0,
                    alarm_active INTEGER NOT NULL DEFAULT 0,
                    alarm_muted INTEGER NOT NULL DEFAULT 0,
                    mute_remaining_s INTEGER,
                    fan_on INTEGER NOT NULL DEFAULT 0,
                    red_led_on INTEGER NOT NULL DEFAULT 0,
                    green_led_on INTEGER NOT NULL DEFAULT 0,
                    buzzer_on INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._migrate_readings_table(conn)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_readings_device_timestamp ON readings(device_id, timestamp)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    message TEXT NOT NULL,
                    first_seen TEXT NOT NULL,
                    last_triggered TEXT NOT NULL,
                    acknowledged_at TEXT,
                    acknowledged_by TEXT,
                    resolved_at TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(device_id, alert_type)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status, device_id, last_triggered)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS rfid_scans (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, uid TEXT NOT NULL, item_name TEXT, firmware_version TEXT, timestamp TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rfid_scans_timestamp ON rfid_scans(timestamp DESC)")
            conn.execute("CREATE TABLE IF NOT EXISTS device_commands (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, command TEXT NOT NULL, created_at TEXT NOT NULL)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS rfid_items (uid TEXT PRIMARY KEY, item_name TEXT, quantity INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_status (
                    device_id TEXT PRIMARY KEY,
                    last_seen TEXT NOT NULL,
                    firmware_version TEXT NOT NULL,
                    wifi_rssi_dbm INTEGER,
                    uptime_s INTEGER,
                    status TEXT NOT NULL DEFAULT 'online',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_defaults(conn)

    def _migrate_readings_table(self, conn: sqlite3.Connection) -> None:
        columns = {
            row["name"]: row
            for row in conn.execute("PRAGMA table_info(readings)").fetchall()
        }
        optional_columns = ("temperature_c", "humidity_pct", "gas_voc", "weight_kg")
        if any(columns[name]["notnull"] for name in optional_columns):
            conn.execute(
                """
                CREATE TABLE readings_migrated (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    temperature_c REAL,
                    humidity_pct REAL,
                    gas_voc REAL,
                    weight_kg REAL,
                    door_open INTEGER NOT NULL,
                    door_open_seconds REAL,
                    battery_mv REAL,
                    wifi_rssi_dbm INTEGER,
                    firmware_version TEXT,
                    uptime_s INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            source_columns = (
                "id, device_id, timestamp, temperature_c, humidity_pct, gas_voc, "
                "weight_kg, door_open, battery_mv, wifi_rssi_dbm, firmware_version, "
                "uptime_s, created_at"
            )
            conn.execute(
                f"INSERT INTO readings_migrated ({source_columns}) "
                f"SELECT {source_columns} FROM readings"
            )
            conn.execute("DROP TABLE readings")
            conn.execute("ALTER TABLE readings_migrated RENAME TO readings")
            columns = {
                row["name"]: row
                for row in conn.execute("PRAGMA table_info(readings)").fetchall()
            }
        if "door_open_seconds" not in columns:
            conn.execute("ALTER TABLE readings ADD COLUMN door_open_seconds REAL")
        additions = {
            "gas_adc_raw": "INTEGER",
            "touch_pressed": "INTEGER",
            "rfid_reader_ok": "INTEGER",
            "temperature_sensor_ok": "INTEGER",
            "gas_sensor_ok": "INTEGER",
            "door_sensor_verified": "INTEGER NOT NULL DEFAULT 0",
            "alarm_active": "INTEGER NOT NULL DEFAULT 0",
            "alarm_muted": "INTEGER NOT NULL DEFAULT 0",
            "mute_remaining_s": "INTEGER",
            "fan_on": "INTEGER NOT NULL DEFAULT 0",
            "red_led_on": "INTEGER NOT NULL DEFAULT 0",
            "green_led_on": "INTEGER NOT NULL DEFAULT 0",
            "buzzer_on": "INTEGER NOT NULL DEFAULT 0",
        }
        for name, declaration in additions.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE readings ADD COLUMN {name} {declaration}")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_device_timestamp ON readings(device_id, timestamp)"
        )

    def _ensure_defaults(self, conn: sqlite3.Connection) -> None:
        defaults = {
            "temperature_high_c": "22.0",
            "gas_rise_delta": "10.0",
            "door_open_seconds": "180.0",
            "low_inventory_kg": "2.5",
            "offline_seconds": "90.0",
            "baseline_gas": "120.0",
        }
        for key, value in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings(key, value, updated_at) VALUES (?, ?, ?)",
                (key, value, _utc_now_iso()),
            )
        conn.execute("UPDATE settings SET value = '22.0' WHERE key = 'temperature_high_c' AND value = '7.0'")

    def insert_reading(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = _utc_now_iso()
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO readings (
                        device_id, timestamp, temperature_c, humidity_pct, gas_voc, gas_adc_raw, weight_kg,
                        door_open, touch_pressed, rfid_reader_ok, door_open_seconds, battery_mv, wifi_rssi_dbm, firmware_version, uptime_s,
                        temperature_sensor_ok, gas_sensor_ok, door_sensor_verified, alarm_active, alarm_muted,
                        mute_remaining_s, fan_on, red_led_on, green_led_on, buzzer_on, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["device_id"],
                    current,
                    payload.get("temperature_c"),
                    payload.get("humidity_pct"),
                    payload.get("gas_voc"),
                    payload.get("gas_adc_raw"),
                    payload.get("weight_kg"),
                    int(bool(payload.get("door_open", False))),
                    _optional_bool(payload.get("touch_pressed")),
                    _optional_bool(payload.get("rfid_reader_ok")),
                    payload.get("door_open_seconds"),
                    payload.get("battery_mv"),
                    payload.get("wifi_rssi_dbm"),
                    payload.get("firmware_version", "1.0.0"),
                    payload.get("uptime_s"),
                    _optional_bool(payload.get("temperature_sensor_ok")),
                    _optional_bool(payload.get("gas_sensor_ok")),
                    int(bool(payload.get("door_sensor_verified", False))),
                    int(bool(payload.get("alarm_active", False))),
                    int(bool(payload.get("alarm_muted", False))),
                    payload.get("mute_remaining_s"),
                    int(bool(payload.get("fan_on", False))),
                    int(bool(payload.get("red_led_on", False))),
                    int(bool(payload.get("green_led_on", False))),
                    int(bool(payload.get("buzzer_on", False))),
                    current,
                ),
            )
            reading_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO device_status(device_id, last_seen, firmware_version, wifi_rssi_dbm, uptime_s, status, updated_at) VALUES (?, ?, ?, ?, ?, 'online', ?) ON CONFLICT(device_id) DO UPDATE SET last_seen=excluded.last_seen, firmware_version=excluded.firmware_version, wifi_rssi_dbm=excluded.wifi_rssi_dbm, uptime_s=excluded.uptime_s, status='online', updated_at=excluded.updated_at",
                (
                    payload["device_id"],
                    current,
                    payload.get("firmware_version", "1.0.0"),
                    payload.get("wifi_rssi_dbm"),
                    payload.get("uptime_s"),
                    current,
                ),
            )
        return self.get_reading_by_id(reading_id)

    def get_reading_by_id(self, reading_id: int) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM readings WHERE id = ?", (reading_id,)).fetchone()
            return dict(row) if row else None

    def insert_rfid_scan(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = _utc_now_iso()
        with self.get_connection() as conn:
            item = conn.execute("SELECT * FROM rfid_items WHERE uid = ?", (payload["uid"],)).fetchone()
            if item is None:
                conn.execute(
                    "INSERT INTO rfid_items(uid, item_name, quantity, updated_at) VALUES (?, NULL, 1, ?)",
                    (payload["uid"], current),
                )
                item_name, quantity = None, 1
            else:
                quantity = int(item["quantity"]) + 1
                item_name = item["item_name"]
                conn.execute(
                    "UPDATE rfid_items SET quantity = ?, updated_at = ? WHERE uid = ?",
                    (quantity, current, payload["uid"]),
                )
            cursor = conn.execute(
                "INSERT INTO rfid_scans(device_id, uid, item_name, firmware_version, timestamp, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (payload["device_id"], payload["uid"], item_name, payload.get("firmware_version"), current, current),
            )
            row = conn.execute("SELECT * FROM rfid_scans WHERE id = ?", (cursor.lastrowid,)).fetchone()
            result = dict(row)
            result["quantity"] = quantity
            return result

    def get_rfid_items(self) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT uid, item_name, quantity, updated_at FROM rfid_items ORDER BY COALESCE(item_name, ''), uid"
            ).fetchall()
            return [dict(row) for row in rows]

    def update_rfid_item(self, uid: str, item_name: str, quantity: int | None = None) -> dict[str, Any] | None:
        current = _utc_now_iso()
        with self.get_connection() as conn:
            existing = conn.execute("SELECT * FROM rfid_items WHERE uid = ?", (uid,)).fetchone()
            if existing is None:
                return None
            new_quantity = int(existing["quantity"]) if quantity is None else quantity
            conn.execute(
                "UPDATE rfid_items SET item_name = ?, quantity = ?, updated_at = ? WHERE uid = ?",
                (item_name, new_quantity, current, uid),
            )
            conn.execute("UPDATE rfid_scans SET item_name = ? WHERE uid = ?", (item_name, uid))
            return dict(conn.execute("SELECT * FROM rfid_items WHERE uid = ?", (uid,)).fetchone())

    def get_rfid_scans(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM rfid_scans ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_latest_reading(self, device_id: str | None = None) -> dict[str, Any] | None:
        with self.get_connection() as conn:
            if device_id:
                row = conn.execute(
                    "SELECT * FROM readings WHERE device_id = ? ORDER BY timestamp DESC LIMIT 1",
                    (device_id,),
                ).fetchone()
            else:
                row = conn.execute("SELECT * FROM readings ORDER BY timestamp DESC LIMIT 1").fetchone()
            return dict(row) if row else None

    def get_readings(self, from_ts: str | None = None, to_ts: str | None = None, bucket: str = "raw") -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM readings"
            params: list[Any] = []
            clauses: list[str] = []
            if from_ts:
                clauses.append("timestamp >= ?")
                params.append(from_ts)
            if to_ts:
                clauses.append("timestamp <= ?")
                params.append(to_ts)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY timestamp ASC"
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_settings(self) -> dict[str, float]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings ORDER BY key").fetchall()
            return {row["key"]: float(row["value"]) for row in rows if row["key"] in {"temperature_high_c", "gas_rise_delta", "door_open_seconds", "low_inventory_kg", "offline_seconds", "baseline_gas"}}

    def save_thresholds(self, thresholds: dict[str, float]) -> dict[str, float]:
        with self.get_connection() as conn:
            for key, value in thresholds.items():
                conn.execute(
                    "INSERT INTO settings(key, value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                    (key, str(float(value)), _utc_now_iso()),
                )
        return self.get_settings()

    def save_baseline(self, baseline: float) -> float:
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO settings(key, value, updated_at) VALUES ('baseline_gas', ?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (str(float(baseline)), _utc_now_iso()),
            )
        return float(self.get_settings().get("baseline_gas", baseline))

    def get_alerts(self, status: str | None = None, severity: str | None = None) -> list[dict[str, Any]]:
        with self.get_connection() as conn:
            query = "SELECT * FROM alerts"
            params: list[Any] = []
            clauses: list[str] = []
            if status:
                clauses.append("status = ?")
                params.append(status)
            if severity:
                clauses.append("severity = ?")
                params.append(severity)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY last_triggered DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def upsert_alert(self, alert: dict[str, Any]) -> dict[str, Any]:
        with self.get_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM alerts WHERE device_id = ? AND alert_type = ?",
                (alert["device_id"], alert["alert_type"]),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE alerts
                    SET severity = ?, status = CASE WHEN ? = 'active' AND status = 'acknowledged' THEN status ELSE ? END, message = ?, last_triggered = ?, acknowledged_at = COALESCE(acknowledged_at, ?), resolved_at = ?
                    WHERE id = ?
                    """,
                    (
                        alert["severity"],
                        alert["status"],
                        alert["status"],
                        alert["message"],
                        alert["last_triggered"],
                        alert.get("acknowledged_at"),
                        alert.get("resolved_at"),
                        existing["id"],
                    ),
                )
                return dict(conn.execute("SELECT * FROM alerts WHERE id = ?", (existing["id"],)).fetchone())
            cursor = conn.execute(
                """
                INSERT INTO alerts(device_id, alert_type, severity, status, message, first_seen, last_triggered, acknowledged_at, acknowledged_by, resolved_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert["device_id"],
                    alert["alert_type"],
                    alert["severity"],
                    alert["status"],
                    alert["message"],
                    alert["first_seen"],
                    alert["last_triggered"],
                    alert.get("acknowledged_at"),
                    alert.get("acknowledged_by"),
                    alert.get("resolved_at"),
                    _utc_now_iso(),
                ),
            )
            alert_id = cursor.lastrowid
            return dict(conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone())

    def acknowledge_alert(self, alert_id: int, acknowledged_by: str) -> dict[str, Any]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
            if row is None:
                raise ValueError("Alert not found")
            current = _utc_now_iso()
            conn.execute(
                "UPDATE alerts SET status = 'acknowledged', acknowledged_at = ?, acknowledged_by = ? WHERE id = ?",
                (current, acknowledged_by, alert_id),
            )
            return dict(conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone())

    def queue_device_command(self, device_id: str, command: str) -> None:
        with self.get_connection() as conn:
            conn.execute("INSERT INTO device_commands(device_id, command, created_at) VALUES (?, ?, ?)", (device_id, command, _utc_now_iso()))

    def consume_device_commands(self, device_id: str) -> list[str]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT id, command FROM device_commands WHERE device_id = ? ORDER BY id", (device_id,)).fetchall()
            if rows:
                conn.executemany("DELETE FROM device_commands WHERE id = ?", [(row["id"],) for row in rows])
            return [row["command"] for row in rows]

    def get_device_status(self, device_id: str | None = None) -> dict[str, Any]:
        with self.get_connection() as conn:
            if device_id:
                row = conn.execute("SELECT * FROM device_status WHERE device_id = ?", (device_id,)).fetchone()
            else:
                row = conn.execute("SELECT * FROM device_status ORDER BY last_seen DESC LIMIT 1").fetchone()
            if row is None:
                return {"device_id": device_id or "unknown", "status": "offline", "last_seen": None, "firmware_version": "unknown", "wifi_rssi_dbm": None, "uptime_s": 0}
            return dict(row)

    def export_csv(self) -> str:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM readings ORDER BY timestamp ASC").fetchall()
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "id", "device_id", "timestamp", "temperature_c", "humidity_pct", "gas_voc", "gas_adc_raw",
                "weight_kg", "door_open", "door_open_seconds", "battery_mv", "wifi_rssi_dbm", "firmware_version", "uptime_s"
            ])
            for row in rows:
                writer.writerow([row[col] for col in [
                    "id", "device_id", "timestamp", "temperature_c", "humidity_pct", "gas_voc", "gas_adc_raw",
                    "weight_kg", "door_open", "door_open_seconds", "battery_mv", "wifi_rssi_dbm", "firmware_version", "uptime_s"
                ]])
            return output.getvalue()

    def prune_old_rows(self, retention_days: int = 7) -> int:
        cutoff = _utc_now_iso(-timedelta(days=retention_days))
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM readings WHERE timestamp < ?", (cutoff,))
            conn.execute("DELETE FROM alerts WHERE last_triggered < ? AND status = 'resolved'", (cutoff,))
            return cursor.rowcount


def _utc_now_iso(delta: timedelta | None = None) -> str:
    if delta:
        now = datetime.now(timezone.utc) + delta
    else:
        now = datetime.now(timezone.utc)
    return now.isoformat(timespec="seconds")


def _optional_bool(value: Any) -> int | None:
    return None if value is None else int(bool(value))
