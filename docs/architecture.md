# Architecture

## System context

```mermaid
flowchart TD
  User[Operator / Faculty Reviewer] --> Dashboard[Web dashboard]
  Dashboard --> API[Flask REST API]
  API --> DB[(SQLite database)]
  API --> AlertEngine[Alert engine]
  ESP32[ESP32 DevKit V1] --> Telemetry[Sensor telemetry / JSON]
  Telemetry --> API
  LocalLogic[Local state machine] --> Fan[Fan]
  LocalLogic --> Buzzer[Buzzer]
  LocalLogic --> LEDs[Red + Green LEDs]
```

## Data flow

```mermaid
sequenceDiagram
  participant Device as ESP32
  participant API as Flask API
  participant Repo as Repository
  participant Engine as Alert Engine
  participant UI as Dashboard
  Device->>API: POST /api/v1/readings
  API->>Repo: save reading
  API->>Engine: evaluate thresholds and baseline
  Engine-->>API: alert lifecycle update
  API-->>UI: latest / readings / alerts JSON
  UI->>API: poll every 2s
```

## Alert state machine

```mermaid
stateDiagram-v2
  [*] --> ACTIVE
  ACTIVE --> ACKNOWLEDGED
  ACKNOWLEDGED --> RESOLVED
  ACTIVE --> RESOLVED
  RESOLVED --> [*]
```

## Database schema

```mermaid
erDiagram
  READINGS ||--o{ ALERTS : generates
  READINGS {
    integer id PK
    text device_id
    text timestamp
    real temperature_c
    real humidity_pct
    real gas_voc
    real weight_kg
    integer door_open
  }
  ALERTS {
    integer id PK
    text device_id
    text alert_type
    text severity
    text status
    text message
    text first_seen
    text last_triggered
    text acknowledged_at
    text resolved_at
  }
```

## Event model

The database is intentionally split into operational telemetry, alert state, and configuration values so the web dashboard can independently query summary analytics without mixing them with live sensor history.
