# API documentation

## Authentication

The device and simulator must send the `X-API-Key` header. Set `SMART_FRIDGE_API_KEY` in `server/.env` and use the same key in the local firmware `device_config.h`.

## Reading payload example

```http
POST /api/v1/readings
X-API-Key: smart-fridge-demo-key
Content-Type: application/json
```

```json
{
  "device_id": "refrigerator-01",
  "temperature_c": 23.4,
  "gas_adc_raw": 2048,
  "temperature_sensor_ok": true,
  "gas_sensor_ok": true,
  "door_open": false,
  "door_sensor_verified": false,
  "alarm_active": true,
  "alarm_muted": false,
  "mute_remaining_s": 0,
  "fan_on": true,
  "red_led_on": true,
  "green_led_on": false,
  "buzzer_on": true,
  "wifi_rssi_dbm": -60,
  "firmware_version": "1.2.0",
  "uptime_s": 2780
}
```

`gas_adc_raw` is the MQ-135 ADC count from 0–4095. It is a relative reading, not ppm or a food-safety result. Temperature sensor failures are represented by `temperature_c: null` and `temperature_sensor_ok: false`. The reed sensor is reported as verified and door alerts are evaluated when `door_sensor_verified` is true. This installation maps GPIO27 LOW to closed and HIGH to open. No humidity or load-cell data is sent. Actuator fields report commanded output states, not physical feedback.

### Response

```json
{
  "data": {
    "id": 1,
    "device_id": "refrigerator-01",
    "timestamp": "2026-10-10T06:00:00+00:00",
    "temperature_c": 23.4,
    "gas_adc_raw": 2048,
    "temperature_sensor_ok": 1,
    "door_sensor_verified": 0,
    "alarm_active": 1,
    "fan_on": 1,
    "red_led_on": 1,
    "buzzer_on": 1
  },
  "meta": {
    "status": "stored",
    "alerts": 1
  }
}
```

## GET latest reading

```http
GET /api/v1/readings/latest
```

## RFID scan events

```http
POST /api/v1/rfid/scans
X-API-Key: <same-device-key>
Content-Type: application/json
```

```json
{
  "device_id": "refrigerator-01",
  "uid": "AB:12:CD:34",
  "firmware_version": "1.2.0"
}
```

The server timestamps and stores the scan. Every scan creates or increments the count for that UID. New tags start as unnamed items with a count of one; assign the food name in **Overview → RFID food inventory**. Later scans increment the count. You can edit both the item name and count in the dashboard.

```http
GET /api/v1/rfid/scans?limit=20
GET /api/v1/rfid/items
PUT /api/v1/rfid/items/AB%3A12%3ACD%3A34
Content-Type: application/json
```

```json
{
  "item_name": "Tomato",
  "quantity": 1
}
```

The dashboard item update endpoint accepts a name and optional quantity. It is intended for the local dashboard; the scanner POST continues to require the device API key.

## GET readings with time filtering

```http
GET /api/v1/readings?from=2026-10-10T05:00:00Z&to=2026-10-10T06:00:00Z&bucket=raw
```

## GET alerts

```http
GET /api/v1/alerts?status=active&severity=high
```

## ACK an alert

```http
POST /api/v1/alerts/1/ack
Content-Type: application/json
```

```json
{ "acknowledged_by": "faculty" }
```

## Threshold update

```http
PUT /api/v1/settings/thresholds
Content-Type: application/json
```

```json
{
  "temperature_high_c": 25.0,
  "gas_rise_delta": 12.0,
  "door_open_seconds": 200,
  "low_inventory_kg": 3.0,
  "offline_seconds": 120
}
```

The ESP32's temperature limit is fixed at 25°C in firmware. Keep this server threshold at 25°C so dashboard alerting agrees with the controller.

## CSV export

```http
GET /api/v1/export.csv
```
