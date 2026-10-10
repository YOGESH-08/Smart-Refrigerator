#pragma once

#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <HX711.h>

#include "../config.h"

class SensorReadings {
 public:
  float temperature_c = 0.0f;
  float gas_voc = 0.0f;
  float humidity_pct = 0.0f;
  float weight_kg = 0.0f;
  bool door_open = false;
  int wifi_rssi_dbm = -80;
  bool has_error = false;
};

class SensorSubsystem {
 public:
  void begin() {
    one_wire_.begin(DS18B20_PIN);
    sensors_.setOneWire(&one_wire_);
    sensors_.begin();
    scale_.begin(HX711_DT_PIN, HX711_SCK_PIN);
    pinMode(REED_SWITCH_PIN, INPUT_PULLUP);
    pinMode(TTP223_PIN, INPUT_PULLUP);
    scale_.set_scale();
    scale_.tare();
  }

  SensorReadings read() {
    SensorReadings sample;
    sample.temperature_c = readTemperatureC();
    sample.gas_voc = analogRead(MQ135_AOUT_PIN) * 0.12f;
    sample.humidity_pct = 50.0f;
    sample.door_open = digitalRead(REED_SWITCH_PIN) == LOW;
    sample.weight_kg = readWeightKg();
    sample.wifi_rssi_dbm = WiFi.RSSI();
    sample.has_error = isnan(sample.temperature_c) || sample.temperature_c == 0.0f;
    return sample;
  }

  float readTemperatureC() {
    sensors_.requestTemperatures();
    const float reading = sensors_.getTempCByIndex(0);
    if (isnan(reading)) {
      return 5.0f;
    }
    return reading;
  }

  float readWeightKg() {
    const int32_t raw = scale_.get_units(5);
    const float kilograms = raw / 1000.0f;
    return max(0.0f, kilograms);
  }

 private:
  OneWire one_wire_;
  DallasTemperature sensors_{&one_wire_};
  HX711 scale_;
};
