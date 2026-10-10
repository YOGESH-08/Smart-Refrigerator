# API documentation

## Authentication

The device and simulator must send the `X-API-Key` header. The default value is `smart-fridge-demo-key`.

## Reading payload example

```http
POST /api/v1/readings
X-API-Key: smart-fridge-demo-key
Content-Type: application/json
```

```json
{
  "device_id": "device-01",
  "temperature_c": 6.5,
  "humidity_pct": 47.1,
  "gas_voc": 128.0,
  "weight_kg": 4.2,
  "door_open": false,
  "battery_mv": 3890,
  "wifi_rssi_dbm": -60,
  "firmware_version": "1.1.0",
  "uptime_s": 2780
}
```

### Response

```json
{
  "data": {
    "id": 1,
    "device_id": "device-01",
    "timestamp": "2026-10-10T06:00:00+00:00",
    "temperature_c": 6.5,
    "humidity_pct": 47.1,
    "gas_voc": 128.0,
    "weight_kg": 4.2,
    "door_open": false
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
  "temperature_high_c": 7.5,
  "gas_rise_delta": 12.0,
  "door_open_seconds": 200,
  "low_inventory_kg": 3.0,
  "offline_seconds": 120
}
```

## CSV export

```http
GET /api/v1/export.csv
```
