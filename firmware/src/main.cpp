#include <Arduino.h>
#include <WiFi.h>

#include "config.h"
#include "actuators/actuators.h"
#include "net/network.h"
#include "sensors/sensors.h"
#include "state_machine.h"

namespace {
  SensorSubsystem sensors;
  ActuatorController actuators;
  NetworkClient network;
  FridgeStateMachine state_machine;
  SensorReadings ring_buffer[MAX_OFFLINE_RING_BUFFER];
  size_t ring_index = 0;
  bool sound_silenced = false;
  unsigned long last_read_ms = 0;
  unsigned long last_heartbeat_ms = 0;
  unsigned long boot_ms = millis();

  void applyLocalControl(FridgeState state, const SensorReadings& sample) {
    const bool door_alert = state == FridgeState::DOOR_ALERT;
    const bool low_inventory = state == FridgeState::LOW_INVENTORY;
    const bool warning = state == FridgeState::WARNING;
    const bool silence = sample.door_open && digitalRead(TTP223_PIN) == LOW;
    sound_silenced = silence;
    actuators.applyState(door_alert, low_inventory, warning, sound_silenced);
  }

  void pushRingBuffer(const SensorReadings& sample) {
    ring_buffer[ring_index % MAX_OFFLINE_RING_BUFFER] = sample;
    ring_index += 1;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(DS18B20_PIN, INPUT);
  pinMode(MQ135_AOUT_PIN, INPUT);
  pinMode(REED_SWITCH_PIN, INPUT_PULLUP);
  pinMode(HX711_DT_PIN, INPUT);
  pinMode(HX711_SCK_PIN, OUTPUT);
  sensors.begin();
  actuators.begin();
  network.begin("smart-fridge-hotspot", "change-me");
  Serial.println("Smart Refrigerator booted");
}

void loop() {
  const unsigned long now_ms = millis();

  if (now_ms - last_read_ms >= READ_INTERVAL_MS) {
    last_read_ms = now_ms;
    SensorReadings sample = sensors.read();
    const FridgeState state = state_machine.update(sample.temperature_c, sample.door_open, sample.weight_kg);
    pushRingBuffer(sample);
    applyLocalControl(state, sample);

    if (network.isConnected()) {
      if (now_ms - last_heartbeat_ms >= HEARTBEAT_INTERVAL_MS) {
        last_heartbeat_ms = now_ms;
        network.sendReading(sample.temperature_c, sample.gas_voc, sample.weight_kg, sample.door_open, now_ms / 1000UL);
      }
    }
  }

  if (!network.isConnected()) {
    Serial.println("WiFi disconnected; retrying");
    delay(5000);
    WiFi.begin("smart-fridge-hotspot", "change-me");
  }

  if (millis() - boot_ms > WATCHDOG_MS) {
    Serial.println("Hardware watchdog triggered");
    ESP.restart();
  }
}
