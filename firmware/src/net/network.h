#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#include "../config.h"
#include "../sensors/sensors.h"

class NetworkClient {
 public:
  void begin() {
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  }

  bool isConnected() const { return WiFi.status() == WL_CONNECTED; }

  int8_t rssi() const { return WiFi.RSSI(); }

  bool sendReading(const SensorReadings& reading, uint32_t door_open_seconds, uint32_t uptime_s) {
    if (!isConnected()) {
      return false;
    }

    StaticJsonDocument<768> payload;
    payload["device_id"] = DEVICE_ID;
    if (reading.temperature_valid) {
      payload["temperature_c"] = reading.temperature_c;
    } else {
      payload["temperature_c"] = nullptr;
    }
    if (reading.gas_valid) payload["gas_adc_raw"] = reading.gas_adc_raw;
    else payload["gas_adc_raw"] = nullptr;
    payload["door_open"] = reading.door_open;
    payload["door_open_seconds"] = door_open_seconds;
    payload["door_sensor_verified"] = reading.door_sensor_verified;
    payload["temperature_sensor_ok"] = reading.temperature_valid;
    payload["gas_sensor_ok"] = reading.gas_valid;
    payload["alarm_active"] = reading.alarm_active;
    payload["alarm_muted"] = reading.alarm_muted;
    payload["mute_remaining_s"] = reading.mute_remaining_s;
    payload["fan_on"] = reading.fan_on;
    payload["red_led_on"] = reading.red_led_on;
    payload["green_led_on"] = reading.green_led_on;
    payload["buzzer_on"] = reading.buzzer_on;
    payload["wifi_rssi_dbm"] = rssi();
    payload["firmware_version"] = FIRMWARE_VERSION;
    payload["uptime_s"] = uptime_s;

    HTTPClient client;
    client.setTimeout(3000);
    if (!client.begin(API_ENDPOINT)) {
      Serial.println("HTTP client could not initialize endpoint");
      return false;
    }
    client.addHeader("Content-Type", "application/json");
    client.addHeader("X-API-Key", API_KEY);
    String body;
    serializeJson(payload, body);
    const int status = client.POST(body);
    if (status < 0) {
      Serial.printf("Reading POST failed: %s\n", HTTPClient::errorToString(status).c_str());
    } else {
      Serial.printf("Reading POST returned HTTP %d\n", status);
    }
    client.end();
    return status >= 200 && status < 300;
  }

  bool sendRfidScan(const String& uid) {
    if (!isConnected()) return false;
    String endpoint = API_ENDPOINT;
    const int readings_suffix = endpoint.lastIndexOf("/readings");
    if (readings_suffix < 0) {
      Serial.println("RFID scan endpoint cannot be derived from API_ENDPOINT");
      return false;
    }
    endpoint.remove(readings_suffix);
    endpoint += "/rfid/scans";
    StaticJsonDocument<192> payload;
    payload["device_id"] = DEVICE_ID;
    payload["uid"] = uid;
    payload["firmware_version"] = FIRMWARE_VERSION;
    HTTPClient client;
    client.setTimeout(3000);
    if (!client.begin(endpoint)) return false;
    client.addHeader("Content-Type", "application/json");
    client.addHeader("X-API-Key", API_KEY);
    String body;
    serializeJson(payload, body);
    const int status = client.POST(body);
    Serial.printf("RFID scan POST returned HTTP %d\n", status);
    client.end();
    return status >= 200 && status < 300;
  }
};
