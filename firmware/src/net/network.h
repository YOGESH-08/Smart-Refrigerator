#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#include "../config.h"

class NetworkClient {
 public:
  void begin(const char* ssid, const char* password) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
  }

  bool isConnected() const { return WiFi.status() == WL_CONNECTED; }

  int8_t rssi() const { return WiFi.RSSI(); }

  bool sendReading(float temperature_c, float gas_voc, float weight_kg, bool door_open, uint32_t uptime_s) {
    if (!isConnected()) {
      return false;
    }

    const size_t capacity = JSON_OBJECT_SIZE(12) + 128;
    DynamicJsonDocument payload(capacity);
    payload["device_id"] = "refrigerator-01";
    payload["temperature_c"] = temperature_c;
    payload["gas_voc"] = gas_voc;
    payload["weight_kg"] = weight_kg;
    payload["door_open"] = door_open;
    payload["humidity_pct"] = 48.5f;
    payload["battery_mv"] = 3900;
    payload["wifi_rssi_dbm"] = rssi();
    payload["firmware_version"] = "1.1.0";
    payload["uptime_s"] = uptime_s;

    HTTPClient client;
    client.begin("http://192.168.43.1:5000/api/v1/readings");
    client.addHeader("Content-Type", "application/json");
    client.addHeader("X-API-Key", "smart-fridge-demo-key");
    String body;
    serializeJson(payload, body);
    const int status = client.POST(body);
    client.end();
    return status >= 200 && status < 300;
  }
};
